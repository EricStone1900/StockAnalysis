# market-regime-service验收

状态：PASS（随阶段06 Ubuntu 人工验收通过，基线 `f43a7cd`）

- [ ] 四维特征和最小Snapshot通过。
- [ ] 四状态规则及版本化定义通过。
- [ ] 迟滞、最短持续和快速降级通过。
- [ ] PIT、行业分类和回放无未来泄漏。
- [ ] 数据FAIL不发布新状态且旧状态显式stale。
- [ ] ruptures/River保持研究或Shadow边界。
- [ ] Agent和Risk只能读取，不能改写Regime。

## 当前实现证据

- 已实现提交：`5f5992b`、`c5fa7e0`，并加入 Compose 部署配置。
- Mac 本机测试4项通过，Ruff、Mypy、`git diff --check`通过。
- 已覆盖四维状态分类、版本化定义、失败关闭、STALE旧快照、最短持续窗口和状态抖动抑制。
- 尚待人工验收历史回放、PIT/行业分类、容器启动、跨服务只读权限及 Ubuntu 恢复演练。

人工项目完成前不得标记阶段PASS。
