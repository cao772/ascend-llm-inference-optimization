# 昇腾大模型推理与算子优化 / Ascend LLM Inference & Operator Optimization

> **V2 离线交互网站 MVP 已开发并通过 Chromium 浏览器验收**：[完整网页源码](design/ascend-explorer-v2/site/)、[可运行单文件构建器](design/ascend-explorer-v2/site/build_site.py)、[GitHub Actions 网页及截图交付](https://github.com/cao772/ascend-llm-inference-optimization/actions/runs/41297454294)；[九展区详细设计](design/ascend-explorer-v2/README.md)。**尚未公网部署、没有 NPU 实测；硬件精确型号规格仍待补齐。**

> 长期研究工程仓库。2026-10-30 初始化；当前仅为研究与基准工具建设，**尚未完成昇腾 NPU 实测**。

## 研究目标
以可复现、可比较、可回滚为原则，研究 vLLM / vLLM-Ascend、昇腾 NPU、MoE、GDN、MTP 投机解码、内存/通信及 AscendC 算子优化。后续可扩展其他模型、GPU/NPU 和服务部署形态。

## 三端事实源
- **GitHub（本仓库）**：代码、配置、基准工具、补丁、Issue、PR、验证记录。
- **Notion**：研究总账、原理解释、实验决策和状态。
- **Google Drive**：论文/文章 PDF、环境快照和大型结果文件。原作者文章不直接复制到公开 GitHub，保留出处链接。

## 起始参考
1. 得物技术《国产算力·昇腾 910C 大模型推理优化（上）：镜像更新与参数调优，提速 40%》（2026-10-21）：https://mp.weixin.qq.com/s/ML52pF8YyezpUDfIEV3IWQ
2. 得物技术《国产算力·昇腾 910C 大模型推理优化（下）：源码修改与算子优化，提速30%》（2026-10-26）：https://mp.weixin.qq.com/s/GXaZWhIZ25ifH07iaTxfZQ
3. vLLM：https://github.com/vllm-project/vllm
4. vLLM-Ascend：https://github.com/vllm-project/vllm-ascend

**重要**：得物文章公开了修改路径、片段和实验结果，未据此确认完整内部优化分支已开源。本文报告的性能数据属于作者环境与负载，**不是本仓库实测**。

## 工作约定
- 不直接覆写上游源码；优先以固定上游 tag/commit + 最小补丁记录差异。
- 优先构建基准与正确性回归，再调整版本、配置、源码、算子。
- 实验数据记录硬件拓扑、CANN、驱动、框架/模型 revision、请求分布、并发、输入输出 token 长度、采样模式、TP/DP、数据集、TTFT/TPOT/E2E/吞吐和 P50/P95/P99。
- 同时记录失败实验，严禁将理论收益、文章收益或模拟数据写作本机/NPU真实测量。
- 性能结论优先使用真实业务负载，比较要控制变量并允许回退。

## 近期范围
请查看 GitHub Issues：环境清点与版本矩阵、论文方法映射、标准压测协议、模型准确性/性能回归、优化实验顺序。

## 版权与来源
上游 vLLM/vLLM-Ascend 代码按各自许可证使用；本文只链接得物文章，不镜像全文或内部未公开源码。