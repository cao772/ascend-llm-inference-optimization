# 昇腾 Matmul 优化公开证据链｜2026-11-01

## 0. 研究结论和证据等级

这次找到了一条可以从 **算子形状 → 官方 Tiling API → 芯片资源查询 → 三次优化 → Profiling 作者报告 → 适用限制** 全程追溯的公开证据链。

**结论：** 在 AscendC 开发者预览文档的 *Atlas A2 系列 Matmul* 指定测试场景中，改变分核数、基本块尺寸和大包搬运，确实有作者报告的耗时变化。这个证据支持“这些机制在该环境、该算子负载下可能有效”，**不证明我们的网站已在 NPU 上运行，也不证明昇腾上任意大语言模型的 TTFT、TPOT 或 tokens/s 得到改善。**

来源网站自述为持续开发的预览资料，可能有缺陷。其图示/数值是**公开作者报告**；没有直接交付可独立复核的原始多次运行 CSV、具体处理器子型号、所有环境版本、置信区间或模型级端到端对照。

- [作者报告的 Atlas A2 Matmul 案例：Matmul 算子优化 Tiling 策略](https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/matmul_tiling_strategy.html)
- [华为官方 CANN 8.5.0 Matmul Tiling API 使用说明](https://www.hiascend.com/document/detail/en/canncommercial/850/API/ascendcopapi/atlasascendc_api_07_0671.html)
- [华为官方 SetFixSplit（CANN 8.5.0）](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/850/API/ascendcopapi/atlasascendc_api_07_0681.html)
- [华为官方 GetCoreMemSize（CANN 8.5.0）](https://www.hiascend.com/document/detail/en/canncommercial/850/API/ascendcopapi/atlasascendc_api_07_1034.html)
- [华为官方 msopprof 用户指南（CANN 9.1.X）](https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/910/devaids/optool/docs/zh/user_guide/msopprof_user_guide.md)
- [华为 351x 架构版本的存储对齐规范（只能适用于该架构）](https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/900beta2/opdevg/Ascendcopdevg/atlas_ascendc_10_00065.html)

## 1. 外部算子实测：严格分口径

公开案例的输入是 **M=4096、N=5120、K=4096** 的 Matmul；输入 half/FP16、输出 float/FP32、ND 格式，运行平台记载为 Atlas A2 系列，**未标注可直接确认的具体 SKU**。

| 阶段 | 变更 | 测量口径 | 优化前 | 优化后 | 变化 |
| --- | --- | --- | ---: | ---: | --- |
| 1. 使用更多计算核 | 4→20 个 Cube 核，所述架构的 Tiling SetDim 对应 8→40 | **整算子执行耗时** | 12,045 μs | 2,532 μs | 按端点计算约 4.76× 耗时缩短；作者报告约 4.75× |
| 2. 优化 Tile | baseM/N/K 从 64/64/256 调整为 128/256/64；`SetFixSplit(128, 256, -1)` | **MTE2 流水耗时** | 2,452 μs | 808 μs | 按端点计算约 3.03× 耗时缩短 |
| 3. 批量搬运 | Matmul 模板使用 `CFG_MDL` | **MTE2 流水耗时** | 808 μs | 591 μs | 按端点计算约 1.37× 耗时缩短；相对时间降低约 26.9% |

**禁止混算：** 表中第 1 行与第 2、3 行统计的是不同指标；不能将 12,045、2,532、808、591 画成一条“最终算子耗时连续下降”的曲线，也不能把 4.76 × 3.03 × 1.37 连乘写成最终推理加速倍数。

开发预览原文亦报告了按模型逻辑搬运量与 MTE2 耗时推算的“带宽利用率”2491→3406 GB/s。它不是独立采集的实际 HBM 物理链路带宽值；网站目前只保留直接给出的时间端点，避免概念误用。

## 2. 机制为何合理——结合源码级接口解释

### 2.1 分核并行

原案例使用的配置为 20 个 Cube 核；作者先前只开 4 核。按照该具体架构 Cube/Vector 数量及 API 执行机制，设备运行核数从 4→20，Host 侧 Tiling 使用的 Vector 分片数 8→40。

这是**案例限定的核组比例**，并不意味所有型号都必须按 Vector 数量为 Cube 2 倍来分块。实际多核约束应通过平台接口读取核数和设备型号后计算。

### 2.2 Tile 与访存强度

原文比较过 `[128, 256, 64]` 与 `[128,128,128]` 两组 Tile 的数据读取量，在同样近似 Cube 运算周期下前者读取的 A/B 输入数据更少，且处理 FP32 ND 输出写回时有地址对齐约束。它利用 `SetFixSplit(baseM,baseN,-1)` 固定 M、N，平台 Tiling 选出 K 分块（案例为 64）。

官方 CANN 8.5.0 文档明确：
- 独立的 [SetFixSplit 说明](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/850/API/ascendcopapi/atlasascendc_api_07_0681.html) 对当前版本明确约束：`baseKIn` 只能是 `-1`，`baseM×baseN×sizeof(C_TYPE) ≤ L0CSize`，且分片维度需满足针对 dtype/单核形状的对齐/范围。**手工模型无法取代这些限制检查。**
- 通过 `SetAType/SetBType/SetCType` 指定 tensor 位置、layout 和 dtype；
- `SetShape` 和 `SetOrgShape` 说明当前计算和原始布局；
- `GetTiling(optiling::TCubeTiling&)` 返回芯片/约束相关的 Tiling 数据（失败值需检查）。
  
所以我们 V2.3 的 `TM/TN/TK` 是**仅供教学的手工输入**，**没有调用真正 CANN GetTiling**，不能将手算结果写成设备选出的 baseM/baseN/baseK。

### 2.3 片内容量：有正式 API，但没有跨型号的通用数字

官方 `PlatformAscendC(context->GetPlatformInfo()).GetCoreMemSize(type, size)` 支持查询 L1、L0A、L0B、L0C、UB、L2 等可用存储空间大小，输出单位**字节**。

这支持在未来真实环境内取得具体设备资源约束。但我们**无法从 API 存在推断某一 SKU 的固定 L1 或 L0 大小**，不能把其他版本、其他芯片架构中的某个 512KiB/64KiB 容量复制到所有昇腾 NPU。

另外有官方 **351x 架构版本**的 L1 32B、L0A/L0B 512B、L0C 64B 等对齐约束资料；这些数值只能按其架构与 CANN 版本使用，不能用于推断上述 Atlas A2 实测案例的硬件对齐标准。

### 2.4 MTE2 与大包搬运

作者报告里，Matmul Tensor 从 GM 到 L1 的搬运是主要热点之一。通过 `CFG_MDL` 实现一次搬入多块输入数据，减少过碎搬入引起的效率问题。

真正要验证此机制需：
1. 目标设备实际 dispatch 对应算子/Kernel，并读取 Tiling 信息；
2. 同一负载分别 Profile Cube/MTE2/Scalar 和必要的 GM/片内内存统计；
3. 修改一个因素（核数或 Tile 或搬运），记录重复运行分布与正确性；
4. 观察**整算子**耗时，再观察在完整大模型上的 Prefill/Decode/TTFT/TPOT/TPS；
5. 记录无收益、错误或不兼容的回退结果。

## 3. 此次来源能证明什么、还不能证明什么

| 结论 | 可用证据 | 结论等级 |
| --- | --- | --- |
| Ascend C 有真正的 Matmul GetTiling API | 官方 CANN 8.5.0 API 文档 | 官方接口确认 |
| 可以在 Host Tiling 查询平台存储空间大小 | 官方 GetCoreMemSize 文档 | 官方接口确认 |
| 该 Atlas A2 案例改分核后算子 12045→2532 μs | asc-devkit 预览版作者报告 | 外部报告，未独立复测 |
| 该案例调 Tile 与 CFG_MDL 后 MTE2 2452→808→591 μs | 同一作者报告与 Profiling 图示 | 外部报告，非本项目实测 |
| 指定 351x 架构下存在不同存储单元的对齐要求 | 351x 官方架构说明 | 版本/架构受限 |
| 上述改动可提升任意 Qwen/GLM/DeepSeek 端到端推理 | **没有**对应的模型级 A/B | **证据不足** |
| 我们的 V2.3 数学实验室显示了真实 NPU 内存流量 | **没有**硬件 trace | **证据不足** |

## 4. 数据与网页交付

- [结构化公开实测与 API 证据链 JSON](../content/public-matmul-evidence-2026-11-01.json)，含 6 个原始资料、8 个来源明确的断言，严格标注 `public_author_reported_not_independently_reproduced` 和 `local_npu_profiling_count=0`。
- [网站交互源码](../site/app.js)：新增“公开案例：Atlas A2 上 Matmul 算子性能实测”，按**整算子**和**MTE2**分别展示前后柱条，支持进入源链接及完整适用性说明，明确不做混口径合并。
- [验证脚本](../../../tests/test_ascend_public_matmul_evidence.py) + [真实浏览器校验](../site/browser_cross_engine.py)：检验证据类型、单位、数值端点、网页的明确免责声明以及来源抽屉。
- [GitHub CI](https://github.com/cao772/ascend-llm-inference-optimization/actions/workflows/ascend-explorer-site.yml) 构建离线 HTML 和测试截图。

本研究不下载模型权重、不操作生产环境、不需要硬件即可复核来源和数学分析；只有后续取得昇腾 NPU 才能产生**本项目自己测量的** Tiling、Profiler 及端到端收益。
