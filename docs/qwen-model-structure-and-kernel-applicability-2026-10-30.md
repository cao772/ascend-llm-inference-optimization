# Qwen 五款模型真实结构 × 算子优化适用矩阵（2026-10-30）

> **状态：官方模型 config.json 静态研究 + 上游特定 PR 分派源码；不包含模型权重或硬件实测。** 研究范围是 5 个模型而不是 Qwen 469 条官方公开模型目录。结构化数据：[选定模型结构矩阵](../research/model-structures/qwen-gdn-structure-matrix-2026-10-30.json)。

## 1. 研究发生的关键变化

不能再仅按“Dense/MoE”将研究分流。Qwen3.5-27B 和 Qwen3.6-27B 没有 MoE Expert 配置，但它们仍采用 **GDN（linear_attention）与 Full Attention 混合架构**，需要研究的 GDN 算子与 MoE 是两条**不同维度**；非 MoE ≠ 没有 GDN。

尤其是 Qwen3.6-27B 的 [官方配置](https://huggingface.co/Qwen/Qwen3.6-27B/raw/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/config.json)：
- `architectures = ["Qwen3_5ForConditionalGeneration"]`，其结构实现仍使用 qwen3_5 架构名称；
- `text_config.num_hidden_layers = 64`，`layer_types` 明确为 **48 层 linear_attention + 16 层 full_attention**；
- `linear_num_key_heads=16`、`linear_num_value_heads=48`（Value/Key=**3:1**）；
- `mtp_num_hidden_layers = 1`；
- 根配置还有 `vision_config` 和 `language_model_only=false`，所以它的原始模型结构也包含视觉配置；但不能由此推断某个具体 OpenAI-compatible 服务已启用视觉输入。

## 2. 官方结构实证矩阵

| 模型 | Dense/MoE | Layers 明示的 GDN / Full | GDN V:K | Experts / TopK | MTP layers 明示 | 此 PR #51674 的 8:1 形状检查 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B/raw/main/config.json) | MoE | 30 / 10（共 40） | **32/16=2:1** | 256 / 8 | 1 | **不通过** |
| [Qwen3.5-397B-A17B](https://huggingface.co/Qwen/Qwen3.5-397B-A17B/raw/main/config.json) | MoE | 45 / 15（共 60） | **64/16=4:1** | 512 / 10 | 1 | **不通过** |
| [Qwen3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B/raw/main/config.json) | Dense（非 MoE） | 48 / 16（共 64） | **48/16=3:1** | 无 MoE Experts | 1 | **不通过** |
| [Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B/raw/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/config.json) | Dense（非 MoE） | 48 / 16（共 64） | **48/16=3:1** | 无 MoE Experts | 1 | **不通过** |
| [Qwen3-Next-80B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct/raw/9c7f2fbe84465e40164a94cc16cd30b6999b0cc7/config.json) | MoE | 该 config **没有明确 `layer_types`**，不填写逐层数量 | **32/16=2:1** | 512 / 10 | 未在此 config 明示 | **仅形状不通过** |

注释：表中的 GDN 与 Full 层数只在 `layer_types` 明确列出时填写。Qwen3-Next 只有 `full_attention_interval=4`，不能把按间隔计算出的数字冒充官方完整逐层列表。

**数据时间版本边界**：对应五个官方模型的 Hugging Face 作者目录 SHA 记录在 JSON 中。2026-10-30 其中 Qwen3.6-27B 和 Qwen3-Next 的 config 已通过其 SHA URL 单独回读；其余三个是 `main` 路径当天读取，虽然目录记录了 revision，但尚未逐一完成“该 SHA 下 config 内容完全一致”的交叉验证。不能暗示所有五个 config 已 hash 锁定。

## 3. 为什么 5 个模型都无法命中 PR #51674 的这个分支？

我们已经读取 [vLLM PR #51674](https://github.com/vllm-project/vllm/pull/51674) 的分派代码以及 `QwenGatedDeltaNetAttention.__init__`：模型配置的 `linear_num_key_heads` 和 `linear_num_value_heads` 直接赋给 `self.num_k_heads` 和 `self.num_v_heads`。该 PR 的特殊 `_can_use_fused_gdn_mtp_decode` 分支明确检查：

```python
self.num_v_heads == 8 * self.num_k_heads
```

我们的五个模型对应的 V/K 比分别为 **2、4、3、3、2**，都不为 8，所以这个 **特定历史 CUDA Kernel 的 Head 比例分派条件**无一满足。这不等于 GDN 算子不能优化，也不等于 Ascend 或其他框架的 GDN 均要求 8:1。

其他 guard 还包括 MTP-only spec batch、BF16/FP32 recurrent state、CUDA decode op 是否构建、`state_indices` 和 ≤8 speculative tokens。形状检查已经不通过时，不需要有 GPU 就能排除该条分支；若 shape 通过，也**仍需真实 Trace 验证命中和正确性**。

## 4. 结构维度与已收集案例关联

| 技术方向 | 值得关联的原有案例 / PR | 研究目标 | 此阶段限制 |
| --- | --- | --- | --- |
| GDN Prefill | [FlashInfer #3001](https://github.com/flashinfer-ai/flashinfer/pull/3001) / [#3155](https://github.com/flashinfer-ai/flashinfer/pull/3155) / [vLLM #40717](https://github.com/vllm-project/vllm/pull/40717) | 找到融合计算、head dim 与 Prefill shape 边界 | CUDA/Blackwell，和 AscendC 的实现不同 |
| GDN Decode/MTP | [vLLM #51674](https://github.com/vllm-project/vllm/pull/51674) 与得物 910C 案例 QINF-001 | 分离 MTP state rollback / recurrent state update / RMSNorm | 五个目标模型都不满足该特定 CUDA PR 的 8:1 Head guard；应优先研究一般化的非 8:1 方案 |
| MoE 路由/小 GEMM | QINF-001（35B）、QINF-005（Qwen3）、QINF-006（397B）和 [TensorRT-LLM MoE Perf Guide](https://nvidia.github.io/TensorRT-LLM/latest/developer-guide/moe-perf-guide.html) | TopK 8 与 10、256 与 512 专家的负载不均、grouped GEMM、通信重叠 | 不能套用纯 Dense 27B，也不能把专家数当成真正活跃专家数 |
| AllReduce + RMSNorm | [SGLang #22664](https://github.com/sgl-project/sglang/pull/22664)、[#24629](https://github.com/sgl-project/sglang/pull/24629)、[Ascend #12119](https://github.com/vllm-project/vllm-ascend/pull/12119) | 观察“开关白名单→正确性回退→旧路径移除”的版本生命周期 | 需要 TP>1/对应芯片/后端，无法从模型 config 单独证明融合可用 |
| 结构与版本兼容 | Qwen3.6-27B 的 `Qwen3_5ForConditionalGeneration` | 模型名称、config 架构名、Transformers/vLLM/Ascend 兼容矩阵分开核查 | 不得直接推断远端服务的实际运行架构/模型 revision |

## 5. 已有离线工具与验收

- `research/model-structures/qwen-gdn-structure-matrix-2026-10-30.json` 记录官方源、修订记录、结构字段和证据边界。
- `tools/analyze_qwen_structures.py` 可以在本机**只读**一个已有 `config.json`，输出 GDN 头数、MoE、明确的 layer_types 统计，以及该 **PR #51674 特定 Head guard** 的静态状态。仅需 Python 标准库。
- `tests/test_analyze_qwen_structures.py` 测试 Dense + GDN 共存、结构比例、头数 guard 与未知元数据逻辑。

命令：

```bash
python3 tools/analyze_qwen_structures.py --matrix
python3 tools/analyze_qwen_structures.py --config /path/to/config.json --model-id Qwen/Qwen3.6-27B
python3 -m unittest discover -s tests -p 'test_analyze_qwen_structures.py' -v
```

本阶段**没有下载任何模型权重，也没有运行 NPU/GPU 性能 Benchmark**。下一批研究重点是对 3.5/3.6 多模型的 `GDN linear attention` 和 MoE 的算子形状分组，进一步把源代码级优化分为「理论可能」「形状满足」「真实分派命中」「可重现提速」四类。
