# Qwen 推理优化：从案例证据到可执行 A/B 的完整分析链路 v1

> 2026-10-31 · 研究推演报告。**已验证：公开模型结构、上游 PR 生命周期及文档描述。推测：瓶颈优先级、优化可能方向。完全未知：本项目在 910C 的真实运行、速度、精度和成本。** 本研究当前没有落地 NPU/GPU 测试环境。任何推断不得作为已部署或性能承诺。

## 一、研究的输出不再是文章清单

已有 15 条跨平台优化案例、5 款官方 Qwen 模型结构、12 条公开 PR 演变证据、8 条失败/限制记录。基于这些数据，构建六阶段的可复核链路：

```text
原始案例/官方源码/PR/负优化记录
   ↓【证据级别与版本审核】
Qwen model config + TP/EP/并发/ISL/OSL + 硬件平台
   ↓【结构、框架、版本与静态guard筛选】
Prefill / Decode 的性能假设 + 分层负载建模
   ↓【Profiler 真正定位瓶颈（尚未发生）】
候选：Graph/Static Kernel、GDN、MoE/MC2、Dense SP、MTP
   ↓【回退、正确性、兼容性、负优化约束】
同模型同负载、逐次开关 A/B 试验 → 完整端到端指标
   ↓【有数据才能裁决】
保留 / 条件性启用 / 排除 / 继续验证 → 回写失败经验与证据图谱
```

所有“是否已经验证”的门槛严格区分：source documented、model config matching、hardware compatibility、runtime dispatch、microbenchmark、E2E accuracy/performance。**未拥有硬件**时最多到结构与源码阶段。历史 PR merge、微基准增益、当前真实服务性能属于不同等级。

## 二、演绎推测：哪个瓶颈可能先出现，取决于负载

以下是**待验证假设，不是推理环境测量**。

| 研究情景（均是假设实验） | 高价值候选 | 理由及最重要的反例 | 第一组可证伪数据 |
| --- | --- | --- | --- |
| Qwen3.5-35B-A3B，目标 910C/TP2，c=1，Decode | 先核查 Graph/Host gap，其次 GDN 与 MoE/通信 | 小 Batch 可能受 launch/同步限制，但得物旧实现已在新版 Ascend 有多处删除；没有 Profile 无法断定优先级 | TTFT/TPOT P50/P95、host gap、GDN/MoE时间分解、图命中与编译成本 |
| 同一模型，c=8，混合 Prefill/Decode | 单独观察路由偏斜、专家 GEMM、Graph shape 覆盖、P95 | 不同 Batch 会改变 expert load 和 capture size；历史多流 gate 已删，不直接恢复 | expert_load_histogram、TP 通信、P95 TPOT、失败/回退率 |
| Qwen3.6-27B，目标 910C/TP2，ISL=4096 Prefill | Dense Sequence Parallel / GDN Prefill | 27B 是 Dense，但依然有 48 GDN/linear 层；新版官方文档有 Dense SP 候选，但芯片/软件兼容和实际收益未验证 | Prefill TTFT、reduce-scatter/all-gather、内存与ISL曲线 |
| Qwen3.6-27B，目标 910C/TP2，c=1 Decode | GDN Decode / Host gap / MTP | **不应**套用 MoE Router GEMM；8:1 CUDA 特例不符合 3:1 头数 | GDN recurrent state latency、TPOT、采样正确性与自然接受率 |
| Qwen3.5-397B-A17B，B200 外部参照，Prefill | 专门检查 FlashInfer GDN Prefill | 外部 Blackwell/GDN 性能案例不代表 910C；不能直接把 CUDA/CuTe-DSL Kernel 移植到 AscendC | 只借鉴 shape guard、head_dim、CUDA版本与回退，非本项目性能证据 |

**先决条件**：目标用户当前没有 910C。上述“910C/TP2”只代表未来研究设定；官方 [vLLM-Ascend v0.30.0 稳定版](https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/release_notes.html) 是需要核验的候选版本，不代表已经确认 910C + 35B-A3B + TP2 的官方支持和兼容性。官方发布重点是特定型号和模型，范围外组合不可从发布公告外推支持。

## 三、推测如何被证明或推翻

