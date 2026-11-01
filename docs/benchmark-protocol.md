# 基准对比协议 v0.1

此仓库当前尚无真实昇腾推理环境实测。代码只比较外部提供的 JSON 记录。

记录字段至少包含：
- `run_id`、`provenance`（`measured` / `reported` / `synthetic`）；
- `model_id`、`model_revision`；
- `hardware`：设备/芯片拓扑、卡数、TP、DP 等；
- `software`：驱动、CANN、vLLM、vLLM-Ascend 版本或 commit；
- `workload`：数据集、并发、输入输出 Token、采样策略；
- `metrics`：`tpot_ms` 必填，`ttft_ms`、`e2e_ms`、`throughput_tps` 及 P95 可选，均为正数。

对比时默认要求 model、revision、hardware、workload 完全一致，允许软件版本不同以评价框架升级；不满足则报错。跨环境对比必须加 `--allow-mismatch`，输出会保留警告。

`python -m unittest discover -s tests -v` 测试计算逻辑。

`python -m tools.compare_runs baseline.json candidate.json` 对比真实测量，默认拒绝非 measured 来源。

`python -m tools.compare_runs baseline.json candidate.json --include-nonmeasured` 可处理文章数据或模拟数据，但不能据此声称已复现。

## 后续真实压测
以固定数据集和采样设置分别测并发 c=1/4/8，记录 warmup、请求数、P50/P95/P99、准确性回归、msprof 分析文件。数据区分原始 NPU 实测、外部文献、synthetic 三类。
