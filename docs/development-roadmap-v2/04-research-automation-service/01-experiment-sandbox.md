# 04-01 实验骨架与Sandbox

## S0：冻结边界与最小契约

本切片只接受服务端预注册的`scriptId`，不接收任意Python源码、镜像名、Shell参数或依赖安装请求。创建实验必须固定
`experimentId`、`Idempotency-Key`、研究假设、`DataVersion`、数据Artifact URI/SHA-256、脚本标识、参数、随机种子和
资源预算；相同幂等键返回同一实验，输入不同立即拒绝。实验只可使用只读数据Artifact引用，禁止读取quant数据库、生产
Registry、券商账户、Docker Socket、宿主目录或Secret。

`ExperimentRun`记录Sandbox配置Hash、脚本/输入Hash、退出码、状态、指标摘要及日志Artifact引用。首版日志和指标只
保存在应用内存，用于最小纵向切片；持久化、Artifact对象存储和事件Outbox在后续步骤补齐。任何失败只能将实验置为
`REJECTED`，不得创建PromotionRequest、不得写入阶段03的快照或Registry。

Sandbox命令必须显式包含非root用户、`--network none`、只读根文件系统、`no-new-privileges`、移除Linux capabilities、
受限CPU/内存/PID、受限临时目录，以及DataVersion只读挂载。Docker/Kubernetes仅可在Adapter层出现；Domain和API
不传递Docker参数。

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

## 文件与接口

- `src/research_automation/domain.py`：实验、运行、预算与状态机。
- `src/research_automation/application.py`：幂等提交、启动与完成/拒绝流程。
- `src/research_automation/sandbox.py`：固定脚本白名单和受限Sandbox命令构造。
- `src/main.py`：只开放创建、查询和只读健康接口；不提供Promotion或生产Registry写接口。
- `tests/unit/`：覆盖状态机、幂等、输入Hash和Sandbox隔离配置。

首个内部接口为`POST /internal/v1/experiments`，请求必须带`Idempotency-Key`；
`GET /internal/v1/experiments/{experimentId}`只返回实验元数据和运行摘要。未知实验返回404，任何不允许的方法返回405。

## 测试

- 超时、OOM、Fork Bomb、网络和宿主写入被限制。
- 重复提交保持幂等。
- Sandbox崩溃不影响API和其他实验。
