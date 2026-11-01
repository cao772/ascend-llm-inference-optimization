# V2.6｜Attention、MoE、GDN、多卡通信：真实来源与反例数据扩充

日期：2026-11-01。项目：《昇腾大模型推理与算子优化》。

> 本轮新增 7 条可追溯的外部技术记录（7 组带双端点的观察指标、18 项单点或效果值），覆盖 Attention、MoE、GDN 与 HCCL/Prefill 通信。与 V2.5 的 8 条原始案例合起来是 **15 条来源型案例**；合并数据不等于 15 场独立可重复实验。本项目真正 NPU 原始测量仍为 0。不能把 PR 或 Issue 数值写成我们的性能成绩。

## 1. Attention：不必要的 QKV Padding

**来源**：[vLLM-Ascend PR #13787](https://github.com/vllm-project/vllm-ascend/pull/13787)，查阅时 PR 为 **Open、未合并**。作者在 Ascend 950、自有多模态模型、`FlashAttentionScoreV4` 上测试，关注 head_size=80 时先 padding 到 128 再切片的开销。

- 调整前算子模式：`3*(slice+pad)+FA+slice`。
- 调整后：`3*slice+FA`，通过 `VLLM_ASCEND_MM_ENCODER_ENABLE_PAD=0` 控制。
- PR 作者报告：FA 单算子性能 **+6.2%**；ViT 单层 **+1.7%**。作者还描述删除小算子带来的贡献约 +2%，但没有完整 before/after 原始时间数据，因此数据库只存百分比报告，不填虚构的 μs。
- **边界**：只有底层 FA 支持原始非对齐 head_size 才应关闭外部 Padding；head_size=128 等情况不能套；也不是普遍的语言模型解码收益。

## 2. MoE：两组完全不同性质的实测

### 2.1 W8A8_DYNAMIC GMM1 Scale 的冗余转型探针

**来源**：[GitHub Issue #18452](https://github.com/vllm-project/vllm-ascend/issues/18452)，属于未完成的性能优化提案。作者报告在 Ascend 910B2C、CANN 9.1.0 B243、torch_npu 2.10.0.post4 上执行独立探针：

| Scale 形状 | BF16→FP32→BF16 单次摊销区间中位数 | 临时 BF16 数据 |
|---|---:|---:|
| [16,6144] | 5.495 μs | 192 KiB |
| [128,768] | 5.591 μs | 192 KiB |
| [128,6144] | 5.485 μs | 1.5 MiB |

30 次预热、7 轮×每轮 200 次 cast，使用 NPU Events。数值是摊销流区间，含可能的调度空隙，不是孤立 Kernel 时间。一个小型真实 INT8 NZ GMM 检查证明转换前后输出逐 bit 一致，但 **没有真实模型 TPOT、TTFT 改善数据**。EPLB 可能重映射权重，重复利用旧 BF16 scale 会出错，不能作为无条件可用的优化。

### 2.2 MoE 细粒度 TP 的显存节省与 TPOT 权衡

**来源**：[vLLM-Ascend Fine-grained TP 官方特性指南](https://github.com/vllm-project/vllm-ascend/blob/main/docs/source/user_guide/feature_guide/Fine_grained_TP.md)。作者在 **32 张 Atlas A2 64GB 推理卡、DP32+EP32、DeepSeek-R1-W8A8、PD 分离 Decode、TP=8、batch=24** 记录：

| 模块 | 每卡权重显存节省 | TPOT 变化 |
|---|---:|---|
| o_proj | 5.8 GB | **+1.5 ms（退化）** |
| LM Head | 1.51 GB | -1.2 ms |
| MLP | 0.9 GB | -1.0 ms |
| Embedding | 1.51 GB | -1.0 ms |
| 合计 | **9.72 GB/card** | 官方只声明略有净改善，没有给一个完整的基线到最终时延端点 |

**边界**：细粒度 TP 只支持 MoE；o_proj 与 MLP 还限制在 PD 的 Decode 端、Graph、TP=1、重计算调度及指定 KV Connector 等条件。四项 TPOT 增量没有足够证据可简单相加当最终整模型净收益。这份资料比纯理论教学更有价值：**扩大模型容量的优化也可能增加通信成本，让其中一项操作变慢**。

## 3. GDN：内存分组错误和投机推理开销

### 3.1 KVPool 与 GDN group 合并失效

来源：[Issue #20352](https://github.com/vllm-project/vllm-ascend/issues/20352)。v0.26 集成构建的 Qwen3.8 Flash-Next hybrid QSA/GDN 在 A3 16 卡、TP8/DP2、最大上下文 262144、MTP3、AscendStore KV transfer 条件下，开启外部 KV Transfer 导致合法分组合并被禁用，**4 个 groups 变为 39 个**；服务启动要求 **19.45 GiB KV**，可用 **15.47 GiB**，因资源不足校验失败。

**边界**：这是可被配置触发的内存与启动故障，不是“4→39 导致模型 TPOT 降低”或独立 A/B；同一 Issue 的后续多项联合修复产生的缓存命中结果已在 V2.5 留存，不能重复当新加速实验。特别注意报告的产品是**v0.26 线上的特定集成构建**，并非未经修改的通用 v0.26 发布包。

### 3.2 采用更长推测树并不保证快

来源：[RFC #18797](https://github.com/vllm-project/vllm-ascend/issues/18797)：作者描述 Qwen3.8-27B GDN 模型在 2×A2B3/TP2 下，DSpark 的 Accept Length **4.9→5.8 tokens**，但同时指出 GDN 状态搬运开销，并且代码在私有仓库迭代。**没有可配对的 TPOT/TPS 测量，不能宣称提速**。

## 4. 通信：既要有成功案例，也要展示失败与性能回退

### 4.1 HCCL AllReduce 偶发慢路径

来源：[Issue #10088](https://github.com/vllm-project/vllm-ascend/issues/10088)：Qwen3.6-27B hybrid GDN+FullAttn，vLLM-Ascend 0.20.2、CANN 9.0.0、TP4、10 并发请求，作者比较执行模式：

| 执行模式 | TPOT 中位数 | 输出吞吐量 | 慢路径 |
|---|---:|---:|---|
| FULL_DECODE_ONLY | **1719.37 ms** | 5.82 tok/s | 每次 execute_model 有一次约 1051 ms 的异常 allReduce |
| PIECEWISE | **105.90 ms** | 90.01 tok/s | 未报告该异常 |
| eager | **208.04 ms** | 46.95 tok/s | 未报告该异常 |

**边界**：这是在相同作者环境下的不同执行模式故障调查，不能说“PIECEWISE 在所有昇腾型号上比 FULL 快”。同环境 TP4 的稠密 Qwen3-8B 没触发该异常。1051ms 是*一次通信算子*的异常值，不是 TPOT 整步时间。

### 4.2 GLM-5.2 Prefill DCP 通信回退

来源：[Issue #13973](https://github.com/vllm-project/vllm-ascend/issues/13973)，GLM-5.2 W4A8，Ascend 910×16、TP8/DCP8/EP32，对比 v0.23 与 v0.26rc，非重叠 DCP 通信时间占单步比例从 **1.58%→8.19%**。作者报告 `DispatchFFNCombineW4A8` 单次 **15.2→22.6ms**、TTFT P50 **7617→54296ms**。不同 vLLM/CANN 构建，而且两边 bench output-len 分别为 **700 与 1**，QPS/TPOT/总吞吐不属于同负载可比指标；即使 TTFT 是首 token 时间，仍需要独立复现实验排除版本与调度干扰。

## 5. 这轮对原研究系统的真实修改

- [V2.6 原始来源数据 JSON](../content/cross-operator-evidence-v2.6.json)：7 条案例、7 组含双端点但未认定为隔离 A/B 的数值、18 项独立记录值；保留每条 PR/Issue 当前状态。
- [交互网页](../site/)：和 V2.5 的 8 个历史案例合并浏览，总计 **15 条来源型案例**；新增 Attention、MoE、GDN、多卡通信的专属筛选。无双端点的指标只显示作者单值，不伪造「前后时间」。
- [专项结构测试](../../../tests/test_ascend_cross_operator_evidence_v26.py)：核对来源、数字、精度、原始报告状态与不因果判断；网站 [Chromium + WebKit 回归](../site/browser_cross_engine.py) 涵盖 15 案例、Attention 报告、MoE 显存收益/退化反例、GDN 分组与通信异常。
- 仍保留 V2.5 [历史数据 JSON](../content/experiment-evidence-v2.5.json) 与 [24 对 CSV 审计表](../tools/export_evidence_csv.py)。**新加的 7 组“有两端点”也不应被不加区分地并入“已证实 A/B”**。

## 6. 证据还缺什么

1. Attention 需要更多直接可测的 FA 各阶段算子耗时、准确性与版本记录。PR #13787 未合并，不等于产品默认已提供此能力。
2. MoE 需要同时记录 GMM、AllToAll、共享专家、路由负载、EP 规模、EPLB 的完整成本；单独 cast 探针不能代表最终模型收益。
3. GDN 需要 state、cache 分组、回滚正确性以及结构混合模型逐步 TTFT/TPOT。
4. HCCL 通信需要逐组的 raw Profiler `communication_matrix.json`、`step_trace_time.csv` 与同形状多次 A/B，而不是把问题报告当定论。
5. 若没有目标昇腾硬件，所有项目自身硬件实测仍应保持 **0**。本轮只从公开来源深化研究与可视化。
