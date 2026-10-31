# Qwen 算子优化证据图谱 v2：有来源的案例、模型、PR 与失败经验

> 2026-10-31。当前不具备 GPU/NPU 硬件，也没有在本研究项目中真实运行 Qwen。这里是 **source-grounded evidence graph（证据关系图）**，不是证明过性能因果关系的行业本体，更不是硬件兼容性认证。

## 1. 与上一版的差异

上一版关系图只覆盖案例、机制、算子，以及少量模型配置；同机制标签会产生 `shares_tags` 边，容易让人误以为算子代码可以直接迁移。现升级为：

- **15 个研究案例**：每个案例保留模型、硬件、测量阶段、来源和作者声称的结果；测量等级区分 proposal、配置/方法、微基准与作者在线服务基准。
- **5 个 Qwen 官方配置结构节点**：含 MoE/非 MoE、混合线性注意力、GDN key/value 头比例；配置来源和未固定版本限制保留。
- **12 个已核对的上游合并 PR**：保存 repo、PR number、merge commit、触及的源码文件、机制标签；不能由已合并推断“当前版本有此算子”。
- **8 条失败或限制经验**：2 条死锁风险、1 条确定性回归、1 条静态不适用、3 条被上游移除的旧功能、1 条微基准噪声/解读风险。
- **PR 生命周期有向关系**：例如方案引入→回退→带 Graph 保护重新引入；Kernel 首次调用挂起→修复 SM/cluster 获取；Qwen3Next auto enable→确定性模式回退。
- **显式的静态模型-PR 排除关系**：五款模型针对 vLLM #51674 的特定 GDN MTP 8:1 头数条件全被排除，但不得推断其它 GDN Kernel 不能用。

全部边具有 `relation`、`evidence_level`、`provenance_urls`，并默认 `runtime_dispatch_verified_by_project=false`、`speedup_verified_by_project=false`。人工标注的机制相似关系统一写明 `explicitly_noncausal=true`。

## 2. 图谱入口

| 文件 | 功能 |
| --- | --- |
| [`research/cases/qwen-optimization-cases-2026-10-30.json`](../research/cases/qwen-optimization-cases-2026-10-30.json) | 案例事实源：15 条 |
| [`research/model-structures/qwen-gdn-structure-matrix-2026-10-30.json`](../research/model-structures/qwen-gdn-structure-matrix-2026-10-30.json) | 模型结构事实：5 条 |
| [`research/source-traces/qwen-operator-pr-lineage-2026-10-30.json`](../research/source-traces/qwen-operator-pr-lineage-2026-10-30.json) | 12 个上游 PR 及 5 条演变边 |
| [`research/failures/qwen-operator-failure-modes-2026-10-31.json`](../research/failures/qwen-operator-failure-modes-2026-10-31.json) | 8 条失败、回退、静态不适用、测量警示 |
| [`tools/build_qwen_evidence_atlas.py`](../tools/build_qwen_evidence_atlas.py) | 纯标准库生成完整 JSON 关系图，并校验引用/边 |
| [`tools/query_qwen_evidence.py`](../tools/query_qwen_evidence.py) | 离线查询证据子图，不需要图数据库或模型服务 |
| [`.github/workflows/evidence-atlas.yml`](../.github/workflows/evidence-atlas.yml) | 统一 CI 校验，并发布 JSON 快照与检索示例 Artifact |

### 本地只读构建

```bash
python3 -m unittest discover -s tests -v
python3 tools/build_qwen_evidence_atlas.py --output build/qwen-evidence-atlas.json
```

### 有用的检索方式

