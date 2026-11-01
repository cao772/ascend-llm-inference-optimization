# Qwen 推理算子优化｜跨案例共性分析 v0.1（2026-10-30）

> **本研究当前无 GPU/NPU/TPU 落地测试环境。** 本文仅据原作者文章、开源 PR、官方技术报告及公开 GitHub 工程整理，不把外部跑分标成我方实测。案例结构化来源：[`research/cases/qwen-optimization-cases-2026-10-30.json`](../research/cases/qwen-optimization-cases-2026-10-30.json)。

## 1. 证据类型和跨案例比较边界

- 首批 **9 条**：7 条有原作者报告或发布代码的性能证据；1 条是 Benchmark 工具入口，没有这里可归因的测量；1 条是未落地的 AMD 优化提案。
- 同时收录 Ascend、H100/H200/B200、Google TPU、Apple Metal。**跨硬件只总结设计思路，不做性能百分比横向排名**。
- 有的结果是算子微基准（如 Fused MoE），有的是 Prefill-only（FlashInfer GDN），有的是实际在线服务吞吐；指标不能混用。
- 标签与重合频次由本研究人工注释，是“研究线索”而不是统计证明，更不是因果效应评估。

### 第一轮对照

| 编号 | 来源与模型 | 优化机制 | 具体证据和重要限制 |
|---|---|---|---|
| QINF-001 | [得物/910C/Qwen3.5-A3B](https://mp.weixin.qq.com/s/GXaZWhIZ25ifH07iaTxfZQ) | Static Kernel、HCCL AIV、MoE overlap、GDN 融合、MinTokens 掩码缓存、MTP | 14.22→5.0ms c1 TPOT（最终组合；实验阶段环境/数据集有变化，且内部代码未见完整公开） |
| QINF-002 | [SGLang PR #22664 / Qwen3-Coder-Next](https://github.com/sgl-project/sglang/pull/22664) | FlashInfer AllReduce 融合 | H100 TP4、2048/256、concurrency 32：req/s +71.4%、TPOT -49.4%；[后续确定性修复](https://github.com/sgl-project/sglang/pull/24629) 说明融合有数值契约风险 |
| QINF-003 | [vLLM/Qwen3.5-397B](https://vllm.ai/blog/2026-05-11-vllm-tops-artificial-analysis) | QKNorm/RoPE/Post-conv、AllReduce/RMS、双流 | c256 综合吞吐约 +10%；多项调整共同作用、不能逐项归因 |
| QINF-004 | [FlashInfer GDN Prefill](https://vllm.ai/blog/2026-08-06-qwen35-25k-tps) | Blackwell 专用 GDN Kernel | GDN 微基准最高约 5.92×；8×B200 Prefill-only 吞吐仅约 1.13×，注意 Kernel vs 端到端 |
| QINF-005 | [腾讯 HPC-Ops × SGLang](https://www.lmsys.org/blog/2026-08-07-hpc-ops-sglang/) | Fused MoE、Router GEMM、Attention | Qwen3/H200 8-token MoE microbenchmark 最高约 4.21×；其他 Hy3 在线 TPOT 数据不可移用 |
| QINF-006 | [Google Ironwood/Qwen3.5](https://developers.googleblog.com/systems-engineering-playbook-optimizing-qwen-35-397b-moe-on-ironwood-tpu7x/) | 模块化 Pallas GDN/Grouped GEMM/专家路由 | 512 并发下 Decode-heavy 约 3.1×、Prefill-heavy 约 4.7×（相较该团队此前基线）；不能直接映射到 910C |
| QINF-007 | [Apple MLX/Qwen3.6-A3B](https://github.com/fbzz/qwen3.6-mlx-inference) | Q4 Gate/Up Metal JIT 融合 | 作者自测 Decode 中位数 +2.768%；同时保留其他试验负优化、数值变化的否决记录 |
| QINF-008 | [SGLang MoE 调优工具](https://github.com/sgl-project/sglang/blob/main/benchmark/kernels/fused_moe_triton/README.md) | TP/EP MoE 自动调优基准 | 代码存在，**本条没有可归因的速度改进数据** |
| QINF-009 | [AMD MI300X Qwen3-Next 规划](https://github.com/sgl-project/sglang/issues/19196) | QKNorm+RoPE、RMSNorm+FP8、Attention、MoE | **只有提案，所有“期望加速”不纳入已验证案例** |

## 2. 从案例归纳的关键技术机制

### H1｜跨平台最高重复率：减少 HBM 往返和多余 Kernel

人工给 7 条有结果的案例注释后：`memory_traffic` 7/7，`fusion` 5/7，`kernel_specialization` 4/7。注意这些是**标签频次**，取决于我们给案例打标的口径。

典型模式：
1. 旧路径：`matmul → AllReduce → residual add → RMSNorm → quant`，多个中间张量的写回/重读、多个 launch。
2. 新路径：融合可合法合并的 **producer/consumer**，或让 AllReduce/RMS/quant 进入同一流水。
3. 测试必须验证形状、精度格式、数值误差、各并发、启停开关与 Fallback；融合并非越大越好。

**共同设计原理**：降低调度开销与内存流量；**平台实现不共享**：昇腾 AscendC/HCCS、NVIDIA CUDA/FlashInfer、TPU Pallas、Apple Metal 独立实现。

### H2｜Qwen3.5 混合注意力使 GDN 成为反复出现的热点

- 得物：910C 的 GDN Decode 路径合并 L2Norm + recurrent，并减少 weight transpose/rearrange 重复开销。
- vLLM：Qwen3.5 Post-Conv 融合、QKNorm + RoPE 路径、跨流。
- FlashInfer：Blackwell GDN Prefill 专用 Kernel；不同形状收益差异很大。
- Google：针对 TPU7x 的 GDN 定制模块。

**研究假设**：先按 `prefill/decode` 和 `GDN vs Full Attention` 拆开，收集每层算子次数、host gap、HBM 访问，再判断在哪个算子边界融合。不能直接拿 Prefill 微基准预测 Decode TPOT。

### H3｜MoE 的优化重点是小 GEMM、路由、权重访存与跨专家调度

- 得物：共享专家与 routed expert 多流重叠、权重预取、MC2。
- 腾讯：将小规模 expert GEMM、路由负载和 kernel fusion 一并考虑；提供 FusedMoE Benchmark。
- Google：Grouped GEMM 和路由调度模块化；不同模型布局逐个映射。
- MLX：Gate/Up Q4 两次 dispatch → 单个受控 Metal Kernel。
- SGLang：给 TP 和 EP 两种模式都提供调优脚手架。

**研究假设**：要把 `token per expert`、`top-k`、`EP/TP`、专家负载不均、权重精度都纳入性能特征，不能只看总参数量。

### H4｜代码分支优化之后仍需服务级校验

- SGLang [#22664](https://github.com/sgl-project/sglang/pull/22664) 的 AllReduce 性能表现很好，但引入的约简顺序会影响跨 Batch 的 bit-exact determinism。
- 后续 [#24629](https://github.com/sgl-project/sglang/pull/24629) 在 `enable_deterministic_inference` 设为 true 时禁用该融合，并给出复现实测。
- 得物 GDN 合并在 c8 下有负优化，MTP capture size 不匹配时延迟反而飙升。
- Apple MLX 作者公开记录性能为负和数值不一致的否决实验。

**研究假设**：未来基准不仅记录 `TTFT/TPOT/TPS`，还应在相同 seeds、采样器、提示词及 precision 下记录 logits/top-k/输出序列一致性、确定性模式、错误率以及分批/并发回归。

### H5｜共性不等于可复制源码

- 算子形状、dtype、显存布局、bank conflict、集群链路、是否使用 graph capture，均会改变优化方向。
- 在已有融合占位（如 AllReduce + RMSNorm）的模型上，新的 `Norm + Quant` 不能盲目重复融合；应选择正确的图边界。
- 新版框架可能已经具备相同优化，先查上游 PR/文件与实际调用链，避免重复维护私有补丁。

## 3. 优先深挖的 4 个“跨案例复用包”（目前仅研究假设）

| 优先度 | 研究包 | 对应案例 | 本阶段可交付证据 |
|---|---|---|---|
| P0 | AllReduce + residual + RMSNorm / Quant Fusion | 001/002/003 | 昇腾 HCCL 与 CUDA FlashInfer 两套代码路径、形状/精度/确定性限制对照 |
| P0 | GDN Decode/Prefill 融合 | 001/003/004/006 | Qwen3.5 GDN 子图与跨平台算子边界图 |
| P0 | MoE Shared/Routed Expert + 小 GEMM | 001/005/006/007/008 | 路由策略、权重预取、TP/EP 与 benchmark 输入维度矩阵 |
| P1 | 图捕获/CPU 数据复用/投机解码交互 | 001/003 | 每项优化的前提条件、输入形状、误用/回退清单 |

## 4. 现在没有硬件，仍可以做的工作

1. **源码级**：只读追踪各上游官方仓库固定版本的算子链路和调用入口；保存 commit SHA、PR 与许可证链接。不把他人私有 Patch 伪装成开源。
2. **静态模型结构**：对 Qwen3.5 / Qwen3.6 的 config.json 做层数、维度、MoE、注意力类型、dtype 等元数据比较，标记可优化热点（未经 Profile 的仅为候选）。
3. **案例对照工具**：运行 `python3 tools/compare_operator_cases.py --output build/case-overlap.json`，只输出共享机制，不输出性能排名或“预计提升 30%”。
4. **准备回归案例**：整合 Exact-Token、Top-k 数值误差、确定性、长短上下文、c=1/4/8/32、TP/EP、不同输入输出长度；未来有机器再测试。
5. **保留失败案例**：每一个负优化、精度回归、Graph 兼容性问题都要关联修复 PR、上游版本和回退条件。

## 5. 下一轮检索关键词与准入要求

- 搜索主线：`Qwen3.5 GDN fusion`、`Qwen3Next allreduce RMSNorm`、`Qwen3 MoE grouped GEMM`、`Qwen MTP cudagraph`、`AscendC recurrent gated delta`、`Qwen3.6 MLX Metal kernel`。
- 新案例至少有**论文/作者报告/PR/实际代码**一项可查证来源；最好附编译/推理软件版本、硬件、负载、具体指标。
- 按 `merged code`、`author reported`、`microbenchmark`、`proposal` 分别标记。
- 收集失败、撤回、数值不一致和后续修复。没有硬件不阻塞资料研究，但**不得宣称复现或落地收益**。
