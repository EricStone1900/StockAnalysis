# 08-04 同镜像多部署与生产强化

## 实施步骤

1. 同一镜像通过AGENT_ID、ModelProfile、Prompt、Tool白名单、Task Queue和Durable Consumer配置独立部署。
2. 六个逻辑部署使用独立Service Account和最小网络权限；风险复核与主决策配置可用不同模型。
3. 建立Agent预算、并发、排队、取消、DLQ和降级策略。
4. Trace关联AgentRun、ModelRun、ToolCall和领域证据；日志不保存隐藏思维链或Secret。
5. 建立Prompt/Agent/模型版本发布和回滚Runbook。

## 测试

- 两个AGENT_ID相互不能使用未授权Tool。
- 单一Agent部署崩溃不影响其他部署。
- NATS重复任务保持AgentRun幂等。
- 模型全部失败返回BLOCKED，不返回默认PASS。

## 完成条件

Fake Agent可以按六种隔离配置部署，但尚无业务推理内容。

