# 阶段07验收

历史状态：PASS（用户已完成所列基线的 Ubuntu 人工验收；不覆盖当前整改提交）

验收基线：`008d6bf`

- [x] platform-api和Web分别可独立构建部署。
- [x] BFF只使用生成Client且不保存领域事实。
- [x] 核心领域页面和新鲜度展示通过。
- [x] RBAC和写代理审计通过。
- [x] 部分失败不会导致整个Dashboard不可用。
- [x] SSE断线和重复事件通过。
- [x] 前端错误边界、安全和无障碍基线通过。
- [x] 阶段10以前交易操作保持关闭。

## 当前实现证据

- 当前提交：`0b294ba`、`accefc6`、`c58ed99`、`cf2fd89`、`65a222e`。
- Platform API 单元与集成测试共8项通过；contracts 生成检查和契约测试通过。
- Web 测试6项通过，ESLint、TypeScript和生产构建通过。
- 已覆盖 Dashboard 部分失败、RBAC、请求审计、Problem Details、版本兼容、Mock/BFF切换和错误边界。
- 当前整改提交仍需重新验证：真实 Compose 启动、BFF 到 market-data 的真实调用、反向代理安全 Headers、SSE、真实认证和无障碍检查。

Ubuntu 人工验收已完成，阶段07可进入后续阶段开发。

## 当前整改提交的验收范围

[整改记录](../../architecture/architecture-remediation-2026-09-05.md)为本次变更证据入口。历史人工PASS仅对应历史基线；本次未签署本阶段REAL_E2E/RELEASE。M1允许前置只读页面；Web到BFF到真实数据服务验证代理、新鲜度和降级；开发身份头不构成生产认证。

- [ ] 补齐当前提交、镜像、迁移、契约版本与报告路径。
- [ ] 完成本阶段新增真实场景；授权、资金、幂等和恢复任一失败判FAIL。
- [ ] 记录风险、回滚目标和签署人，不以新增文档替代运行验证。
