# 项目成果档案｜昇腾大模型推理与算子优化

> 原“Qwen 推理优化知识图谱与智能决策系统”为首期案例研究/软件原型的历史名称。现在的项目范围扩大到昇腾硬件、芯片内部资源、推理软件栈、跨模型算子加速与机制讲解；原有 Qwen 证据与代码完整保留。
>
> [V2 详细设计](design/ascend-explorer-v2/DESIGN.md) · [Notion V2 设计记录](https://app.notion.com/p/40b7bbed135281d78e69ca7cd395b56e?pvs=204)。**V2 仅设计，未实现正式页面；无 NPU 实测。**

> 项目负责人主导研究方向与验收口径，AI 协作完成资料分析、规则实现、测试和软件原型。当前为**阶段一：研究与离线软件原型已交付**，尚未进行真实昇腾推理性能实验。  
> 归档时间：2026-11-01。代码事实源为本仓库 Draft PR #4，未合并 main。

## 1. 项目定位与要解决的问题

Qwen 大模型推理优化往往散落在开源 Kernel、框架 PR、博客基准和不同平台部署案例中。同名“GDN / MoE / AllReduce 融合”在不同模型结构、精度、Prefill/Decode 阶段、NPU/GPU 和框架版本下并不等价。过去直接引用其他团队的性能倍数，会形成错误的技术选型和不可信的项目结果。

本项目自主建设一个**多案例证据驱动的推理优化研究与决策系统**，研究流程为：

`公开技术证据 → 来源分级与版本校验 → 模型/硬件/负载结构分析 → 适用性规则推断 → 候选优化与失败约束 → 实验与回退合同 → 条件性结论与可视化 → 未来实测回写`。

这里的“自主”指**研究方法、证据数据结构、关系图谱、校验逻辑、决策流程和软件原型**；不意味着本项目自行编写了得物 / SGLang / FlashInfer 的原始 Kernel，也不意味着已复现其性能数据。

## 2. 研究与实现的完整过程

| 阶段 | 研究 / 研发工作 | 项目产生的实际成果 |
|---|---|---|
| 技术调研 | 研究得物 910C、SGLang AllReduce、FlashInfer GDN、vLLM、NVIDIA、Google TPU、HPC-Ops 等案例 | 15 条跨平台结构化研究案例，分级记录作者实测、微基准、配置/提案 |
| 模型拆解 | 读取五款 Qwen 官方配置，分析混合注意力、Dense/MoE、GDN Head 比例与路由 | 五模型静态结构表、特定 Kernel Guard 排除方法 |
| 源码与负例治理 | 检查 12 个上游合并 PR 的源文件、提交、撤销/修复关系，整理 8 条失败与限制 | 可溯源 PR 演变链、失败经验知识库、误关联修正 |
| 证据图谱 | 设计 Case / Model / Operator / Mechanism / PR / Failure 等节点及有来源的关系 | **75 节点、202 条关系**的离线图谱，全部包含证据类型与来源约束 |
| 规则与算法 | 设计场景过滤、模型适用、Prefill/Decode、Graph、MoE、GDN、Dense SP、MTP 等约束 | 10 条可证伪假设、5 组研究场景、6 阶段验证决策流水线 |
| 软件实施 | 开发标准库脚本、离线查询器、自包含 HTML 仪表板、JSON 导出和 CI 构建 | 可实际打开与交互的研究工作台、自动构建 ZIP/HTML/JSON |
| 工程验收 | 静态输入验证、图谱引用完整性、错误路径排除、规则测试、浏览器布局 | **100 项 Python 自动化测试、精确 HEAD CI 全绿**；浏览器交互已核查 |
| 性能实测 | 未来接入 Ascend NPU、固定框架/模型版本、Profiler 与真实 A/B | **尚未进行**，没有本项目的 TTFT/TPOT/TPS 加速结果 |

## 3. 五个可被清晰认定为本项目工程创新的点

1. **从跨案例知识汇总升级为证据数据资产**：为公开结果保留原作者、模型、硬件、负载、测试层级、源码版本，避免“论文加速倍数”脱离上下文。
2. **把 Kernel 的“代码合并 / 可命中 / 真正有效”分开处理**：设计适用性静态检查和证据等级。例如 vLLM #51674 历史 CUDA GDN MTP 专用分支要求 Value/Key Head 比例为 8:1，所研究五模型不满足，不能将其微基准收益认定为我方部署收益。
3. **将失败经验和移除历史纳入同一个图谱**：记录死锁、数值确定性回归、特性删除、Shape Guard 不匹配和微基准统计噪声；同时提供后续技术复用时的负面约束。
4. **形成可证伪而非伪预测的优化决策引擎**：每条候选都给出“何时可能有效、如何检查、应测哪些指标、什么情况判失败、怎么回退”；没有设备时不输出虚构速度。
5. **端到端交互式成果展示与可持续归档**：通过六阶段链路、五种场景、可视化选择和 Amdahl 理论灵敏度分析，将研究结果转成能实际操作的离线系统。

## 4. 我们目前真正拿到的结果

- **研究成果**：15 案例、5 Qwen 模型、12 源码 PR、8 条失败/限制、五类优化方向。
- **数据成果**：75 个节点、202 条关系，来源可追溯，派生标签明确标记为“非因果关系”。
- **软件成果**：离线来源数据校验、模型结构分析、Kernel 适用性检查、证据图谱生成、结构化检索、决策规则引擎和自包含 HTML 看板。
- **方法成果**：完整的证据→结构→瓶颈假设→优化候选→正确性/稳定性约束→A/B 验收→经验回写闭环。
- **质量成果**：精确 HEAD `c1a61573cc89cebc93098238e7c1284001b614a2` 的 [研究自动化测试](https://github.com/cao772/ascend-llm-inference-optimization/actions/runs/41166102288) 返回 **SUCCESS（100 项测试）**；[全链路 HTML 和 JSON 构建](https://github.com/cao772/ascend-llm-inference-optimization/actions/runs/41166097516) 返回 **SUCCESS**。
- **明确边界**：尚无 GPU/NPU 环境、尚无模型真实推理/Profiler、尚无 NPU 算子重写和实测吞吐收益；5 个硬件/负载场景是**实验设计**，并非实际测试结果。

## 5. 可用于项目汇报的成果摘要

**长版（技术汇报）**

> 本人主导建设了面向昇腾算力的 Qwen 大模型推理优化知识图谱与智能决策系统，针对开源优化案例分散、模型与硬件适用性不明确、失败经验难复用等问题，形成了“多源证据治理—源码版本与模型约束分析—优化机制图谱—可证伪决策推演—实验验证合同—可视化交付”的研究与软件原型。项目首阶段沉淀 15 条跨平台优化案例、12 个上游 PR、8 条失败与限制记录、5 款模型结构数据，构建 75 节点/202 关系的证据图谱，形成 10 条研究假设与 5 组场景推演；100 项自动化测试通过，并实现可离线运行的交互工作台。当前已交付研究决策软件原型，后续将结合真实 Ascend NPU Profiler 与 A/B 验证进一步形成推理性能优化实证。

**短版（项目成果展示 / 个人介绍）**

> 负责 Qwen 推理优化证据驱动决策系统的技术研究与原型实现，构建 75 节点 / 202 关联的知识图谱，形成 10 条优化推断规则、5 组模型场景及配套可视化工作台，100 项自动化测试通过，实现从开源案例研究到技术适配、风险校验与未来实机验收的全链路闭环。

## 6. 代码、证据与现有工作台

| 项目资产 | 位置 |
|---|---|
| 长期研究档案 | [Notion 研究总账](https://app.notion.com/p/4097bbed1352816fad17d3102052812e) |
| 独立项目成果档案 | [Notion：个人项目成果（阶段一）](https://app.notion.com/p/40b7bbed135281dabe95c10c5206be42?pvs=204) |
| 源码研发记录 | [Draft PR #4](https://github.com/cao772/ascend-llm-inference-optimization/pull/4) |
| 完整链路研究报告 | [docs/qwen-end-to-end-inference-research-v1-2026-10-31.md](docs/qwen-end-to-end-inference-research-v1-2026-10-31.md) |
| 完整证据图谱说明 | [docs/qwen-evidence-atlas-v2-guide-2026-10-31.md](docs/qwen-evidence-atlas-v2-guide-2026-10-31.md) |
| 数据与规则 | [15案例](research/cases/qwen-optimization-cases-2026-10-30.json)、[12 PR](research/source-traces/qwen-operator-pr-lineage-2026-10-30.json)、[8风险](research/failures/qwen-operator-failure-modes-2026-10-31.json)、[10假设](research/decisions/qwen-fullchain-hypotheses-v1.json) |
| 核心生成工具 | [tools/build_qwen_evidence_atlas.py](tools/build_qwen_evidence_atlas.py)、[tools/build_qwen_decision_pipeline.py](tools/build_qwen_decision_pipeline.py)、[tools/render_qwen_decision_dashboard.py](tools/render_qwen_decision_dashboard.py) |
| 构建产物 | [GitHub Actions 完整 HTML/JSON 原型](https://github.com/cao772/ascend-llm-inference-optimization/actions/runs/41166097516) |

## 7. 下一阶段实机研发与验收边界

项目未来可进入“Ascend 实机推理优化”阶段，但只有在硬件、CANN/驱动、模型权重与 vLLM-Ascend 具体版本都确定后，才能按顺序开展：模型加载 → 正确性基线 → Profiler 分阶段测量 → 单变量优化 → 有回退的 A/B → P50/P95/吞吐联合验收。

本阶段成果不能改写成“自主研发了他人的 Kernel”“已优化 910C 推理速度 X 倍”或“已经部署上线”。**独立项目的真实性与价值，来自已完成的研究系统、工程方法、代码和可验证的软件交付。**

## 阶段二网站研发：昇腾大模型推理与算子优化交互展馆（V2.2）

独立于 Qwen 首期决策原型，新增九模块、离线可运行的昇腾硬件—软件栈—算子—推理流程讲解网页，已将原有 75 节点 / 202 来源关系的研究图谱嵌入展馆。V2.2 继续补充了：

- **有依据的具体设备规格**：华为 Atlas 300I Duo 整卡 FP16/INT8、48/96 GB LPDDR4X 与整卡带宽；Atlas 800I A2 的 4U/8 模组/可选整机全互联等参数。产品层级、精度单位和可选配置单独标注，不与单 NPU 指标混淆。
- **版本锁定的兼容解释**：按 vLLM-Ascend 0.30.0 官方安装指南记录 HDK/CANN/NNAL/PyTorch/TorchNPU/Triton/vLLM 的整套共同验证环境；展示 Qwen、GLM、DeepSeek 支持表的*文档范围*，不等于本机实测。
- **真实可点的 AI Core 数据流教学**：针对官方特定架构的 AIC Cube 7 帧、AIV Vector 5 帧，SVG 逐步高亮算子搬入、计算、搬出与可能的访存问题。是机制讲解，而非模拟 NPU 利用率。
- **质量保障**：独立 JSON 来源契约 + Python 单元测试 + Chromium/WebKit 多尺寸端到端交互回归，新增设计均保留出处与“不支持推断实测”的限制。

[V2.2 完整技术来源报告](design/ascend-explorer-v2/docs/official-hardware-and-ai-core-v2.2.md) · [网站源码](design/ascend-explorer-v2/site/) · [V2 任务跟踪](https://github.com/cao772/ascend-llm-inference-optimization/issues/7)。

当前可确认为自主研发的成果：证据采集与分层模型、教学图示与交互前端、离线构建、自动回归。**尚不能确认昇腾算子重写已完成，或实际模型 TTFT/TPOT/TPS 已提高。**
