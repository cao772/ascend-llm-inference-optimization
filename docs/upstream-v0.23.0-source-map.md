# 上游源码定位快照（2026-10-30）

本记录仅证明**公开源码的版本及文件/标识符存在情况**，未运行 NPU，也未确认得物内部分支已合并上游。

## 已核对的 Git 标签

| 项目 | 研究版本 | Git commit（直接校验 Git refs/tags） |
| --- | --- | --- |
| [vLLM-Ascend](https://github.com/vllm-project/vllm-ascend) | v0.23.0 | `5cb98caaadeff42b5b62b996e34bb2aaa29d20fd` |
| [vLLM](https://github.com/vllm-project/vllm) | v0.23.0 | `0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665` |

这两个 tag 可追踪，不等于说两者在所有模型/设备组合下已验证兼容。

## vLLM-Ascend v0.23.0 文件核对

| 文章讨论 | 官方仓库对应路径 | 核查结果（静态字符串检索） |
| --- | --- | --- |
| Block Table CPU 快路径 | [`vllm_ascend/worker/block_table.py`](https://github.com/vllm-project/vllm-ascend/blob/5cb98caaadeff42b5b62b996e34bb2aaa29d20fd/vllm_ascend/worker/block_table.py) | 文件存在，`_compute_slot_mapping_kernel` 存在；文章的低并发 CPU 快路径尚未确认 |
| MinTokens EOS 掩码缓存 | [`vllm_ascend/sample/rejection_sampler.py`](https://github.com/vllm-project/vllm-ascend/blob/5cb98caaadeff42b5b62b996e34bb2aaa29d20fd/vllm_ascend/sample/rejection_sampler.py) | 文件存在，文章名 `_apply_min_tokens_spec_cached` 未匹配；不能据此断言没有等效逻辑 |
| GDN 小算子 | [`vllm_ascend/ops/gdn.py`](https://github.com/vllm-project/vllm-ascend/blob/5cb98caaadeff42b5b62b996e34bb2aaa29d20fd/vllm_ascend/ops/gdn.py) | 文件及 `l2norm_fwd` 名称存在；仍需检查融合调用链 |
| MoE shared expert | [`vllm_ascend/ops/fused_moe/fused_moe_0_23_0.py`](https://github.com/vllm-project/vllm-ascend/blob/5cb98caaadeff42b5b62b996e34bb2aaa29d20fd/vllm_ascend/ops/fused_moe/fused_moe_0_23_0.py) | 文件及 `multistream_overlap_shared_expert` 名称存在；并行实现细节仍需对照 |
| Runner 冗余数据拷贝 | [`vllm_ascend/worker/model_runner_v1.py`](https://github.com/vllm-project/vllm-ascend/blob/5cb98caaadeff42b5b62b996e34bb2aaa29d20fd/vllm_ascend/worker/model_runner_v1.py) | 文件存在，文章中的 `_prev_num_reqs` 名称未匹配；具体条件拷贝待核查 |

下一步：用固定 SHA 的源码构建**逐函数差异与 API 兼容性表**，再对 0.30 发布线重做同样检查；不把某个字符串缺失视为优化未实现的证明。

## 官方更新线索

- [vLLM-Ascend Releases](https://github.com/vllm-project/vllm-ascend/releases)：截至 2026-10-30 已见到 v0.30.0rc1 发布说明（2026-10-12）。
- [支持矩阵](https://docs.vllm.ai/projects/ascend/en/main/user_guide/support_matrix/supported_models.html)：包含 Qwen3.5/3.6/3.8 系列的支持项；具体型号、量化格式、功能与 CANN 版本依矩阵逐项验证。
- [Qwen 官方说明](https://github.com/QwenLM/Qwen3.8)：权重推荐通过官方 Hugging Face / ModelScope 分发，不混入 GitHub 代码仓库。
