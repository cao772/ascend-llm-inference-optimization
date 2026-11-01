# V2.5｜昇腾推理与算子优化真实证据中心：实验条件、指标和原始来源

研究快照：2026-11-01。项目《昇腾大模型推理与算子优化》。

## 项目这一轮真正新增了什么

- 从 6 篇 **Ascend C 开发文档预览版**中提取不同算子优化案例，分别保留矩阵形状、精度、Tiling、机制、Profiler 指标和反例。
- 从 1 条有完整配置与请求数量的 **vLLM-Ascend GitHub Issue**中提取 A2 与 A3 的两组缓存复用观测；它不是随机对照实验，也没有单变量消融。
- 一共形成 **8 个外部公开报告案例、24 组有前后数值的指标对**（其中 6 个算子案例、2 个服务观测案例）。注意“24 组指标”不是“24 场独立实验”，同一案例含多个相关指标。
- 另外放入 1 条官方 vLLM benchmark **输出文档示例**，单独隔离为 `documentation_example`，不计入真实报告的实验和指标数。
- **本项目自己运行的 NPU 性能测试数 = 0**。网页上的比值仅是逐指标同口径端点之间的算术推导，非重复实验显著性结论。

原始机器可读证据：[experiment-evidence-v2.5.json](../content/experiment-evidence-v2.5.json)。

## 1. 来源证明等级，绝对不能混用

| 标记 | 定义 | 是否能说成我们实测 |
| --- | --- | --- |
| `vendor_developer_preview` | 公开昇腾开发者预览资料，作者陈述自己执行了 Profiling 并给出数值 | **不能**。预览资料还声明存在缺陷风险 |
| `github_issue_report` | 上游 issue 提交者所报告的环境、请求数和指标；未经本项目复测 | **不能**，其中轮次也不是独立 A/B |
| `documentation_example` | 官方教程中用于演示 `vllm bench` 输出格式的数字 | **不能**，且不计入外部实测案例 |
| `project_own_hardware_measurement` | 将来目标设备生成原始 csv/json、环境版本、正确性和重复对照后才可认定 | **当前没有** |

## 2. 六组算子级公开数据

| ID / 技术 | 工作负载 | 最关键指标 | 改变前 → 改变后 | 原始证据 |
| --- | --- | --- | --- | --- |
| ASC-OP-001：分核 | Atlas A2 系列；FP16→FP32；M4096,N5120,K4096 | 完整算子执行耗时 | 12045 → 2532 μs | [Tiling 策略](https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/matmul_tiling_strategy.html) |
| ASC-OP-001：调 Tile | 同场景；base [64,64,256] → [128,256,64] | MTE2 流水 | 2452 → 808 μs | 同源 |
| ASC-OP-001：CFG_MDL | 同一作者的阶段实验 | MTE2 流水 | 808 → 591 μs | 同源 |
| ASC-OP-002：MDL 缓存 | M128,N30720,K1024，FP16，24 AIC / 48 AIV 架构 | 最大 AIC 耗时 / 平均 MTE2 | 83.68 → 53.4 μs / 75.64 → 46.24 μs | [MDL 模板](https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/matmul_mdl_template.html) |
| ASC-OP-003：常量化 | M128,N30720,K64，FP16 | 最大 AIC 耗时 / 平均 Scalar | 10.62 → 7.87 μs / 6.32 → 3.38 μs | [Tiling 常量化](https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/matmul_tiling_constant.html) |
| ASC-OP-004：L2 切分 | A[30720,1024]，B[4096,1024]，FP16；此案例处理器 L2 为192MB | AIC 耗时 | 867 → 805.6 μs | [L2 Cache 切分](https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/matmul_l2_cache_split.html) |
| ASC-OP-005：错峰 | M768,N2048,K6144，FP16；非全载 K、多核 | 算子总耗时 / 平均 MTE2 | 98.72 → 85.68 μs / 90 → 69.87 μs | [K 轴错峰](https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/matmul_multi_core_k_stagger.html) |
| ASC-OP-006：AIV ND2NZ | M1024,N4095,K1024，FP16；B 内轴非 256B 对齐 | 算子总耗时 / AIC 平均 MTE2 | 149.82 → 93.76 μs / 130.77 → 22.85 μs | [AIV 重排](https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/aiv_nd2nz_conversion.html) |

### 2.1 为什么不要只看“提速多少倍”

- **不同口径不可混合**：ASC-OP-001 一次是完整算子时长，另外两次是 MTE2 流水时长；它们不是连续的总耗时。
- **最大值和平均值不同**：MDL 例中的最大 AIC 53.4μs 不是平均 MTE2 46.24μs，不能相除解释“总体性能”。
- **L2 版本依赖特定硬件**：示例中的 192MB 是原文指定处理器的 L2；不是所有昇腾卡的通用配置。该案例文本只明确报告了 MTE2 降幅约 10.7%，没有明确可独立核对的优化后具体 MTE2 终点，数据 JSON 特意填 `after:null`，不反推精确数。
- **AIV 格式重排不是免费**：ND2NZ 的 AIV 平均 MTE2 是新增加的 10.31μs；小矩阵可能因额外同步反而劣化。因此它放在 `reported_only`，不标成“AIV 耗时降低”。
- **不是端到端大模型推理实验**：这些大多数是算子微基准；部署完整 LLM 时，Kernel 是否命中、Prefill/Decode 占比、通信和缓存瓶颈都会决定最终收益。

