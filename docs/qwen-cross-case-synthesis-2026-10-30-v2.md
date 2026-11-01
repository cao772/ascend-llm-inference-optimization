# Qwen 多案例算子优化共性研究 v0.2｜15 个来源与“不能套用”的边界

> 2026-10-30。**没有任何本项目的 GPU/NPU/TPU 真实性能测量**。所有加速数值来自原作者、厂商或开源基准；类型、环境和统计口径不一致。结构化记录见 [15 条案例 JSON](../research/cases/qwen-optimization-cases-2026-10-30.json)，上版 [v0.1](./qwen-cross-case-synthesis-2026-10-30.md)。

## 1. 第二批新增的 6 个案例

| ID | 对象 | 所能确认的事实 | 本项目的结论边界 |
| --- | --- | --- | --- |
| QINF-010 | [TensorRT-LLM/Qwen3.8-2.4T-A95B-FP8](https://nvidia.github.io/TensorRT-LLM/latest/deployment-guide/deployment-guide-for-qwen3.8-qwen3.5-on-trtllm.html) | GB300、16 GPU、TP16/EP1、并发1、8192→1024，MTP3 条件下从 133.502→383.051 output tok/s/user | **接受草稿数人为控制在 2.3**；不是实际业务平均接受率，更不能预测任何昇腾上的收益 |
| QINF-011 | [TensorRT-LLM MoE Perf Guide](https://nvidia.github.io/TensorRT-LLM/latest/developer-guide/moe-perf-guide.html) | Qwen3.8 的结构包括 512 个专家、每 token 选择 10 个；`bench_moe` 在完美路由下选快配置，真实路由可偏斜 | 该指南对于其他模型给了端到端交叉验证，**不能将其他模型的改善/退化统计说成 Qwen3.8 结果** |
| QINF-012 | [TileOPs MoE 基准](https://tile-ai.github.io/TileOPs.github.io/benchmarks/moe/) | Qwen3-30B b1 FusedMoE 0.0396ms vs 0.0413ms（1.04×）；另一个 EP8 grouped-GEMM shape 0.0213ms vs 0.0320ms（1.51×） | 站点说明 **0.95–1.05× 是近似同级/测量噪声**，因此 1.04× 不得宣传为有效提速；仅 GPU device/kernel 时间 |
| QINF-013 | [vLLM XPU-kernels Qwen3.5 跟踪](https://github.com/vllm-project/vllm-xpu-kernels/issues/172) | GDN L2Norm、chunk_fwd、conv1d、RMSNorm 等子任务清单 | **规划 Issue，不是测试报告**；需追踪每个 PR 的合入状态 |
| QINF-014 | [vLLM Speculators MTP](https://docs.vllm.ai/projects/speculators/en/latest/user_guide/algorithms/mtp/) | 用已有 Qwen3.5/Qwen3-Next 原生 MTP 头转换、微调、再拼回模型；冻结 embedding 与 LM head | 方法存在，不代表接受率或 TPOT 已有改善 |
| QINF-015 | [TensorRT-LLM Qwen3.5 配置](https://nvidia.github.io/TensorRT-LLM/deployment-guide/deployment-guide-for-qwen3.5-on-trtllm.html) | 4×B200、TP4/EP4、attention DP、CUTEDSL、graph capture 等吞吐方向配方 | 配置范例不是 `A/B measured speedup`，只能作为未来独立测试的候选 |

本批 6 条里，2 条包含对应模型/算子测量证据（QINF-010/012），其余 4 条是基准方法、配置或计划。数据库现为 **15 条：9 条含外部报告或微基准数据、6 条没有可归因测量数据**。

## 2. 从 v0.1 到 v0.2，认识发生的三点变化

### H6｜专家路由偏斜是 MoE 的独立变量

- 模型 `num_experts` 与 `top_k` 只是结构约束；专家负载（每专家 Token 数分布）决定 GEMM 形状、dispatch/combine 通信和 tail latency。
- [NVIDIA MoE Perf Guide](https://nvidia.github.io/TensorRT-LLM/latest/developer-guide/moe-perf-guide.html) 用 `bench_moe` 做完美均匀路由微基准，并承认真实路由偏斜会打破最优配置排序。
- 假设：未来不能只复刻别人汇报的 `token_count, hidden_size, top_k`，还要固定 `expert_load_histogram`、`max/mean load`、`skew`、`dispatch time` 与 `combine time`。
- 此假设可以跨 NPU/GPU 借鉴，但特定的 NVLink/HCCS/PCIe 协议实现不可共享。

### H7｜投机解码的接受率必须与算子优化区分

- MTP 不是“开关打开就快”。draft 成本、target verify 成本、MTP token 接受率和捕获尺寸共同决定端到端 TPOT。
- [Qwen3.8 GB300 的受控接受率案例](https://nvidia.github.io/TensorRT-LLM/latest/deployment-guide/deployment-guide-for-qwen3.8-qwen3.5-on-trtllm.html) 显示很高的低延迟速度，但人为控制平均接受草稿数 **2.3**，不是自然提示词分布。
- [vLLM Speculators](https://docs.vllm.ai/projects/speculators/en/latest/user_guide/algorithms/mtp/) 提供原生 MTP 头的领域微调方法，有助于提高特定业务语料的接受率，但本研究尚没有其收益数据。
- 下一步研究中分别记录 `draft_length`、`accepted_draft_mean`、`verify_batch_shape`、`graph_coverage`、`sampler_mode` 与 `dataset_domain`。不同接受率的性能数字不得横向排序。

### H8｜不要把微小算子优势误判为显著提速

- [TileOPs 阅读指南](https://tile-ai.github.io/TileOPs.github.io/benchmarks/reading/) 明确 0.95–1.05× 属于相近/测量噪声区间；因此 Qwen3-30B BF16 b1 FusedMoE 1.04× 在其准则下 **不是显著胜出**。
- 相反，特定 grouped-GEMM 的 1.51× 可以作为“值得复测的 shape”，也只限该算子该形状。
- 对我们未来的研究：每条测量保存重复次数、统计量、误差带、计时范围（kernel device/CPU/E2E）、精度输入和基线代码版本。不因为数据写了 `×` 就声称成功。

## 3. 更新后的共性标签频次（仅 9 条含外部测量的案例）

| 技术机制（人工标注） | 案例数量 |
| --- | ---: |
| memory_traffic | 9/9 |
| fusion | 5/9 |
| kernel_specialization | 5/9 |
| communication_overlap | 3/9 |
| host_dispatch | 3/9 |
| routing | 3/9 |
| graph_capture | 2/9 |
| speculative | 2/9 |

这些统计**受人工标注与案例入选偏差影响**，只用来引导下一阶段代码追踪。9/9 的 memory_traffic 不等于“每个案子的瓶颈都由 HBM 限制”，也不等于所有场景都应优先改 HBM。

## 4. 无落地环境时，推荐转向“证据图谱”

代码：[`tools/build_case_graph.py`](../tools/build_case_graph.py)

- 节点包括 `case`、`operator`、`mechanism`。
- 边包括 `case→operator` 与 `case→mechanism`（人工标注的出现关系），以及两条案例间的 `shares_tags`（共享至少 N 个技术机制）。
- 所有关系保留案例 ID → 来源链接，`measured_by_our_project=false`，`performance_comparison_allowed=false`，`code_portability_verified=false`。
- **不把两个案例同时出现的标签当成已证明的算子因果图**。只有具体源文件与函数调用链核对后，才能提升关系证据级别。
- 运行 `python3 tools/build_case_graph.py --min-shared 2 --output build/qwen-case-graph.json` 可离线导出。后续可按同一 JSON 结构接入 Neo4j/NetworkX，但暂不需部署图数据库。

## 5. 未来逐项复现需要具备的“证据合同”

**模型和数据**：model revision / quant precision / workload（prefill vs decode）/ ISL / OSL / concurrency / batch shape / natural vs controlled draft acceptance。

**硬件与软件**：SoC/GPU、die/卡、TP/EP/DP、通信链路、CANN/CUDA、驱动、框架/算子库 commit。

**算子细节**：shape、dtype、shared/routed expert、top_k、expert-load histogram、graph capture、fallback、编译正确性。

**正确性**：固定采样器、随机种子、输出一致性、logits 误差容忍、确定性模式、拒绝采样分布、回归失败。

**测量等级**：proposal、config recipe、microbenchmark、upstream author E2E、ours measured。严禁把相同“MoE”标签视为可复制实现。

## 6. 当前研究边界与下轮优先级

这 15 条数据均已找到公开原文或代码，仍未验证每条上游 PR 的当前提交状态，也没有本地硬件指标。下一轮优先开展：

1. 针对 **AllReduce+RMSNorm、GDN、MoE Expert GEMM** 选择 2–3 条已公开 PR，固定 upstream commit 与函数调用边界。
2. 设计 **MoE 专家偏斜的输入分布协议** 和 **MTP 自然/受控接受率区分协议**（无需硬件即可形成 JSON Schema）。
3. 增补失败案例与回退记录；避免只选成功案例造成偏差。
4. 推进更严格的 source confidence、代码路径、许可证、作者实测/修复状态审核；真实 GPU/NPU 环境到位后再启动编译和速度比较。
