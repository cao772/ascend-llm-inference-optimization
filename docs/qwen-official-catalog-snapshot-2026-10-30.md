# Qwen 官方公开模型目录｜首轮完整分页快照（2026-10-30）

## 采集事实

- 直接使用 Hugging Face 的 `/api/models?author=Qwen`，每页 100 条，依照官方 Link 分页，**5 页采集完毕，469 个唯一 model ID**。
- 实际运行：GitHub Actions [#41041892981](https://github.com/cao772/ascend-llm-inference-optimization/actions/runs/41041892981)，结论 success。
- 完整 JSON：[catalog/qwen-official-inventory.json](../catalog/qwen-official-inventory.json)。永久文件由后续研究分支 CI 成功写入；其内容明确 `complete: true`、`model_count: 469`。
- 采集工具：[tools/discover_qwen_models.py](../tools/discover_qwen_models.py)，6 个纯离线测试。仅下载元数据，不包含模型权重、私有文件或用户凭证。
- 这是**某个时间点 Hugging Face 的 Qwen 官方作者账户可见条目**，不是「全部历史 Qwen 权重、全部镜像、全部量化版本或所有 ModelScope 仓库」的证明。

## 按模型名称进行启发式分组（总计 469）

| 研究分类 | 条目数 |
| --- | ---: |
| 文本及其他/未精准归类 | 316 |
| 视觉语言 | 62 |
| 代码相关 | 44 |
| Omni/Audio | 11 |
| 图像 | 11 |
| Embedding | 8 |
| 语音识别 | 6 |
| 语音合成 | 6 |
| Reranker | 5 |
| **合计** | **469** |

**分类只是文件名关键词的初筛**；例如某些视觉多模态模型未在名称中明确带 VL，不能由此判断功能不支持。

## 当前数据质量和边界

- 469 个条目的 `revision` 均非空；真实版权/商用许可仍必须检查各个 Model Card；
- 批量 API 响应的 `license_reported_by_hub` 在当前快照全部为 `null`；这是**未知**，不表示没有许可限制；
- 这些条目全部标记 `weights_mirrored_to_drive=false`。
- Google Drive 的 [模型归档文件夹](https://drive.google.com/drive/folders/178-RqShzz4aJzZx7B436BdQagI8BT6yb) 已创建，模型权重未上传。
- 适用硬件需按 [vLLM-Ascend Supported Models](https://docs.vllm.ai/projects/ascend/en/main/user_guide/support_matrix/supported_models.html) 每型号/算子功能核查；官方支持列表不等于当前主机实测通过。

## 下一步（不影响主分支）

1. 从 469 中筛选低延迟推理相关的 Qwen3.5-35B-A3B / Qwen3.6-27B / Qwen3.8-27B / Qwen3-0.6B 等，核验 Model Card 许可、权重大小、文件签名。
2. 小模型（例如 Qwen3-0.6B）完成「本地下载→文件 hash→Drive 上传→远端回读」试点后，才执行较大模型。
3. 研究 [v0.23.0 → v0.30.0rc2 源码路径变化](./upstream-v0.30.0rc2-gap-analysis.md)，建立硬件兼容性实测清单。
