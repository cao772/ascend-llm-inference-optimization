# Ascend Explorer V2 · 交互网页与详细设计

## V2.2｜官方规格 + 固定版本兼容 + AI Core 逐帧 SVG（2026-11-01）

- [V2.2 来源与技术审计](./docs/official-hardware-and-ai-core-v2.2.md)：将 Atlas 300I Duo 整卡 FP16/INT8、LPDDR4X 48/96 GB、408 GB/s 与 Atlas 800I A2 整机 4U、8 模组、可选互联 392 GB/s 分开标注，防止把整机互联误称为单芯片显存带宽。
- [经核实的产品数字](./content/verified-product-specs-v2.2.json)：只收录已找到厂商产品页证据的两个具体产品，其余数值保持未核验。
- [vLLM-Ascend 0.30.0 固定兼容版本](./content/software-compat-v2.2.json)：列出驱动/CANN/TorchNPU/vLLM 共同验证的整套发布环境与四个模型族示例；不同硬件族的 Triton 使用范围分别显示。
- [AIC Cube / AIV Vector 数据路径](./content/architecture-paths-v2.2.json)：典型矩阵计算七帧与向量计算五帧，SVG 随步骤高亮，每一步给出数据搬运、可能的代价和如何用 Profiler 证伪。
- [6 项新增测试](../../tests/test_ascend_verified_specs_v22.py) + [Chromium/WebKit 375/768/1440 回归](./site/browser_cross_engine.py)；修复了新增宽幅芯片 SVG 引起的移动端 Grid 最小宽度溢出。

**注意**：型号规格为厂商标称值，不是本项目实测性能。官方模型支持矩阵不意味着任意卡型/并行拓扑已验证；本轮未实际拥有 NPU、未进行真实推理或算子性能 A/B。

## V2.1 产品谱系与多浏览器验收（2026-11-01）