```bash
# 查 Qwen3.6-27B 静态结构及已知特定 Kernel 的不适用条件
python3 tools/query_qwen_evidence.py --model-id Qwen/Qwen3.6-27B

# 查 GDN 案例和关联的来源（只做直接邻接，不自动推导兼容）
python3 tools/query_qwen_evidence.py --operator GDN --radius 1

# 查所有上游文档记录的死锁、修复 PR 和机制
python3 tools/query_qwen_evidence.py --failure-kind deadlock

# 查 AllReduce 的一个特定 PR 与修复/回退及机制
python3 tools/query_qwen_evidence.py --pr-id PR-SGL-22664 --radius 1

# 按中文关键词或英文词组检索；这是字面子串，不是语义搜索
python3 tools/query_qwen_evidence.py --text 死锁 --radius 1

# 机制的邻居可能很多，可限制输出量
python3 tools/query_qwen_evidence.py --mechanism fusion --max-nodes 40 --radius 1
```

输出包含：查询类型、命中的确切锚点、节点、带来源的关系、截断标志和禁止性能外推声明。

## 3. 两项数据治理修正

**修正一：PR 不再因为技术相似就自动挂到案例。**

此前将 SGLang MNNVL（某些 PR 中其他模型的实验）直接挂在 Qwen3-Coder-Next 案例下，还将 vLLM GDN MTP Decode Kernel PR #51674 直接挂到 FlashInfer GDN Prefill 案例下。二者均有误导风险。现在，只有确有同一来源/优化阶段联系的 PR 才保留 `pr_documents_specific_case` 关系；其它 PR 通过机制或生命周期相连，并保留原始发现记录，不改动这些 PR 的事实。

**修正二：区分“失败”与“适用性限制”及“维护性删除”。**

`deadlock`、`numerical_regression` 是作者上游报告的行为；`guard_mismatch` 是静态匹配不通过，不能宣称代码或模型有 Bug；`feature_removed` 是上游维护决策，不说明所有同类思路无效；`benchmark_interpretation` 是作者报告与测试准则的统计解释边界。任何一项都没有本项目实机复现。

## 4. 三条研究路线现在可以直接检索

**通信融合：** 查询 `--mechanism fusion`、`--pr-id PR-SGL-24629`、`--failure-kind numerical_regression`，沿 PR #12787 → #20792 → #23402 查 Graph 问题，沿 #22664 → #24629 查确定性约束；同时保留 Ascend #12119 已移除旧路径的独立事实。

**GDN：** 查询 `--operator GDN`、`--pr-id PR-FI-3001`、`--pr-id PR-VLLM-51674`，对比 Prefill 调度和 Decode/MTP 的特殊门槛。不能由任一微基准代替另一阶段。

**MoE：** 查询 `--operator MoE`、`--failure-kind feature_removed`；把专家路由形状、TP/EP、采样负载、weight prefetch 生命周期一起研究，而不是只看一条 Fused MoE 的倍数。

## 5. 知识体系的后续演进顺序

1. **固定来源：** 当前 Qwen 五模型中部分 `config.json` 使用 main 路径读到；还需要对照 HuggingFace 目录中的 commit SHA 逐个回读一致性；不能暗示都已 SHA 固定。
2. **补函数级调用链：** 新 PR 进入资料库时记录入口→调度 guard→Kernel→Fallback，并指明是否合并、被撤回、继续有效。
3. **量化比较协议：** 未来要保存精确模型权重 revision、driver/runtime、TP/EP、batch、context、测量阶段、统计误差和正确性回归，才能把 `case` 标成我们的实测。
4. **未来的检索升级：** 目前是确定性结构/关键字检索；如果案例规模扩大，可以先给关键字段做 BM25，再对人工确认的材料做向量检索，但检索结果最终仍需回到来源链接、具体 PR 与代码 diff。不要把向量相似度直接解释为算子可移植性。

## 当前验收口径

- 纯标准库离线构建，任何 Python 3.12 主机可运行；
- 不下载模型权重、不建立训练环境、不启动推理服务、不修改主分支；
- 所有新增失败记录具有明确 PR/报告来源；
- 每条图谱边具有可追溯来源（项目自身标签派生也明确为人工分析）；
- CI 对引用完整性、错关联、来源、模型 guard、检索边界有自动回归校验；
- 没有硬件时 **速度收益和部署可用性始终保持未验证**。
