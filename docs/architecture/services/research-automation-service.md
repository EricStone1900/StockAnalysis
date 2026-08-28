# research-automation-service

## 1. 定位

独立的自动研究限界上下文，封装RD-Agent及其代码生成、实验调度和Sandbox执行能力。它服务于因子与模型研发，但不属于每日生产评分链路，也不拥有生产Factor/Model Registry。

独立拆分的原因：生成代码具有更高安全风险、资源需求和依赖变更频率；与Qlib生产服务隔离后，可单独限制网络、CPU、内存、密钥和文件权限。

## 2. 职责与边界

负责：

- 接收研究假设、数据版本和基准配置。
- 调用RD-Agent生成候选因子、模型或实验计划。
- 在无生产密钥的Sandbox中运行候选代码。
- 保存Experiment、Artifact、日志、指标和可复现环境清单。
- 生成Promotion Request，交给`quant-research-service`复验和人工批准。

不负责：

- 修改ACTIVE因子或生产模型。
- 写入DailyAnalysisSnapshot。
- 读取券商密钥、账户、订单或真实成交。
- 自动批准候选；Agent或RD-Agent给出的阈值不能覆盖治理配置。

## 3. DDD模型

- `ResearchExperiment` Aggregate：假设、配置、状态、预算、数据版本。
- `CandidateArtifact`：不可变代码、依赖锁、镜像摘要和内容Hash。
- `ExperimentRun`：Sandbox执行、指标、日志和失败原因。
- `PromotionRequest` Aggregate：候选、证据、门禁结果和人工审批引用。

状态机：

```text
DRAFT -> QUEUED -> RUNNING -> EVALUATED -> REJECTED
                                     \-> PROMOTION_REQUESTED
```

`PROMOTION_REQUESTED`仍不是生产生效。只有`quant-research-service`在独立复验、偏差检查和人工批准后才能创建新Registry版本。

## 4. 接口与事件

同步接口：

- `POST /internal/v1/experiments`：创建实验，支持`Idempotency-Key`。
- `GET /internal/v1/experiments/{experimentId}`：查询状态与Artifact引用。
- `POST /internal/v1/promotion-requests`：提交候选，不表示批准。
- `GET /internal/v1/artifacts/{artifactId}/manifest`：获取可复现清单。

订阅：

- `stock.market-data.data-version.published.v1`。
- 可选的人工研究命令由Temporal Activity调用，不用领域事件表达命令。

发布：

- `stock.research.experiment.completed.v1`。
- `stock.research.promotion-request.created.v1`。

事件只包含ID、Hash、指标摘要和Artifact URI，不嵌入生成代码或大型日志。

## 5. 服务内部结构

```text
services/research-automation-service/
  src/research_automation/
    domain/
    application/
    ports/
    adapters/http/
    adapters/events/
    adapters/rd_agent/
    adapters/sandbox/
    adapters/persistence/
    bootstrap/
  migrations/
  tests/unit/
  tests/integration/
  tests/security/
  Dockerfile
  pyproject.toml
```

RD-Agent、Docker/Kubernetes Job、Seccomp或其他Sandbox实现只能出现在Adapter层，Domain层不得依赖这些框架。

## 6. Docker与安全要求

- API/调度容器与Sandbox执行容器使用不同镜像和Service Account。
- Sandbox默认无外网、只读根文件系统、临时工作目录、非root、资源/时间上限。
- 只挂载指定`dataVersion`的只读数据；不能挂载Docker Socket、生产数据库或宿主机目录。
- 依赖安装使用允许列表和缓存仓库；保存SBOM、镜像摘要、Python锁文件和随机种子。
- 每个实验有成本预算、Token预算、并发限制和Kill Switch。

## 7. 与quant-research-service的关系

`research-automation-service`提出候选，`quant-research-service`拥有生产Registry与准入规则。推荐流程：

```text
RD-Agent候选 -> Sandbox初评 -> PromotionRequest
  -> quant-research独立复算/时序切分/泄漏检查
  -> 人工审批 -> 新FactorSetVersion
  -> 下一次生产任务显式选择该版本
```

两个服务可以读取同一个不可变Parquet/MinIO Artifact，但必须使用各自数据库，不共享ORM表。

## 8. 验收条件

- RD-Agent身份不能调用生产Registry激活接口。
- Sandbox不能访问生产密钥、账户和Broker网络。
- 同一Artifact、dataVersion、镜像摘要和随机种子可复现实验。
- 恶意文件写入、网络访问、超时和资源耗尽测试均被阻断并审计。
- 未批准候选不能影响任何DailyAnalysisSnapshot。
