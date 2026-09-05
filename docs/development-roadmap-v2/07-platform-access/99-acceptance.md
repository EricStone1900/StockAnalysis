# 阶段07验收

- [ ] platform-api和Web分别可独立构建部署。
- [ ] BFF只使用生成Client且不保存领域事实。
- [ ] 核心领域页面和新鲜度展示通过。
- [ ] RBAC和写代理审计通过。
- [ ] 部分失败不会导致整个Dashboard不可用。
- [ ] SSE断线和重复事件通过。
- [ ] 前端错误边界、安全和无障碍基线通过。
- [ ] 阶段10以前交易操作保持关闭。

## 当前实现证据

- 当前提交：`0b294ba`、`accefc6`、`c58ed99`、`cf2fd89`、`65a222e`。
- Platform API 单元与集成测试共8项通过；contracts 生成检查和契约测试通过。
- Web 测试6项通过，ESLint、TypeScript和生产构建通过。
- 已覆盖 Dashboard 部分失败、RBAC、请求审计、Problem Details、版本兼容、Mock/BFF切换和错误边界。
- 尚待人工验收：真实 Compose 启动、BFF 到 market-data 的真实调用、反向代理安全 Headers、SSE、真实认证和无障碍检查。

在 Ubuntu 人工验收完成前，阶段07保持未验收状态。
