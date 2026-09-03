# 04-02 RD-Agent与可复现Artifact

## 当前最小切片

当前只实现Adapter边界和可复现元数据，不调用真实LLM或RD-Agent Provider。`ReproducibilityManifest`固定DataVersion、
数据Artifact Hash、依赖锁Hash、镜像Digest、参数Hash、随机种子和评估协议版本，并生成确定性内容Hash。
`CandidateCodeScanner`在代码进入Sandbox前拒绝网络、进程、Secret、动态执行和运行时安装依赖；
`FixedRDAGENTAdapter`只登记扫描通过的候选代码Artifact，不拥有quant生产Registry权限。

本切片测试覆盖Hash稳定性、环境变更产生新Hash、安全扫描拒绝和候选Artifact元数据校验。真实Provider调用、SBOM/许可证
服务、对象存储发布和完整Artifact复现留在后续实现；不得把本地扫描结果当作生产候选审批。

当前同时提供不可变对象存储Adapter和最小供应链门禁：写入前验证Artifact SHA-256，URI冲突且内容不同立即拒绝；
依赖不在允许列表、许可证不在允许列表或存在高危漏洞时拒绝候选。当前存储实现仅用于本地测试，生产MinIO/S3、SBOM
生成及漏洞数据库接入仍需在后续环境集成中完成。

已补充`S3ArtifactStore`，支持通过Endpoint、Bucket和Secret连接MinIO/S3，并在对象写入与读取时再次校验Hash；
同时提供幂等的`ModelCallAuditStore`，记录Provider、模型、Prompt版本、输入Hash、Token数和成本。真实环境仍需由部署配置
提供凭证，禁止把凭证写入代码、锁文件或Artifact。

`ProviderAdapter`已实现严格的`CandidateProposal`输出Schema和响应大小门禁。非法JSON、缺少支持证据/反例/失败原因、
额外字段、负Token/成本或超大响应均失败关闭；模型调用审计先于Schema解析写入。`FixedModelProvider`仅用于本地契约测试，
真实Provider切换不得改变Domain契约。

## 实施步骤

1. 在Adapter层接RD-Agent，Domain只识别研究假设、候选Artifact和结果。
2. 每次模型调用保存Provider、modelId、PromptVersion、输入Hash、Token和成本。
3. 生成代码先进行静态扫描、依赖允许列表、SBOM和许可证检查，再进入Sandbox。
4. 实验固定DataVersion、镜像Digest、依赖锁、参数、随机种子和评估协议。
5. 研究结果必须包含支持证据、反例、失败原因和不确定性，不能只报告最佳收益。

## 测试

- Provider切换不改变Domain契约。
- 候选代码中的网络、Secret和动态安装请求被拒绝。
- 相同Artifact和环境可重现实验指标。
- 模型输出不符合Schema时有限修复后失败关闭。
