# V2.3｜GEMM Tiling 与数据复用交互实验室研发记录

日期：2026-11-01。项目：**昇腾大模型推理与算子优化**。

> 本轮是有公式、可操作、可测试的**教学数学模型与网页**，不是 Ascend NPU 真正执行的 Matmul Kernel，也没有算子实测时延、GM 带宽、TTFT/TPOT 或端到端加速数据。

## 一、用户问题与设计目标

在 V2.2 的 Cube/Vector 七步和五步官方架构示意基础上，进一步回答三个问题：

1. 如果 A[M,K] × B[K,N] 的矩阵很大，为何要拆成许多 Tile？
2. 每个输出 Tile 为什么沿 K 轴多次累加？非整除的矩阵边界如何处理？
3. 为什么重复读取相同的 A/B 分块可能造成不必要的数据搬运？什么叫“数据复用”？

新增独立 **GEMM 分块与数据复用实验室**，嵌入已有 AI Core 解剖展区，不增加不必要的后台服务，也不修改之前的 Qwen 案例/知识图谱。

## 二、界面与操作

- 3 个可点击示例：Decode 细 M 形状、Prefill 方形练习、非整除边界；
- 6 个参数：M/N/K、Tile M/Tile N/Tile K；
- 三张联动的小矩阵网格：A[M,K]、B[K,N]、C[M,N]；当前涉及的三个 Tile 高亮；
- 可连续选择“下一块/上一块/回到首块”，显示有效行列与 K 轴区间，例如 M=144、N=112、K=80，TM=TN=64、TK=32，最终边界块为 16×16、16×48（对应 A/B 输入形状），总计 18 个逻辑迭代；
- 4 种用于教学比较的条件：不跨输出块复用 / 理想复用 A / 理想复用 B / 两输入各只读一遍的理论下界；
- 展示逻辑任务数、K 轴轮次、数学 FLOPs、片内块大小算术估计、理想化逻辑读取字节量，始终标记“非硬件测量”。

## 三、数学逻辑（可审计）

定义：

- 输出分块数：`ceil(M/TM) × ceil(N/TN)`；
- K 轴分块轮次：`ceil(K/TK)`；
- 逻辑 Tile 任务数：三者相乘；
- 乘加算两次运算的数学 FLOPs：`2×M×N×K`；
- 仅用于说明的 A/B 输入块 + FP32 累加块“局部工作集”：
  `(TM×TK + TK×TN)×2 bytes + (TM×TN)×4 bytes`。

**抽象数据重复读取模型**（假设输入采用 2 字节元素）：

- 无跨输出 Tile 复用：A 输入元素计数 = `M×K×ceil(N/TN)`；B = `K×N×ceil(M/TM)`；
- 理想复用 A：A = `M×K`，B 保持不变；
- 理想复用 B：B = `K×N`，A 保持不变；
- 理论下界：A = `M×K`、B = `K×N`（必须明确这不是总能在真实芯片上实现的策略）。

例如 M=N=K=64，TM=TN=TK=32 时，逻辑 Tile 总数为 8，按上述模型“不跨输出 Tile 复用”输入累计 32,768 字节，理想复用 A 或 B 对应 24,576 字节，两者各读一次的**数学下界**为 16,384 字节。

以上数字不是实际 GM/HBM 通信量。**真实硬件还要考虑 L1/L0 容量、内存布局、对齐、补齐、访存路径、L2、线程/核布局、DMA/缓存行为、同步、输出写回和 kernel 编译策略等。** 不能把“逻辑读取比例”当成真正加速百分比，也不能依据这个练习决定具体型号的 TM/TN/TK 最优参数。

## 四、技术资料依据与边界

- [Ascend C Matmul Tiling API 官方说明（CANN 8.5.0）](https://www.hiascend.com/document/detail/en/canncommercial/850/API/ascendcopapi/atlasascendc_api_07_0671.html)：要求设置矩阵形状、位置、格式与 dtype，经 `GetTiling` 获得与 Kernel 初始化配套的参数；单核/多核/BatchMatmul 有不同接口。
- [Ascend C Matmul API 的 CopyIn/Compute/CopyOut 说明](https://www.hiascend.com/document/detail/zh/canncommercial/80RC3/developmentguide/opdevg/Ascendcopdevg/atlas_ascendc_10_0042.html)：`SetTensorA`、`SetTensorB`、`Iterate`、`GetTensorC` 是具体高级 API 的开发步骤。
- 较小矩阵 L1 长驻、分次搬运另一输入以降低搬运，是官方 Ascend C 最佳实践记录的真实**优化机制**，但实际收益须依据设备和负载通过 Profile/A/B 核查，不能由本练习定量推出。参考 [CANN 8.1.RC1.alpha001 Ascend C 最佳实践](https://www.hiascend.com/doc_center/source/zh/CANNCommunityEdition/81RC1alpha001/devguide/opdevg/ascendcbestP/CANN%E7%A4%BE%E5%8C%BA%E7%89%88%208.1.RC1.alpha001%20Ascend%20C%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5%2001.pdf)。

不能跨版本把 Tiling 的抽象数学练习误写成真实 `TCubeTiling` 结果；示例不调用 `GetTiling`。

## 五、代码与测试清单

- [数学核心（JS，可 Node 测试）](../site/tiling_math.js)：`derive`、`tileAt` 两个纯函数；
- [教学案例数据与来源](../content/gemm-tiling-lab-v2.3.json)：三个例子、四种复用模型、事实限制；
- [交互页面实现](../site/app.js) + [UI](../site/index.html) + [CSS](../site/app.css)；
- [自动单元测试](../../../tests/test_ascend_tiling_math.cjs)：六组公式、边界、失效参数与防止虚构硬件事实；
- [浏览器回归脚本](../site/browser_cross_engine.py)：Chromium/WebKit 375/768/1440 下切换预设、单步推进、复用对照、证据抽屉和溢出检查；
- [完整网页打包](../site/build_site.py)：包含数学模块和本项目既有数据，生成自包含离线 HTML；
- [GitHub CI](https://github.com/cao772/ascend-llm-inference-optimization/actions/workflows/ascend-explorer-site.yml)：自动执行 Node、Python、真实浏览器并留存截图。

## 六、后续优先项

1. 逐官方模型与芯片架构补具体存储大小和 Tiling 限制；有了正式 CANN/算子编译环境后才调用真实 `GetTiling` 并比对模型。
2. 增加真正 **L1 容量约束**、动态 Tile/数据布局、Kernel 行为追踪，并与 Profiler 导出的真实 GM 读写和时长对照。
3. 更深入展示 A/B 的多层循环与 K 分段重用，在相同工作量下比较调度与核间搬运，而非只看理想全局下界。
4. 保留旧页面和所有已有数据；当前没有目标 NPU，不能写实机提速成果。
