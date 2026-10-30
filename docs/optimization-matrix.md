# 昇腾 910C 文章优化项 → 上游源码研究矩阵（起始版）

> 来源：得物技术 2026-10-21 和 2026-10-26 两篇文章。本表是**研究候选清单**，不是已经复现。上游实际文件、适用版本、开关是否仍生效，待固定上游 tag/commit 后逐项核查。

| 优化方向 | 文章入口 | 边界与风险 | 验证状态 |
| --- | --- | --- | --- |
| 框架版本 | vllm-ascend 0.22.0rc1 → 0.23.0 | CANN / 驱动 / 模型 revision | 未验证 |
| HCCL AIV | `HCCL_OP_EXPANSION_MODE=AIV` | TP/SoC/通信拓扑 | 未验证 |
| 静态 Kernel | Static Kernel + FULL_DECODE_ONLY | 捕获形状、初始化成本 | 未验证 |
| HBM 分配 | `PYTORCH_NPU_ALLOC_CONF` | 显存碎片、负载差异 | 未验证 |
| CPU 分配 | jemalloc | 非普适收益，不当作零风险 | 未验证 |
| MoE 多流 | shared expert overlap / weight prefetch | 数据依赖、同步正确性 | 未验证 |
| Block Table | `worker/block_table.py` CPU fast path | token 数门槛 | 未验证 |
| GDN | `ops/gdn.py` + recurrent kernel | 可能在 c=8 负优化 | 未验证 |
| MinTokens | `sample/rejection_sampler.py` cache | 语义与失效条件 | 未验证 |
| 贪婪采样 | vocab parallel argmax | 仅条件成立时等价；tie-break 需验 | 未验证 |
| FUSED_MC2 | 通信/计算融合 | CANN/SoC 依赖 | 未验证 |
| SuperKernel | 组合小算子 | 编译与 warmup 负担 | 未验证 |
| AscendC | o_proj + AllReduce + residual + RMSNorm | TP=2/bf16/shape 与 fallback | 未验证 |
| MTP | 多 Token 草稿 + CUDAGraph | 接受率、capture sizes | 未验证 |

## 研究顺序

1. 锁定上游 vLLM-Ascend tag/commit 与支持矩阵。
2. 固化标准输入输出长度、并发、TTFT/TPOT/E2E/P95/P99/吞吐基线。
3. 每次只调整一个变量，测试性能和结果一致性。
4. 记录无效、失败、负优化；不得将文章报告或模拟数据写作本仓库实测。
5. 确认回退策略后再研究源码修改及 AscendC 算子。

## 来源
- [上篇](https://mp.weixin.qq.com/s/ML52pF8YyezpUDfIEV3IWQ)
- [下篇](https://mp.weixin.qq.com/s/GXaZWhIZ25ifH07iaTxfZQ)
- [vLLM](https://github.com/vllm-project/vllm)
- [vLLM-Ascend](https://github.com/vllm-project/vllm-ascend)
