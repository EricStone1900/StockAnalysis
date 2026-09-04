# market-regime-service测试计划

- Trend/Breadth/Volatility/Liquidity公式和窗口。
- 行业分类、指数成分、PIT和DataVersion。
- 四状态规则、迟滞、持续窗口和快速降级。
- 数据缺失、质量FAIL、stale和恢复。
- 日频、盘中窗口、重复事件和原子快照。
- 历史回放、变化点研究和River Shadow。
- API/Event Contract和Agent只读权限契约。

Fixture覆盖牛市、震荡、缓跌、急跌、流动性紧张和数据缺口。

## 本机验证记录（Mac）

- `uv run ruff check .`、`uv run mypy src`、`git diff --check`：通过。
- `uv run pytest -o addopts=''`：4 passed。
- 覆盖四维特征分类、版本化快照、质量FAIL拒绝、最短持续窗口和STALE降级。
- Compose配置校验通过；真实容器启动、历史回放和 Ubuntu 验收需另行执行。