### 假设 A：低并发“调度型瓶颈”

**推断依据**：得物小并发作者报告和 vLLM-Ascend [Graph 模式/Static Kernel 文档](https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/feature_guide/graph_mode.html)。

- 若 Profiling 表示 Host gap 很高、Kernel 碎片化、图捕获稳定 → 先验证静态图/静态 Kernel；若 Host gap 很低，而 GDN/MoE 算子时间占主导 → 降级这条路线。
- 验证要记录启动/编译时间、静态 Kernel 真实命中、graph 捕获范围、GPU/NPU 内存与延迟，而不是只比较单个请求速度。
- **反例**：Graph 改动可能增加启动耗时、内存开销，某些动态形状回退；不能在所有 c=1/8 中假设相同改善。
- **准入**：上游 README 和 model tutorial + 设备实际支持明确，之后真实 traces，再进行 A/B。

### 假设 B：MoE 的“路由形状与通信”比某一个 Kernel 名字更关键

**推断依据**：35B-A3B 模型 256 experts/top8、397B-A17B 模型 512/top10；NVIDIA MoE Perf Guide 指出专家完全均匀的 benchmark 不一定等价于线上负载。官方 [Qwen3.5 397B 部署示例](https://github.com/vllm-project/vllm-ascend/blob/main/docs/source/tutorials/models/Qwen3.5-397B-A17B.md) 列有 `enable_fused_mc2`、shared expert overlap 等选项。

- 需先收集每 expert 的 tokens、路由分布偏斜、grouped GEMM M/N/K、dispatch/combine 耗时、TP/EP 链路。
- 根据官方环境实际支持再逐个 A/B：无融合 baseline → 单项路由/通信改变 → 可能的 MC2/重叠 → 组合方案。**不直接恢复被移除的 vLLM-Ascend 旧 weight prefetch/overlap gate。**
- 如果改善只出现在人工均匀路由，真实负载不改善，标成“微基准有效 / 真实服务不支持结论”。

### 假设 C：Dense 并非传统纯全注意力，特别注意 Qwen3.6-27B

**模型结构事实**：Qwen3.6-27B 官方配置的 `layer_types` 包含 48 `linear_attention`、16 `full_attention`，但没有 MoE Experts。这意味着 **GDN 优化可能适用，MoE 路由不适用**。

- 对长输入 Prefill，验证 [vLLM-Ascend 0.30 Sequence Parallel](https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/feature_guide/sequence_parallelism.html) 是否在目标硬件/拓扑有支持，若支持则对照 ISL=512/4096/8192 的 TP 通信和 TTFT。
- 对 Decode，分析 GDN gate / state update / recurrent 计算与图形状。不能使用“Dense=传统 Attention”和“官方 MTP 头存在=一定加速”两个捷径。
- 对 vLLM [PR #51674](https://github.com/vllm-project/vllm/pull/51674)：特殊 CUDA MTP-GDN kernel 仅处理 `num_v_heads=8*num_k_heads`，我们五个目标模型比例 2、3、4:1，都不满足；这不限制其他 GDN 算法与实现。

### 假设 D：MTP 只有在自然草稿接受率高时才值得启用

- 需要对真实业务语料测量 `accepted_draft_mean_natural`、MTP草稿/Target verify 代价、状态回退开销、图覆盖、正确性。
- 不能以 NVIDIA [Qwen3.8 受控草稿数 2.3 的性能案例](https://nvidia.github.io/TensorRT-LLM/latest/deployment-guide/deployment-guide-for-qwen3.8-qwen3.5-on-trtllm.html) 预测我们业务 TPOT。
- 设计对照：无 MTP → 自然 prompt MTP → 同条件模型/采样器消融，人工控制接受率仅用于机制实验，不能掺入生产基准。

## 四、为什么不能简单叠加多个“提速百分比”

若某段已知算子占总串行耗时比例为 `f`，该段在相同语义下被加速 `s` 倍，其理想 Amdahl 上界为：

```text
End-to-end speedup ≤ 1 / ((1 - f) + f / s)
```

这个关系仅在 `f` 真实测得、其他部分不变且无额外通信/调度/排队开销时才有解释意义。

例如 **纯数学假设**：某 Kernel 占总延迟 30%，自身 2 倍加速，则整体理想加速只有 `1/(0.7+0.3/2)≈1.176×`，即总延迟减少约 15.3%（不是 50%）。**30% 与 2 倍都是教学假设，不是任何 Qwen/Ascend 实测数据**。在异步并行、通信重叠、批量调度和排队存在时，实际效果甚至可能不同方向。

### 不同指标也不能互相替代

- `TTFT` 主要涉及排队、Prefill、首 token 调度及服务配置。
- `TPOT` 是生成阶段单位输出时间；MTP 接受率会影响这一指标。
- `TPS/requests/s` 还取决于 Batch/并发/调度策略；c=1 TPOT 降低不等于高并发吞吐提高。
- `P95` 可能比 P50 更早暴露死锁、路由不均、图回退和显存压力。

## 五、实验计划和数据合同

仓库已提供 [标准输入、五个实验情景、十条可证伪假设](../research/decisions/qwen-fullchain-hypotheses-v1.json)，以及从结构数据自动派生的 [完整决策生成器](../tools/build_qwen_decision_pipeline.py)。

每组实验必须记录：模型/权重 SHA、官方框架及关键算子 SHA、驱动/CANN、硬件拓扑、TP/EP/DP、precision、Qwen版本/配置、ISL/OSL/c、warmup/采样重复、TTFT/TPOT E2E p50/p95、host gap、通信时间、GDN/MoE占比、自然/受控 MTP接受率、correctness/稳定性/回退。

对照顺序先做 baseline/profile，再逐项对照 Graph/GDN/MoE 或 Dense SP、MTP，最后测试叠加并判断交互影响。多个开关一起变化的结果不能归因到某一个算子。

**结果分级**：

| 结论 | 当前能否成立 | 证据要求 |
| --- | --- | --- |
| 某模型确实有 GDN/MoE 结构 | **可通过官方 config 确认** | 精确 config revision、字段原值 |
| 某历史 CUDA GDN MTP 分支不能处理 2/3/4:1 头比 | **可静态确认（限定 PR #51674）** | 源码 guard + config |
| 官方版本提供某优化开关/示例 | **可以通过文档确认** | 特定 release / 文档，适用卡/模型仍待核 |
| 910C 某 Kernel 是实际瓶颈 | **不能确认** | 真实硬件 Profiler |
| 启用后提高 TPOT/TPS | **不能确认** | 同硬件同负载 A/B + 误差与质量 |
| 多算子叠加最终加速多少 | **不能确认** | 控制变量/消融/端到端测量 |

## 六、结果展现与可操作产物

- [纯标准库决策推演程序](../tools/build_qwen_decision_pipeline.py)：从 15 案例、5 模型、12 PR、8 失败和 10 假设推导 5 组情景；每条含来源、适用范围、风险、需要采集的指标、回退条件。
- [独立 HTML 可交互工作台](../tools/render_qwen_decision_dashboard.py)：六阶段流程、研究情景切换、动态优先级筛选、结构参数、性能待测卡、可展开的原始证据、验证/回退计划、JSON 导出。**不需要网络或额外 Python 包**即可在浏览器打开生成的 HTML 文件。
- [GitHub Actions 全链路构建](../.github/workflows/qwen-fullchain.yml)：离线单元测试、五情景 JSON + HTML 生成、禁止填假实测值检查、上传完整交付包 Artifact。
- 研究事实、逻辑假设、示例测试参数、实际运行结果分别存在不同字段，未来接入真实 Profiler 才能升级数据等级。

运行命令：

```bash
python3 -m unittest discover -s tests -p 'test_qwen_fullchain_pipeline.py' -v
python3 tools/build_qwen_decision_pipeline.py --output build/qwen-fullchain-decision-v1.json
python3 tools/render_qwen_decision_dashboard.py --output build/qwen-fullchain-dashboard-v1.html
```

浏览器直接打开 `build/qwen-fullchain-dashboard-v1.html`，无需后端或外部服务。**页面在无机器阶段展示的是“证据驱动的推断链 + 下一步实验”和“没有真实性能结果”的明确边界，不是把设计图充作真实部署。**
