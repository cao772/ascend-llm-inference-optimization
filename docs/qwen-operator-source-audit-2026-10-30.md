# Qwen 推理优化：上游源码与 PR 演变链核查 v0.3

> 研究日期：2026-10-30，事实来自相关项目 GitHub PR 页面、其文件变更列表与 vLLM-Ascend 官方发行说明。**无可用 GPU/NPU 环境，无本项目实际 Kernel 编译、Profiler 或吞吐测试。** 上游 PR 的自测结果不等于我们复现。当前用户重点为多案例共性研究，而不是建立任何可运行服务。

## 最重要的发现

不能用“原作者提速百分比 + 算子名称”判断优化可移植性，需要连续检查五个关卡：

1. 原作者的 **PR 是否真正合并**；
2. **优化所涉及的具体算子代码是否存在于所用版本**（不是只看到历史提交）；
3. **模型真实形状 / dtype / 运行模式是否满足 dispatch guard**；
4. **图捕获、通信后端、确定性模式和 CPU worker 运行环境是否允许调用**；
5. **对应模型在完整在线链路中是否有实测 + 正确性验证**。

不满足其中任何一条，必须记为「未证明可复用」，而不是优化失败或成功。

## A. AllReduce + residual + RMSNorm / Matmul Fusion

| 证据 | 实际发生的事 | 和 Qwen 相关的研究边界 |
| --- | --- | --- |
| [SGLang #22664](https://github.com/sgl-project/sglang/pull/22664) | 在 `python/sglang/srt/server_args.py` 增加 **Qwen3NextForCausalLM 的自动启用白名单**；PR 仅修改 1 个文件（+3/-1），**并未新写融合 Kernel**。作者在 Qwen3-Coder-Next/H100 TP4 报告 request throughput 5.49→9.41 req/s、TTFT 456.24→167.54 ms | 性能收益来自将已有融合优化路由到适用模型；先检查现有开关和已实现的算子，比盲目重写更重要 |
| [SGLang #12787](https://github.com/sgl-project/sglang/pull/12787) → [#20792](https://github.com/sgl-project/sglang/pull/20792) → [#23402](https://github.com/sgl-project/sglang/pull/23402) | MNNVL 融合方案 **引入→因部分场景卡死撤销→加入后端参数及 PCG 保护后重新引入**；问题与 MNNVL Lamport-style wait loop / Piecewise CUDA Graph capture/replay 交互相关 | [#23402](https://github.com/sgl-project/sglang/pull/23402) 给 `auto/trtllm/mnnvl` 后端选择；MNNVL + PCG 禁用，失败回退必须做正常 AllReduce |
| [SGLang #24629](https://github.com/sgl-project/sglang/pull/24629) | `--enable-deterministic-inference` 下强制禁用 FlashInfer AllReduce 融合；作者复现不同 Batch 导致 logprob 不一致，修复只影响确定性模式 | 同一配置 **默认服务模式可以启用，但确定性验收模式不得启用**；比较输出时需要先定义确定性契约 |
| [vLLM-Ascend #12119](https://github.com/vllm-project/vllm-ascend/pull/12119) | 已合并：删除 `matmul_allreduce_add_rmsnorm` C++/AscendC 相关文件、图融合 Pass、配置项/测试 | 文章使用的是 **旧版独立分支**，不能把旧版融合路径视为 vLLM-Ascend 后续版本的现成功能 |

**重要版本边界**：[vLLM-Ascend v0.23.0 发布说明](https://github.com/vllm-project/vllm-ascend/releases/tag/v0.23.0) 将权重预取 / 多流重叠门控 / matmul-allreduce 等列为准备弃用；[v0.26.0rc1 发布说明](https://github.com/vllm-project/vllm-ascend/releases/tag/v0.26.0rc1) 明确列出这些路径的删除。对应 [#11956](https://github.com/vllm-project/vllm-ascend/pull/11956) 和 [#11949](https://github.com/vllm-project/vllm-ascend/pull/11949) 均已合并。**但这不意味着新版本完全没有任何共享专家多流优化或其他预取机制：这里仅指特定被删除的实现与开关。**

## B. GDN：Prefill 和 Decode/MTP 必须分成两个问题

### Prefill：FlashInfer #3001 → 修复 #3155 → vLLM 适配 #40717

- [FlashInfer #3001](https://github.com/flashinfer-ai/flashinfer/pull/3001)：CuTe-DSL Blackwell 专用 GDN Prefill Kernel，含基准源码与形状表。
- [FlashInfer #3155](https://github.com/flashinfer-ai/flashinfer/pull/3155)：发现使用 `HardwareInfo().get_max_active_clusters(1)` 获取 SM/cluster 数在 vLLM EngineCore 的子进程环境里可能返回错误值，使 persistent scheduler 无法分配所有工作并在首次执行时 **死锁**；改为 `get_num_sm(q.device)`。该修复是 vLLM 新 Kernel 可用性的前置依赖。
- [vLLM #40717](https://github.com/vllm-project/vllm/pull/40717)：启用 FlashInfer 路径时按 `backend in {flashinfer,auto}`、CUDA、SM90 或 Blackwell SM10x、`head_k_dim=128`、CUDA major >=13 等条件进行分派；否则回退 Triton/FLA。官方 PR 也指出 #3155 的修复先于启用。
- 核对源码：`flashinfer/gdn_kernels/blackwell/gdn_prefill.py`、`vllm/model_executor/layers/mamba/gdn_linear_attn.py`。此融合与得物的 **910C GDN Decode** 不同，算子、阶段和实现框架均不同。

### Decode + MTP：vLLM #51674 的“合入但公开模型无法命中”

- [vLLM #51674](https://github.com/vllm-project/vllm/pull/51674)：合并了 `fused_gdn_decode_post_conv_mtp`，将 gating、recurrent state rewind/update、RMSNorm 融合。CUDA 核心文件 `csrc/libtorch_stable/gdn/fused_gdn_decode_kernel.cu`，分派逻辑 `vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py`。
- 源码实际包含 `_can_use_fused_gdn_mtp_decode`，要求 `spec_sequence_masks != None`、普通 `num_decodes == 0`、`num_spec_decodes > 0`、recurrent state BF16/FP32、`gdn_decode_kernel == "cuda"`、`num_v_heads == 8 * num_k_heads`、state index 存在/宽度不超过 8，以及 fused CUDA op 已构建。
- PR 报告的冷缓存 Kernel microbenchmark **1.17–2.20×** 是作者在特定形状上的测量；但作者指出他检查的公开 Qwen3.5 checkpoints（示例：0.8B 16/16、35B-A3B 16/32、397B-A17B 16/64）**均不满足 8:1 head 比例，真实公开模型不会命中这条新分支**；没有给出此融合对这些公开模型的完整 lm_eval 提升。
- 这不是说 CUDA Kernel 不能运行，也不能推断其他模型不能命中；仅能说 **当前被核查的公开模型布局不满足该 PR 分派条件**。必须把「PR merged」「microbench works」「real checkpoint dispatch hits」「E2E helps」拆成四个独立状态。
- 已新增 [离线条件检查器](../tools/check_kernel_applicability.py) 与 [输入夹具](../research/source-traces/qwen35-35b-layout-pr51674.json)。无需真实显卡，只判断 PR 文本和源码中已明确的条件；返回 `ruled_out_by_known_guard / insufficient_metadata / documented_guards_satisfied_not_runtime_verified`，不预测速度。

## C. MoE Expert GEMM：共性在性能维度，源码不能生搬硬套

- [得物 Qwen3.5 910C 下篇](https://mp.weixin.qq.com/s/GXaZWhIZ25ifH07iaTxfZQ) 讨论共享专家与 routed experts 计算/通信重叠。
- vLLM-Ascend [#11956](https://github.com/vllm-project/vllm-ascend/pull/11956) 删除特定 multistream overlap gate（PR 称 low-value/underutilized），[#11949](https://github.com/vllm-project/vllm-ascend/pull/11949) 删除特定 weight prefetch 功能。这给出**工程维护成本/兼容性反例**；不能误解为所有 MoE overlap 都应禁止。
- [腾讯 HPC-Ops + SGLang](https://www.lmsys.org/blog/2026-08-07-hpc-ops-sglang/) 侧重 Fused MoE / Router GEMM 的小矩阵性能。
- [NVIDIA TensorRT-LLM MoE Perf Guide](https://nvidia.github.io/TensorRT-LLM/latest/developer-guide/moe-perf-guide.html) 指出均匀专家路由微基准可能与实际偏斜路由排序不一致。
- 待深入的核心变量：`tokens_per_expert` 分布、`top_k`、`shared_expert`、`ep/tp`、dispatch/combine 通信、精度、grouped-GEMM M/N/K、调度侧 CPU gap。

## D. 统一的跨案例判定模型（研究规则）

| 状态 | 判定要求 | 不得推断 |
| --- | --- | --- |
| `idea` | 来源提出设计或可行性 | 已有代码 |
| `code_merged` | 上游 PR 已合并，保存 SHA/路径 | 模型会调用 |
| `guard_eligible` | 模型静态结构和软件配置满足所有已知 guard | 实际调度成功、没有隐藏前提 |
| `runtime_hit` | 有 Trace/日志确认真实调用新 Kernel | 性能显著更好 |
| `microbenchmark_gain` | 算子级同形状重复测量，统计误差受控 | 端到端也提速 |
| `e2e_gain` | 同模型/同数据/同硬件/同拓扑 A/B + 正确性回归 | 其它平台也提速 |
| `reverted/removed` | 后续 PR 删除或关闭该路径 | 所有等价优化机制被否定 |

**不能用一个速度数字覆盖全部状态**。特别关注两个不同层次的“没命中”：源码函数实际不存在，以及函数存在但模型 guard 未通过。

## E. 文件、证据与离线验证

- PR 演变链：[`research/source-traces/qwen-operator-pr-lineage-2026-10-30.json`](../research/source-traces/qwen-operator-pr-lineage-2026-10-30.json)，12 个合并 PR 和 5 条可溯源的撤销/修复/依赖边。
- PR 数据核验：[validate_operator_pr_lineage.py](../tools/validate_operator_pr_lineage.py)，验证 SHA 形式、PR URL、关联端点与来源。
- 适用条件：[check_kernel_applicability.py](../tools/check_kernel_applicability.py)；该脚本不访问外网，不加载模型，不运行硬件。
- 单元测试分别覆盖 Qwen3.5 head 比例、MTP speculative tokens >8、数据未知、Blackwell HeadDim/CUDA、SGLang Deterministic Fusion、PR rollback 与 provenance。

```bash
python3 -m unittest discover -s tests -v
python3 tools/validate_operator_pr_lineage.py
python3 tools/check_kernel_applicability.py --mode vllm_gdn_mtp_51674 --facts research/source-traces/qwen35-35b-layout-pr51674.json
```

**下一步**：逐个检查模型官方 `config.json` 和上游自动 dispatch 的版本变化；为热门 Kernel 建立适用性矩阵，包括 NVIDIA、Ascend 上不同模型结构和动态 batch；对所有融合添加确定性/返回值回退/graph capture 的失败用例。不要在没有相关卡型的情况下制作虚构的 NPU 性能表。
