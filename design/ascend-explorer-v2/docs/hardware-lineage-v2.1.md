# V2.1｜昇腾产品谱系、处理器证据与多端质量验证

> 2026-11-01 · 开发记录。此处只记录已核查的产品分类与代码实施；网页教学图不是对硬件内部结构或性能的实测。

## 一、为什么需要从“卡列表”改为四层钻取

上一版本将“模块、卡、推理整机、训练整机、超节点”分类展示，但“型号→产品系列→处理器”的关联靠面包屑文字，没有真正的来源验证。新版本将四级导航拆为：

**形态（form）→ 官方产品系列（family）→ 产品 SKU/目录条目（product）→ 有来源的处理器映射（processor evidence）**。

这不是价格和性能排行。点开每一个层级时提供来源和适用边界；未知的设备内存、TOPS、带宽和功耗继续保持 `null`。带宽只有确认精度/测试范围和设备型号后才可比较。

## 二、本轮新增核实信息

| 证据范围 | 新的页面能力 | 必须保留的边界 |
| --- | --- | --- |
| [昇腾官方产品形态说明（2024-05-13）](https://www.hiascend.com/doc_center/source/zh/mindx-dl/60rc1/description/productform/%E6%98%87%E8%85%BE%E4%BA%A7%E5%93%81%E5%BD%A2%E6%80%81%E8%AF%B4%E6%98%8E.pdf) | Atlas 300I Pro 和 Atlas 300I Duo 属于配置 Ascend 310P 处理器的产品系列 | 这不是对板卡显存、计算力、芯片数量、当前型号兼容性的完整证明 |
| [MindCluster 26.1.0 支持产品形态](https://www.hiascend.com/document/detail/en/mindcluster/2610/faultdiag/faultdiagug/docs/en/faultdiag/ascend-faultdiag/01_introduction/02_supported_products.md) | Atlas A3 推理产品、训练产品分开归类；Atlas 800I A3 不应默认放到“训练服务器系列” | 该文档是 MindCluster 组件支持范围，不等于所有模型和框架的通用兼容矩阵 |
| [Atlas 900 A3 SuperPoD 官方互联拓扑](https://www.hiascend.com/document/detail/en/mindcluster/730/clustersched/schedulingug/dl_affinity_0007.html) | 额外说明「处理器→HiAM→节点内 HCCS-L1→节点间 HCCS-L2」的层次 | 仅能针对官方说明对应的 A3 SuperPoD 产品展示，不能泛化到所有昇腾卡 |
| 先前源码研究 | 910B、910C 作为芯片代际研究主题保留 | 未取得具体整卡 SKU 官方规格前，不给 TOPS、HBM、具体芯片数量或带宽 |

新增 [来源型产品与处理器关系 JSON](../content/product-lineage-v2.json)，与原 [产品数据目录](../content/hardware-catalog.json) 分离；原数据未被虚构参数覆盖。

## 三、代码和交互落地

- 第一级：选择模块/加速卡/推理服务器/训练服务器/超节点。
- 第二级：在当前类别中切换与官方资料相符的产品系列。
- 第三级：选择正式产品目录条目，显示所属产品族、准确已核验字段与未知规格。
- 第四级：通过处理器来源证据面板，追踪已被证实的产品系列映射。尚未确认的内容显示「处理器型号未核验」。
- Atlas 900 A3 专用互联拓扑示例有单独的来源抽屉，不影响其他产品。
- 现有最多三产品对照继续可用，**未核验参数仍不允许用于性能排名**。

## 四、质量验证

专门增加 [产品谱系源数据校验](../../../tests/test_ascend_product_lineage.py) 与 [Chromium+WebKit 多宽度测试](../site/browser_cross_engine.py)，宽度覆盖 **375、768、1440px**。由于采用 Playwright WebKit 引擎，测试代表“WebKit 浏览器引擎兼容性”而非真实 macOS Safari 产品认证。

浏览器 QA 会实际操作产品族与处理器证据、A3 拓扑卡、AI Core 数据通路、算子故事板，并断言页面横向溢出不超过 3px、无脚本错误。

测试发现并修复过一处真实的 375px 窄屏缺陷：长模型/PR 字符串撑开研究案例卡片，导致页面横向溢出。通过 `minmax(0,1fr)` 和内容换行约束解决，**没有用全局隐藏溢出来掩盖问题**。

## 五、下一阶段

继续补逐 SKU 的官方数据手册和 CANN/推理引擎兼容矩阵，扩展 Ascend 950 产品族等新型号（需逐条核实产品类型、芯片映射与来源）；改善专业版 NPU 内部数据通路 SVG 结构和工具提示；完成原生 Safari 设备侧手动验证；等待真实昇腾环境后才进行 Profiler/A-B。

本轮依旧没有开发或声称任何真实昇腾大模型推理加速倍数。