- [产品形态→产品族→SKU→处理器四级钻取及依据](./docs/hardware-lineage-v2.1.md)：6 官方产品系列、10 个代表产品；对 Atlas 300I Pro/Duo 提供 310P 产品族映射，含来源与作用范围。
- [产品谱系数据](./content/product-lineage-v2.json)：A3 专属拓扑案例、来源 URL、未核验规格标识，**不把 910B/910C 错当做完整物理板卡**。
- [跨浏览器测试](./site/browser_cross_engine.py)：Chromium + WebKit 内核，375/768/1440 宽度；硬件筛选、族谱、证据与拓扑、芯片通路和算子分镜均实际点击验收。
- [成功 CI #41299453500](https://github.com/cao772/ascend-llm-inference-optimization/actions/runs/41299453500)：12 项设计检查、10 项网页单元测试、5 项产品证据规则测试，以及浏览器实际交互。Artifact 含离线 HTML 和多张截图。
- 曾发现 375px 窄屏下长模型名撑开案例网格造成约 51px 横向溢出，已通过网格最小宽度与内容换行修复，**不是强行隐藏溢出**。

仍待完成：原生 macOS Safari 人工验收、逐 SKU 精确官方规格、更多芯片与模型支持矩阵、实机 Profiling/A-B，以及公网部署。WebKit 自动测试不等于原生 Safari 认证。

## V2 可运行网页 MVP（与早期设计预览分开）

**新增真实网页代码**保存在 site/：

- [index.html](./site/index.html)、[app.css](./site/app.css)、[app.js](./site/app.js)：九展区的实际互动页面，不再是旧 [preview.html](./preview.html) 的局部演示。
- [build_site.py](./site/build_site.py)：从现有产品、七类算子数据和完整图谱，打包可离线打开的独立单 HTML。
- [browser_smoke.py](./site/browser_smoke.py)：Chromium 真实点击产品筛选、芯片组件、软件栈、时间线、算子六帧、诊断、图谱邻域和来源抽屉，以及手机导航与水平溢出测试。
- [网站专属 CI](../../.github/workflows/ascend-explorer-site.yml)：自动运行数据、JS/HTML 和浏览器测试，输出 HTML + JSON/设计资料 + 截图 Artifact。

本地打包（Python 标准库，不下载大模型）：

    python3 design/ascend-explorer-v2/site/build_site.py --output build/ascend-explorer-v2.html
    python3 -m unittest discover -s tests -p 'test_ascend_explorer_site.py' -v

用浏览器直接打开 build/ascend-explorer-v2.html；离线交互与证据浏览可用。仓库未确认已启用 GitHub Pages，不把 Actions 构建产物误称为公网网站。

目前交互覆盖全景因果链、产品分类和对照、四层解剖与数据路径、六层软件栈、Token 生命周期、八条影响关系、七专题六帧、七类症状、15 个历史案例、75 节点/202 关系的一跳证据图谱。

边界：这是教育与研究网页，不是已接入 NPU 的可实测推理服务。完整型号精确规格、硬件/模型适配矩阵、源码级 AscendC 性能实证与线上部署待后续完成。


项目：**昇腾大模型推理与算子优化** · 当前状态：**V2.1 可运行网页 MVP 已通过跨引擎质量验收；完整型号规格与实机推理仍待开发**。

本文下半部分为 V2 原始设计合同；上半部分已经有可运行网页及 V2.1 来源型产品谱系实现。它不是公网生产部署，也不包含昇腾硬件实测。旧 Qwen 决策看板完整保留，不覆盖。

## 导航与交付

- [preview.html](./preview.html)：可离线打开的深蓝视觉设计预览，可点击产品形态、AI Core 组件和算子六帧，**不是完整 V2 实现，内部少量卡片为设计演示副本，后续应改为读 content JSON**。
- [DESIGN.md](./DESIGN.md)：9 模块、4 级硬件钻取、6 层软件栈、Token 时序、7 算子显微镜、案例知识图谱、设计规范、验收细则。
- [content/hardware-catalog.json](./content/hardware-catalog.json)：10 个有官方产品来源的**产品形态条目**；310P/910B/910C 等芯片族与物理 SKU 分开。
- [content/operator-stories.json](./content/operator-stories.json)：7 个算子专题 × 每个 6 帧 = **42 帧**，每条含来源和不适用/失败边界。
- [content/modules.json](./content/modules.json)：9 个模块对应的锚点、行为、可访问性及逐项可测验收条件。
- [src/types.ts](./src/types.ts)：内容类型、版本/归属状态、硬件规格可空性、真实性能证据门槛。
- [src/tokens.css](./src/tokens.css)：深蓝色设计 Token / 响应式和 reduced motion。
- [tools/validate_design.py](./tools/validate_design.py)：使用 Python 标准库检查数据类型、来源、结构、假性能与模块完整性。
- [tests/test_ascend_explorer_design.py](../../tests/test_ascend_explorer_design.py)：10 个离线回归测试。
- [CI](../../.github/workflows/ascend-explorer-design.yml)：自动检查设计资料，生成设计资产 Artifact。

## 开发前验证

    python3 design/ascend-explorer-v2/tools/validate_design.py
    python3 -m unittest discover -s tests -p 'test_ascend_explorer_design.py' -v

推荐开发阶段：D1 首屏/产品地图 → D2 芯片解剖/软件栈 → D3 请求时间轴 → D4 算子显微镜/症状地图 → D5 证据图谱/完整验收。每一阶段单独保存测试证据，不能用静态 SVG 图片代替真正交互。

## 事实边界

产品名称/型号归属和 Ascend C 硬件抽象来自官方文档。**没有**给任何卡型录入未经核验的 TOPS、内存容量、带宽或功耗，也不把某个 910C 博文视为硬件官方规格。未接入 NPU、没有真实 Profiler、未测得 TPOT/TPS 提升。模型/框架“支持”须单独证明芯片、版本、模型、拓扑和量化精度组合。

### 文档来源与长期记录

- [昇腾产品形态说明](https://www.hiascend.com/doc_center/source/zh/mind-sdk/600/description/productform/hardwaredesc_0001.html)
- [Ascend C 硬件架构](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/programug/Ascendcopdevg/docs/en/guide/programming_guide/advanced_programming/hardware_implementation/basic_architecture.md)
- [vLLM-Ascend 0.30.0](https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/release_notes.html)
- [原研究 Notion 总账](https://app.notion.com/p/4097bbed1352816fad17d3102052812e)
- [既有研发 Draft PR #4](https://github.com/cao772/ascend-llm-inference-optimization/pull/4)

设计中的九大模块已经有可运行离线版本；后续仍要根据官方 SKU 数据与硬件实测完善。现有内容不自动合并 main。
