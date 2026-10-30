# Qwen 模型资料库与权重备份方案（2026-10-30）

> 状态：**目录和代码已建，尚未完成任何模型权重到 Google Drive 的下载/上传/回读**。不要把 Hugging Face 链接或仅有模型卡误标为「已备份」。

## 三端位置

- 研究代码：\`cao772/ascend-llm-inference-optimization\`，工作分支 \`research/2026-10-30-foundation\`（Draft PR #4，不修改 main）。
- Notion：<https://app.notion.com/p/4097bbed1352816fad17d3102052812e>。
- Drive 根目录：<https://drive.google.com/drive/folders/178-RqShzz4aJzZx7B436BdQagI8BT6yb>。
- Drive 权重目录（目前为空）：<https://drive.google.com/drive/folders/1NVaimWqjE6a0uoGBh-kSxAJrivBEnqsm>。

## 「Qwen 全套」的边界

Qwen 包含多代模型、Dense/MoE、Coder、VL、Embedding、Reranker、ASR、Omni、不同精度和大量衍生版本。
不能把 \`catalog/qwen-research-models.json\` 的 **6 个优先研究 checkpoint** 当成全部 Qwen。
先按官方组织持续检索：<https://huggingface.co/Qwen/models>，官方项目：<https://github.com/QwenLM/Qwen3.8>。
同一模型的 BF16/FP8/GGUF 等不必全部备份；应按研究需求、许可和可用空间选择具体版本。

### 优先模型（全部未上传权重）

| 模型 | 优先级 | 用途 |
| --- | --- | --- |
| Qwen/Qwen3.5-35B-A3B | P0 | 得物文章的 MoE/GDN/MTP 基线 |
| Qwen/Qwen3.6-27B | P0 | 已讨论过的服务模型，密集模型对照 |
| Qwen/Qwen3.6-35B-A3B | P1 | 新一代 MoE 与 MTP |
| Qwen/Qwen3.8-27B | P1 | 新一代模型与软件栈兼容性 |
| Qwen/Qwen3-0.6B | P1 | 轻量运行与下载完整性测试 |
| Qwen/Qwen3-Embedding-0.6B | P1 | 文档检索/向量化研究 |

单个 Qwen3.5-35B-A3B 的官方 Hugging Face 文件列表约 71.9 GB，Qwen3-0.6B 约 1.52 GB；
**容量是来源页面展示的约数，不是我们实际下载计算值**。具体以固定 revision 的远端文件列表为准。
模型权重属于大型二进制，**不得提交 GitHub**。

## 1. 生成官方模型清单

\`\`\`bash
python3 tools/qwen_inventory.py --output build/qwen-offline.json
python3 tools/qwen_inventory.py --online --output build/qwen-live-metadata.json
python3 tools/qwen_inventory.py --online --only Qwen/Qwen3.6-27B
\`\`\`

\`--online\` 会尝试从 Hugging Face 获取当前 revision、文件数量、许可声明与文件体积。
网络不可用、文件大小信息不完整时，状态必须保留为 error/unknown，不能凭估计宣称完成。
\`build/\` 中数据仅是索引、不是权重。

## 2. 单模型受控下载（在有足够磁盘与外网的工作站/服务器执行）

\`\`\`bash
python3 -m pip install -U huggingface_hub
python3 tools/download_qwen_snapshot.py --model-id Qwen/Qwen3-0.6B
# 仅需要元数据：真正执行，但不下载权重
python3 tools/download_qwen_snapshot.py --model-id Qwen/Qwen3-0.6B --execute --max-gb 3
# 完整权重：明确打开开关，先核实磁盘容量、许可和网络
python3 tools/download_qwen_snapshot.py --model-id Qwen/Qwen3-0.6B --execute --include-weights --max-gb 3
\`\`\`

工具默认 dry-run；明确指定 \`--execute\` 才启动传输。执行时从官方 Hub 锁定 SHA revision，
要求全部文件大小可核对，超出 \`--max-gb\` 则拒绝。完成后逐文件计算 SHA-256，并写 \`local-checksums.json\`。
此 SHA-256 是**本地完整性记录**，不能单独证明与官方哈希一致；如果官方提供 LFS/Xet 校验数据还应逐项比对。
下载日志要记录带宽/失败/重试、revision、license、总字节、验证结果。

## 3. 上传至 Google Drive（需有 Google Drive 授权与足够容量）

运行上一步并验证本地快照后，才允许启动到 Drive 的上传。例如在已授权 rclone 的机器上：

\`\`\`bash
# 此处 gdrive: 是你自己已配置好的 rclone remote；不要把 OAuth token 放进 GitHub。
rclone copy "model-checkpoints/Qwen3-0.6B" \
  "gdrive:AI-Infra/Qwen/weights/Qwen3-0.6B" --dry-run
# 核查 dry-run 后，再移除 --dry-run 执行真实上传
rclone check "model-checkpoints/Qwen3-0.6B" \
  "gdrive:AI-Infra/Qwen/weights/Qwen3-0.6B"
\`\`\`

示例远端路径**不等于当前已创建的 Drive 文件夹 ID**；实际配置必须指向本项目的真实目录。
针对多 GB 文件应分批上传，必要时采用支持断点续传的方式，之后核验 Google Drive 远端字节、
文件数量和适用的校验和。上传成功才更新模型状态为 \`uploaded_to_drive: true\`。

## 4. 不同工作物的归档原则

- GitHub：下载器、环境/版本锁、Benchmark、差异补丁、GitHub Actions；不存未经授权的原文镜像或大模型权重。
- Notion：模型版本和 license、实验假设/结论、下一步和失败记录。
- Drive：原始模型权重、tokenizer/配置、模型卡、profiling 大文件、实验报告。每模型独立文件夹包含固定 SHA revision 与校验清单。
- 所有结果明确区分 \`article-reported\`、\`hypothesis\`、\`synthetic\` 与 \`measured\`。

## 5. 下一批性能研究

1. 固定 vLLM-Ascend **0.23.0**（文章版本）与当下适配版本；检查 release/tag 和 CANN、驱动兼容性。
2. Qwen3.5-35B-A3B（MoE）与 Qwen3.6-27B（dense）分别建立 c=1/4/8、1024→512 的 TPOT/TTFT/E2E 基线。
3. 分别实验 HCCL AIV、Static Kernel、CUDAGraph 捕获、MTP；不能跨不同硬件/数据集盲目套用百分比。
4. 将下篇的 MinTokens 缓存、Block Table CPU 快路径、词表并行 argmax 按版本差异逐项映射；保留 fallback 和正确性测试。
5. 后续探索 vLLM-Ascend 0.30 系列与 Qwen3.8-27B 支持，但不能把最新版实验与旧版得物基线混成一条曲线。

## 外部来源

- <https://huggingface.co/Qwen/models>
- <https://huggingface.co/Qwen/Qwen3.5-35B-A3B/tree/main>
- <https://huggingface.co/Qwen/Qwen3.6-27B/tree/main>
- <https://huggingface.co/Qwen/Qwen3.8-27B/tree/main>
- <https://docs.vllm.ai/projects/ascend/en/main/user_guide/support_matrix/supported_models.html>
- <https://github.com/vllm-project/vllm-ascend/releases>
- <https://mp.weixin.qq.com/s/ML52pF8YyezpUDfIEV3IWQ>
- <https://mp.weixin.qq.com/s/GXaZWhIZ25ifH07iaTxfZQ>
