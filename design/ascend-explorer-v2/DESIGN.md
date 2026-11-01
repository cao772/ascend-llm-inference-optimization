# 昇腾大模型推理与算子优化｜V2 全景交互网站详细设计方案

> 2026-11-01 · DESIGN ONLY / 待评审。该文件是可交付开发的设计，不是已经上线或实机验证的页面。项目名已扩大为《昇腾大模型推理与算子优化》；Qwen 是既有模型案例，不再限制项目范围。独立目录，不破坏现有 Qwen HTML 看板。

## 1. 产品目标、信息层级与禁区

设计成能从简单到深入阅读的**昇腾技术展馆**：先看明白“芯片、卡、服务器、超节点”，再进入 NPU 计算单元与片内缓存、模型推理的 Token 生命周期、影响指标和算子优化机制，最后提供案例/知识图谱与项目成果证据。

阅读路径分三层：**60 秒总览 / 3 分钟机制 / 10 分钟源码与性能验收**。首页主线为“硬件 → 软件栈 → 模型 → Prefill/Decode → 算子/通信 → 指标 → 候选优化 → 证据”。

四条不可破坏的边界：
- **芯片、产品形态、产品族并非同一维度**：310P / 910B / 910C 是处理器或研究标签；Atlas 300I Duo 是卡，Atlas 800I A2 是服务器，Atlas A3 是产品系列。没有官方具体规格，不做跨代“排行”。
- **AI Core 架构说明存在版本差异**：Cube/Vector/Scalar、GM/LocalMemory、DMA/MTE 可作为架构抽象；独立 AIC/AIV 及特定 L0/UB 路径必须标明特定硬件架构。不得将 351x 的独特数据通路画成所有昇腾芯片共同内部结构。
- **软件功能、硬件适配、运行命中、性能提升是四件不同的事**：文档有功能，不等于目标设备或模型支持，也不等于跑起来，更不等于提速。
- **教学示意不伪装真实数据**：动画不输出毫秒、利用率和 TPS；外部文章的性能数字不能冒充项目实测；没有可靠 datasheet 的 TOPS/带宽/内存/功耗全部显示“未核验”。

## 2. 信息架构：一张全景图 + 九个深度模块

| 编号 / hash | 模块 | 第一个视觉 | 二级深挖 |
| --- | --- | --- | --- |
| M00 #overview | 全景导览 | 输入请求流到 NPU 输出、Hover 高亮全路径 | 打开每段“是什么/为什么慢/如何验证” |
| M01 #hardware | 产品与芯片谱系 | 产品族→具体产品→处理器的层级筛选 | 卡/服务器/互联比较、可追溯官方数据 |
| M02 #anatomy | AI Core 解剖 | 设备→NPU→AI Core→存储与计算单元的 4 层放大 | Cube/Vector/Scalar/GM/UB/L1/L0/DMA 数据流示意 |
| M03 #stack | 软件栈 | 模型→框架→适配→CANN→Driver→NPU 的 6 层栈 | 每层版本、Kernel dispatch 与真实命中条件 |
| M04 #lifecycle | Token 推理时间线 | 请求→排队/分批→Prefill→Cache→Decode→流输出 | TTFT、TPOT、P95、吞吐的清晰定义与计时范围 |
| M05 #factors | 性能影响因素地图 | 模型/负载/硬件/软件/算子五组映射 | 选择一因素，关联热点、反例、量测指标 |
| M06 #operators | 算子显微镜 | 7 类算子小型动画与逻辑 before/after | 输入形状→操作→搬运→瓶颈→优化→回退 |
| M07 #optimization | 从问题出发的加速路线 | 症状→Profiler→候选→验证→回退路径 | 明确条件和证据层级，禁止直接输出“最佳优化” |
| M08 #evidence | 案例/知识图谱/项目成果 | 15案例/12PR/8失败/5模型结构的研究快照 | 真实来源关系、跨平台限制、成果与未完成边界 |

所有模块保留“返回主因果链”；右侧共享 SourceDrawer 引用抽屉，不跳转后丢失上下文；移动端改用底部抽屉和分段导航。

## 3. M00 全景首屏详细布局

桌面 1440px：固定顶栏 64px，主体 12 栏。左 5 栏放项目名、三条“从硬件看懂推理”的摘要；右 7 栏放 SVG 逻辑路径：用户请求→Tokenizer→Scheduler→Prefill→GDN/Attention/MLP→KV/State→Decode→Stream。下方对应 Cube/Vector/Memory/Communication 四资源区。不得让连线横穿标签。

点击节点：锁定右侧“这一层做什么/相关指标/潜在热点/深入模块/原始来源”。默认开讲解模式，不自动播放；若启动演示，仅 token 小方块沿路径移动，不显示假时间。键盘 Enter/Space 激活，Esc 关闭抽屉；减少动态效果偏好时停止动画但可逐帧查看。

## 4. M01 设备谱系与产品钻取