## 3. 两组模型级真实请求观测：缓存复用不是单变量优化

来源：[vLLM-Ascend Issue #20354](https://github.com/vllm-project/vllm-ascend/issues/20354)，提交者详细说明 2026-10-30 之后三项组合修复的验证。**这是上游提交者报告而非本项目实测**。

**关键实验条件**：A2、A3 各 16 个可见 NPU，TP8/DP2/EP、MTP3；固定请求数据集，两轮每轮 100 个请求、输入 3,028,487 tokens，单请求输入约 20,558～43,508 tokens，输出 cap 700；第二轮不清空外部缓存；两轮缓存命中条件不同。

| 平台 | 轮次 | 有效请求 | 平均 TTFT (ms) | 平均 TPOT (ms) | QPS | 外部缓存命中率 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| A2 | 第 1 轮 | 100/100 | 3990.14 | 19.00 | 0.0641 | 6.12% |
| A2 | 第 2 轮 | 100/100 | 907.67 | 19.11 | 0.0794 | 88.89% |
| A3 | 第 1 轮 | 100/100 | 3893.36 | 16.75 | 0.0712 | 7.20% |
| A3 | 第 2 轮 | 100/100 | 972.83 | 16.93 | 0.0877 | 88.90% |

**解释限制**：第 1 轮不是严格冷缓存、输出长度存在差异、测试构建不同于当前固定版 v0.30.0，且多项修复一起出现。不能把 TTFT 的前后比例当成某个独立 Kernel、单卡型号或缓存修复所造成的加速效果。值得展示的事实是：外部 Cache 命中率提高的两个重复请求轮次中，TTFT 同时显著变化，而 TPOT 并没有相同方向下降。**这正好提醒我们不能只挑选改善的指标。**

## 4. 官方 Benchmark：实验协议与示例数字必须分开

[官方 vLLM-Ascend v0.30.0 性能测试说明](https://docs.vllm.ai/projects/ascend/en/v0.30.0/developer_guide/performance_and_debug/performance_benchmark.html) 包含线上/离线、ShareGPT 请求集、`vllm bench serve`、TTFT/TPOT/ITL/throughput 等格式与示例输出。对我们最有价值的是复现协议和口径，而不是把文档示例当作已跑过的实验。

**正式复现最低验收字段**：设备完整产品 SKU、NPU 数量、Driver/HDK、CANN、NNAL、框架/引擎版本、模型完整 revision 与 dtype/量化、TP/EP/DP、最大上下文和缓存策略、输入/输出 token 分布、并发/请求速率、Warmup、种子、重复运行次数、显存占用及任何错误；指标至少包含 TTFT/TPOT/ITL 的 P50/P95/P99、TPS 和成功率；按 Prefill/Decode 分阶段保存 Profile。缺项不允许声称同负载对照成立。

额外的指标语义参考：[vLLM Benchmark CLI 文档](https://docs.vllm.ai/en/v0.31.0/benchmarking/cli/)——TTFT 是请求发送到首个流式输出，TPOT 通常按单请求排除首 token 的总时间除以后续输出 token 数，ITL 统计连续流式响应的间隔；MTP 场景一个流式 chunk 可能包含多个 token，不能将两者无条件互换。

## 5. 本轮网站和软件实际修改

- 新增 [实验数据 JSON](../content/experiment-evidence-v2.5.json)，将来源、实验负载、指标口径、可比性、反例、不确定性都写入正式契约。
- 在现有 [九展区交互网页](../site/) 的“案例与成果”区域加入 V2.5 实验中心，支持算子/模型服务切换、关键词过滤、按指标细看两端点与单位、工作负载及说明、原始来源跳转，非隔离 A/B 自动标警告。
- 原有 [Atlas A2 Matmul 公开案例](./public-ascend-matmul-evidence-chain-2026-11-01.md)保留，V2.5 新档案覆盖更多操作和服务层结果，但不能把两个文件的重叠记录简单相加当新增独立实验。
- 新增 [数据完整性 Python 测试](../../../tests/test_ascend_experiment_evidence_v25.py)；原有 [浏览器测试](../site/browser_cross_engine.py)加入 8 条案例/类别筛选、Scalar 数值、服务观测标签与文档示例隔离验收。
- 构建脚本仍输出单文件离线 HTML；所有性能数据直接链接公开原文，不需要未授权 API、生产服务或 NPU。

## 6. 下一轮真正要补强的实机工作

下一步不是“再抄几篇资料就宣称实验丰富”，而是优先建立**我们自己的原始日志→实验表→分析视图**：

1. 接入真实昇腾设备后，按固定配置运行官方 bench CLI 与 msopprof，保存原始 CSV/JSON、进程和设备版本；
2. 保留正确性和失败案例；先追踪瓶颈，再改变一个独立变量（Core/Tile/MDL/Graph/Cache）；
3. 在相同 request 数、输入输出长度分布、精度、缓存条件与并发下重复多次做 A/B，统计 P50/P95/P99 和 TPS；
4. 对任何收益标上“本项目实测”、精确硬件、提交 SHA、时间窗和可复现脚本；没有证据的数字仍是 null；
5. 导入本项目的知识图谱，把“适用的硬件与形状、优化机制、反例、收益和回退”做成可检索关系。

**最终研发边界**：本轮 8 组来自公开材料的案例，24 对作者报告的指标，0 项本项目 NPU 实测。素材有价值，但严格意义上的**独立实验证据**必须后续用实际硬件采集。
