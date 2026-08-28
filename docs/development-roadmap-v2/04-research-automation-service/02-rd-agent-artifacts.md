# 04-02 RD-Agent与可复现Artifact

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