四级：**形态**（模块、卡、服务器、超节点）→**系列**（Atlas 推理、A2、A3 等）→**产品 SKU**（如 300I Pro/Duo、800I A2、800T A2、900 A3）→**处理器结构和资源**。UI 不将 310P/910C 和 Atlas A3 放同一张“卡排行”里。

产品卡必须显示：正式名称、产品层级、应用场景、官方来源、资料适用版本，以及 6 个技术维度（芯片/内存/通信/功耗/拓扑/官方支持情况）。没有数据的数字字段为 null，展示“未核验”，绝不以 0 或其他卡的值替换。三卡对比默认只显示有来源的定性参数；定量比较必须确保同精度、同测试负载与来源。

“910C / 910B”建立研究主题入口，未验证对应官方规格前不显示具体加速卡照片、功耗、TOPS、HBM、价格，也不宣称与某个 A2/A3 SKU 一一对应。

交互：分类 Tab、同组多选（最多三项）、面包屑返回、来源抽屉；mobile 屏幕卡片纵向布局。

## 5. M02 AI Core 内部结构与算子微观数据流（核心视觉投入）

需要分别绘制 4 张语义 SVG：产品拆解示意、NPU 高层结构、AI Core 架构抽象、某个运算的数据传输链。不得直接复用某个芯片官方架构原图冒充自绘；新图为基于官方文字的原创教学结构示意。

AI Core 可点击单元：
- **Cube**：矩阵乘 / GEMM / MoE Expert 矩阵运算；并列展示输入 M/N/K 与分块概念。
- **Vector**：归一化、激活等向量计算；用 RMSNorm 作为教学示例。
- **Scalar**：控制/分支/循环、地址和指令分发。
- **Global Memory（GM）**：外部全局存储，勿在所有产品里都标成 HBM。
- **Local Memory**：UB、L1、L0A/B/C 按目标架构适配；架构不明确时只显示抽象。
- **MTE/DMA/FixPipe**：搬运与写回；点击后突出内存路径，显示何时数据搬运成本可压过计算成本。
- **AIC/AIV**：对支持独立核架构版本单独呈现，不得在所有产品默认显示相同比例。

教学数据流 A（典型 Matrix）：GM → L1 → L0A/L0B → Cube → L0C → GM/下一级。B（典型 Vector）：GM → UB → Vector → UB → GM。每一步可前进/后退和自动播放，默认标记“硬件架构抽象，非真实 profiler”。

切换“提高复用”仅显示片内搬运/访存的逻辑差异，不给倍数。所有连线使用正交或分层避让，不能穿过可点元件。

## 6. M03 六层软件栈 & M04 请求生命周期

M03：模型及服务 → 推理引擎（MindIE/vLLM-Ascend/SGLang-Ascend）→ 框架适配（torch_npu 等）→ CANN（编译/算子/运行时）→ 驱动/固件 → NPU。是**逻辑架构**，不是所有框架都走固定一条函数调用链。每层含输入/输出、常见瓶颈、版本依赖、可证伪核验方法。示例 vLLM-Ascend v0.30.0：Static Kernel 与 Super Kernel 的前提和编译开销需和对应文档一致，不能拿 v0.23 的旧融合做现成功能。

M04：显示 Host 队列 + NPU 计算 + KV/State 缓存三条逻辑轨；可设置 ISL(32/512/4096) OSL(16/128/512)、并发(1/8/32) 来变更**示意 token 数与路径复杂度**，但不计算伪毫秒。定义：
- TTFT：从约定的请求开始点到第一个输出 token（明确是否包含排队/网络）。
- TPOT：后续 token 平均间隔，需说明 denominator 与统计方法。
- E2E：请求到完成的整体时长。
- tokens/s、req/s 与 P95：都保留单位、分母、统计窗口和负载范围。
点击 Prefill、Decode 和缓存轨，联动亮起不同算子和可能约束，并给出“要通过 Profiler 采集什么”。

## 7. M05 影响因素地图 & M06 算子显微镜

M05 五大类模型/负载/硬件/软件/算子。至少八个因果演示：输入长度→Prefill；输出长度→Decode；并发→批次/P95；Dense/MoE→专家路由；GDN/Full→状态缓存；TP/EP→通信；量化→访存/数值正确性；图捕获→启动/缓存/形状开销。每张因素卡必须有“五段论”：是什么→可能影响什么→在哪个阶段明显→可能反例→要测什么。用户一次只看一条高亮因果链。

M06 至少七类：MatMul/GEMM、RMSNorm/Residual、Attention/GDN、KV Cache、MoE/Grouped GEMM、AllReduce/Collectives、Graph/Static Kernel/MTP。每类严格 6 帧：
1 输入 Tensor/张量形状（非量测）；
2 执行步骤；
3 数据搬运/通信；
4 热点条件与可证伪原因；
5 优化前后**逻辑图**（不展示性能数值）；
6 版本限制/负例/如何验收/回退。

