# vLLM-Ascend v0.23.0 → v0.30.0rc2：得物文章相关源码映射

> 检索日期：2026-10-30。此文件来自官方 GitHub 固定 tag 的公开源码核对、官方配置文档；不是得物内部分支 diff，更不是 NPU 运行测试。

## 1. 版本固定

- `vllm-project/vllm-ascend@v0.23.0` = `5cb98caaadeff42b5b62b996e34bb2aaa29d20fd`（Git refs/tags API 已核查）。
- `vllm-project/vllm-ascend@v0.30.0rc2` = `8fde6d4e335fe300e2b949aab0e31659cce0811d`（Git refs/tags API 已核查）。
- 所列 ref 是 Git 版本，不表示此二者的编译环境或 CANN/驱动版本已具备。

## 2. 源码路径及名称初查（注意证据等级）

| 研究项 | 旧版本 v0.23.0 | 新版本 v0.30.0rc2 | 目前结论 |
| --- | --- | --- | --- |
| MoE 共享专家多流 | `vllm_ascend/ops/fused_moe/fused_moe_0_23_0.py` 中找到 `multistream_overlap_shared_expert` | 旧文件原路径 404；[`vllm_ascend/ops/fused_moe/shared_experts.py`](https://github.com/vllm-project/vllm-ascend/blob/8fde6d4e335fe300e2b949aab0e31659cce0811d/vllm_ascend/ops/fused_moe/shared_experts.py) 含 `multistream_overlap_shared_expert` 与 `shared_experts_calculation_stream` | 文件结构已变化，需做事件/等待/预取语义检查；不能原样移植 |
| FUSED_MC2 | 文中涉及 MC2/MoE 通信 | [`ops/fused_moe/fused_moe.py`](https://github.com/vllm-project/vllm-ascend/blob/8fde6d4e335fe300e2b949aab0e31659cce0811d/vllm_ascend/ops/fused_moe/fused_moe.py) 中有 `FUSED_MC2` 名称 | **仅确认名称**，未做配置和性能验证 |
| Block Table | [`worker/block_table.py`](https://github.com/vllm-project/vllm-ascend/blob/5cb98caaadeff42b5b62b996e34bb2aaa29d20fd/vllm_ascend/worker/block_table.py) 含 `_compute_slot_mapping_kernel` | 同路径仍在，含该符号 | CPU fast path 的等效逻辑是否存在未确认 |
| GDN | `ops/gdn.py` 含 `l2norm_fwd` | 同路径仍在、仍含 `l2norm_fwd` | L2Norm 是否融入 recurrent kernel 未确认 |
| MinTokens EOS 缓存 | `sample/rejection_sampler.py` 未找到文章方法名 `_apply_min_tokens_spec_cached` | 同路径仍未找到该名字 | **不能由此推断没有等价缓存机制**；需按调用链追踪 |
| `model_runner_v1.py` | 文件存在；文章私有 `_prev_num_reqs` 名未匹配 | 文件存在；该私有名字未匹配 | 原始名称有差异，需针对 copy/fill 分支人工审查 |
| 词表并行 argmax | 文章 `_draft_greedy_shard_argmax` | `spec_decode/step3p5.py` 存在但此命名未匹配 | 是否有功能等效实现未确认 |

**证据等级**：文件存在=确认；指定字符串存在=确认；运行逻辑与功能等价=待验证；性能收益=尚无实测。

## 3. 官方文档已明确提供的配置与限制

来自 [v0.30.0rc2 Additional Configuration](https://docs.vllm.ai/projects/ascend/en/v0.30.0rc2/user_guide/configuration/additional_config.html)：

- `ascend_compilation_config.enable_static_kernel` 默认 `false`，更适合固定形状；要记录启动编译时间与稳态收益。
- `enable_super_kernel` 默认继承 `enable_static_kernel`，且依赖 Static Kernel；二者必须作为一个独立实验组合，不得误把它们视为两个完全独立开关。
- 不直接将得物旧版未公开的 SuperKernel patch 复制到新版。

来自 [v0.30.0rc2 Speculative Decoding Guide](https://docs.vllm.ai/projects/ascend/en/v0.30.0rc2/user_guide/feature_guide/speculative_decoding.html)：

- 已明确列出 `mtp` 等方法；在 NPU 上 `(num_speculative_tokens + 1) <= 16` 的限制应纳入配置校验。
- 把 `num_speculative_tokens` 从 K=0/1/2/4 做受控对比，记录 token 接受率，且要求 graph 捕获尺寸覆盖对应形状。
- 正在演进的动态投机长度策略根据并发变化调 K，建议列为研究项；不要假设所有型号/runner 组合都能直接用。

## 4. 下一轮需要解决的真实差异

1. 分别读取两 tag 的 MoE 和 rejection sampler 的函数级 diff，标出 data dependency 与 H2D 同步次数。
2. 以两版适配的 API 各写一个**仅展示配置、不启动服务**的 profile/benchmark 入口。
3. 仅在拥有匹配 NPU+CANN 环境后运行 c=1/4/8、1024→512、同模型 revision 的 A/B。
4. 对比 TTFT、TPOT、P50/P95/P99、请求正确性与错误率，验证是否存在负优化。
5. 对 Qwen3.6-27B 密集模型与 Qwen3.5-35B-A3B MoE 分开建基线。

## 来源与原文边界

- [得物上篇](https://mp.weixin.qq.com/s/ML52pF8YyezpUDfIEV3IWQ)
- [得物下篇](https://mp.weixin.qq.com/s/GXaZWhIZ25ifH07iaTxfZQ)
- [vLLM-Ascend v0.23.0](https://github.com/vllm-project/vllm-ascend/tree/5cb98caaadeff42b5b62b996e34bb2aaa29d20fd)
- [vLLM-Ascend v0.30.0rc2](https://github.com/vllm-project/vllm-ascend/tree/8fde6d4e335fe300e2b949aab0e31659cce0811d)

原作者报告的 14.22ms → 5.0ms 等数据只能标记为 `article-reported`，当前本研究未在 NPU 验证。
