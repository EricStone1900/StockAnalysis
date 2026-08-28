# 04-01 实验骨架与Sandbox

## 实施步骤

1. 创建ResearchExperiment、ExperimentRun、CandidateArtifact和PromotionRequest Aggregate。
2. 先实现提交固定Python脚本的最小实验，不接LLM和RD-Agent。
3. 调度一次性Sandbox：非root、只读根文件系统、临时目录、无外网、无Docker Socket。
4. 只挂载指定DataVersion的只读Artifact；配置CPU、内存、磁盘、进程、时间和日志上限。
5. 保存状态、退出码、指标、日志Artifact、镜像Digest和随机种子。

```python
class ExperimentStatus(StrEnum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    EVALUATED = "EVALUATED"
    REJECTED = "REJECTED"
    PROMOTION_REQUESTED = "PROMOTION_REQUESTED"
```

## 测试

- 超时、OOM、Fork Bomb、网络和宿主写入被限制。
- 重复提交保持幂等。
- Sandbox崩溃不影响API和其他实验。