特别注意 FlashInfer GDN Prefill 与 vLLM GDN MTP Decode 不是同一个算子；旧 Ascend matmul+allreduce+rmsnorm 代码的删除史必须单列；MoE 专家负载不均不能用均匀路由微基准预测线上收益。

## 8. M07 症状到验证路径 & M08 证据与成果

M07 症状入口：模型放不下/OOM、TTFT 高、TPOT 高、吞吐低、P95 尾延迟、高通信等待、个别算子慢。每条路径至少两种可能根因，先提供区分它们的 Profiler/统计证据，再给候选操作（量化、缓存、SP、图、融合、路由、调度等）与正确性/兼容性回退门槛。不能自动给出百分比。

M08：展示已有 15 外部案例、12 上游 PR、8 失败/限制、5 官方 Qwen 模型配置及 75 节点/202 关系的**历史图谱快照（标记日期）**。外部案例作者数据与项目自测分栏，不做混合排行榜。DeepSeek/GLM 作为新增研究专题“待补证据”而非已有研究结论。图谱查询复用 tools/build_qwen_evidence_atlas.py 的来源 JSON；不再手录一套有歧义的图谱数字。项目状态“软件研究原型已实现，真实昇腾硬件加速待验证”，不写“已上线/已完成芯片优化”。

## 9. UI 系统 / 组件 / 数据规范

色彩：深蓝背景 #081321、主表面 #0F233A、次表面 #142D48、分割线 #294661、正文 #EAF2FF、辅文 #B1C4D8、数据流 #68D6CF、风险 #F2C984、明确不适用 #FF999E。对焦状态不能只用颜色，必须文字+形状。

响应式：1440px 内容上限 1360px，12 栏；1024 断为 8 栏；768 和 375 单列。图内最小标注 12px，来源 11px，重要说明 14–16px。所有复杂关系 SVG 标签不遮挡节点、不出现横向溢出；减少动态偏好可逐帧查看。

设计组件：GlobalHeader、CausalChain、ProductFamilyTabs、ProductDetail、ArchitectureBadge、ChipExplodedView、ComputeMemoryPath、StackLayer、TokenTimeline、BottleneckMap、OperatorStoryboard、SourceDrawer、CaseEvidenceCard、ProjectStatusPanel。必须支持鼠标/触控/键盘焦点、aria-label、Esc、Back、清晰状态。

数据约束见本目录的 content JSON、src/types.ts、tokens.css；ID 必须稳定。定量参数缺失用 null；模型/卡型/软件兼容无法证明时使用 unknown，**绝不把未知当 false 或支持**。每条解释关联 provenance URL/版本/局限。

## 10. 开发分批与验收（本轮仅设计）

- D0：本轮设计冻结候选、UI Tokens、来源型内容档案、类型契约、离线校验、Notion 设计专页。
- D1：页面骨架/首屏/M01 产品级导航，验收不同产品层级不混淆。
- D2：AI Core 四级放大、两种存储路径动画、六层软件栈及版本依赖。
- D3：Prefill/Decode 时间轴、参数与指标解释，教学示意与实测严格分离。
- D4：五因素联动、七算子六帧分镜、异常/回退/来源抽屉。
- D5：症状路径和知识图谱真实数据、案例与研究成果、移动端/无障碍/CI 回归。

每阶段验证：产品来源链接可用、数据不伪造、动线绕开节点、键盘和移动端可用；真实进度与 GitHub CI 状态分开。绝不覆盖现有前端，不合并 main。**v2 页面尚未实现，待设计评审后才开始高保真编码。**

## 11. 证据与待核实事项

官方参考：
- 产品形态：https://www.hiascend.com/doc_center/source/zh/mind-sdk/600/description/productform/hardwaredesc_0001.html
- 架构抽象：https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/programug/Ascendcopdevg/docs/en/guide/programming_guide/advanced_programming/hardware_implementation/basic_architecture.md
- AIC/AIV 独立结构示例：https://www.hiascend.com/document/detail/zh/canncommercial/81RC1/developmentguide/opdevg/Ascendcopdevg/atlas_ascendc_10_0015.html
- 351x 非普适细节：https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/900beta2/opdevg/Ascendcopdevg/atlas_ascendc_10_00065.html
- vLLM-Ascend v0.30.0：https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/release_notes.html
- Static/Super Kernel：https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/feature_guide/graph_mode.html
- Sequence Parallelism：https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/feature_guide/sequence_parallelism.html
- MindStudio Insight：https://www.hiascend.com/document/detail/en/mindstudio/2610/visualization_tool/MindStudioInsight/docs/en/user_guide/overview.md

待考证：910B/910C 官方 SKU/规格映射，A3 各服务器的硬件细节，多架构缓存路径和具体型号适配，未来使用的正版产品图片与许可证，以及任何模型在具体卡和 CANN 组合下的真实功能支持。不能为了页面“完整”捏造这些事实。
