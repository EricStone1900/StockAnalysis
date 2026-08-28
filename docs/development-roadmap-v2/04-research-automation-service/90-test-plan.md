# research-automation-service测试计划

- Domain：实验和PromotionRequest状态机、预算和幂等。
- Sandbox：网络、文件、Secret、Docker Socket、超时、OOM和进程限制。
- Reproducibility：代码、依赖、镜像、数据、参数和随机种子。
- Model：Schema失败、超时、限流、Provider切换和成本上限。
- Supply Chain：SBOM、许可证、锁文件、镜像Digest和高危漏洞。
- Integration：quant独立复算、拒绝、批准和重复请求。
- Isolation：研究数据库用户不能写quant数据库，研究身份不能激活版本。

关键通过条件：任何自动生成代码都不能直接影响DailyAnalysisSnapshot或DailyStrategySnapshot。

