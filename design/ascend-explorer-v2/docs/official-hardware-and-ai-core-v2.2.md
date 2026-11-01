# V2.2｜昇腾硬件规格、软件版本与 AI Core 数据流可视化

> 2026-11-01 · 阶段成果是可运行的交互教学网站和有来源的规格数据，不是已完成的昇腾算子移植或真实性能提升。

## 一、这轮解决的三个实际问题

### 1. 官网有具体参数，但此前页面一律写“未核验”

现在把可核实数据按精确产品收录。数据单独存储在 [verified-product-specs-v2.2.json](../content/verified-product-specs-v2.2.json)，不会覆盖没有官方凭据的通用型谱字段。

| 产品 | 采集到的数值 | 数值范围与归属 |
| --- | --- | --- |
| [Atlas 300I Duo](https://e.huawei.com/cn/products/computing/ascend/atlas-300i-duo) | FP16 140 TFLOPS、INT8 280 TOPS；LPDDR4X 48 GB 或 96 GB；总带宽 408 GB/s；功耗 150W | **整张卡**；两种内存容量是可选版本，不可相加。FP16 和 INT8 是不同精度，不能直排。 |
| [Atlas 800I A2](https://e.huawei.com/cn/products/computing/ascend/atlas-800i-a2) | 4U、8 模组、4×鲲鹏920、可选 NPU 全互联整机带宽 392GB/s | **整台服务器**；可选互联带宽不是单 NPU 的内存带宽，不可与 300I Duo 的 LPDDR4X 408GB/s 直接比较。 |

**其他型号**、尤其 910B/910C 的具体卡/芯片映射、内存/算力仍需逐 SKU 核查；本轮没有猜测。

### 2. 版本名字看得见，却不知道哪些组件必须配套

现在网站新增“已验证软件组合”交互视图。基于 [vLLM-Ascend 0.30.0 安装文档](https://docs.vllm.ai/projects/ascend/en/v0.30.0/getting_started/installation.html) 采集：

| 部件 | 文档列示版本 |
| --- | --- |
| Python | 3.12 |
| Ascend HDK（驱动/固件） | 26.1.1 |
| CANN Toolkit + Ops / NNAL | 9.2.0 |
| PyTorch / TorchNPU | 2.10.0 / 2.10.0.post7 |
| Triton Ascend | 3.6.0.post2，适用于 A2、A3、950DT；文档明确不用于 300I DUO / 200I Pro |
| vLLM / vLLM-Ascend | 0.30.0 / 0.30.0 |

**不能把不同发布版本的依赖拆开自由混装**。这张表代表发布文档中一套共同验证的堆栈，不代表用户机器已通过安装、自检或推理吞吐测试。页面提供 A2/A3/300I DUO/950DT 切换，并且对 Triton 等产品族限制显示不适用。

“跨模型”也已显示 [官方模型支持矩阵](https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/support_matrix/supported_models.html) 中的 **Qwen3.5/3.6、GLM-5.3-Flash、DeepSeek-V4.1-Flash** 示例。所有条目展示的是**官方文档列示的 A2/A3 范围**，DeepSeek-V4.1-Flash 更注明文档中的 W8A8 和多节点限制。不能据此声称在具体 SKU、TP/EP、采样精度组合已经跑通。官方网页内容会更新，采集日期已写入 JSON。

完整源数据：[software-compat-v2.2.json](../content/software-compat-v2.2.json)。

### 3. “芯片解剖”原来只是几个按钮和文字，没有数据流执行过程

现增加真实可操作的 SVG 教学通路，支持“矩阵 / 向量”切换、逐步高亮、每一步解释与可证伪的 Profiling 提问：

- **Cube / AIC 典型通路**：GM → L1 → L0A/L0B → Cube → L0C → FixPipe → GM 写回（共 7 帧）
- **Vector / AIV 典型通路**：GM → UB → Vector → UB 结果 → GM 写回（共 5 帧）

每一帧都包含“这一阶段做什么、可能慢在哪里、如何用 trace/Profiler 验证”。技术依据是 [Ascend C CANN 8.0.RC2.2 的 AIC/AIV 架构说明](https://www.hiascend.com/document/detail/zh/canncommercial/80RC22/developmentguide/opdevg/Ascendcopdevg/atlas_ascendc_10_0019.html)。

**特别警告**：这些是对应官方架构版本下的典型教学路径，不能把 AIC/AIV 物理布局和 FixPipe 路径套到所有 310P / 910B / 910C / 950DT 产品上。动画没有时间数字、没有模拟“芯片利用率实测”。详见 [architecture-paths-v2.2.json](../content/architecture-paths-v2.2.json)。

## 二、代码与测试

- [网页入口](../site/index.html)、[交互实现](../site/app.js)、[CSS 视觉系统](../site/app.css)：新增官方规格与具体配置卡、固定发布版本兼容剖面、跨模型官方支持示例、SVG 数据流图。
- [离线单文件打包器](../site/build_site.py)：将三份 v2.2 来源 JSON 与已有产品族谱、研究案例和知识图谱合并，离线 HTML 不依赖网络服务。
- [数据验证测试](../../../tests/test_ascend_verified_specs_v22.py)：产品数值精度/范围、可选配置、CANN/驱动发布组合、跨模型来源、AIC/AIV 分帧等 6 项新增回归。
- [Chromium + WebKit 六尺寸组合浏览器回归](../site/browser_cross_engine.py)：实际点击 Duo 的 FP16/容量、800I A2 可选互联、Cube/Vector SVG、版本兼容筛选与 GLM 示例；仍保留窄屏溢出检验。
- [网站 CI](https://github.com/cao772/ascend-llm-inference-optimization/actions/workflows/ascend-explorer-site.yml)：产生可直接打开的 HTML 和多张截图，检验真实浏览器交互与所有现有数据门槛。

## 三、剩余问题与后续研发

1. 官方逐 SKU 数据集范围仍不够大，后续补 950DT、Atlas 300I A2、Atlas 800I A3 等，切记型号/产品级别和数值单位。
2. 需要模型+版本+精度+卡型的真实兼容查询和部署记录，当前只有发布文档与静态支持示例。
3. 进一步丰富 SVG 图示与交互，如 tiled GEMM 的多轮搬运/复用对比和 Host–Device 联合 Profile。
4. 原生 Safari 与辅助技术人工验收仍未进行；Playwright WebKit 测试只覆盖浏览器引擎。
5. 实际 NPU 环境、模型加载、Profiler、A/B 和优化后 TTFT/TPOT/TPS 均**没有完成**。不会将厂商峰值参数、外部论文或教学动画写成我们的推理加速成果。
