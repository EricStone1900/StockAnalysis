# 阶段07 Ubuntu 联合验收步骤

## 1. 获取并固定版本

```sh
git clone https://github.com/EricStone1900/StockAnalysis.git
cd StockAnalysis
git checkout <待验收CommitSHA>
node --version
pnpm --version
docker compose version
```

记录 Commit SHA。不要在仓库或 Shell 历史中写入生产密码、Token 或模型密钥。

## 2. 构建前检查

```sh
pnpm install --frozen-lockfile
pnpm --filter @stock/contracts check:generated
pnpm --filter @stock/platform-api-service lint
pnpm --filter @stock/platform-api-service typecheck
pnpm --filter @stock/web lint
pnpm --filter @stock/web typecheck
pnpm --filter @stock/web build
```

生成 Client 漂移或 TypeScript 检查失败时停止验收，不得继续启动旧镜像。

## 3. 启动基础设施和服务

```sh
docker compose -f infra/compose/docker-compose.yml up -d postgres minio nats
docker compose -f infra/compose/docker-compose.yml up -d market-data-service platform-api-service
```

确认 `market-data-service` 和 `platform-api-service` 均为 `healthy`。Web 可使用静态产物由 Nginx/Caddy 托管；若使用 Vite 预览，仅用于验收，不作为生产部署。

## 4. BFF 健康和版本检查

```sh
curl --fail http://127.0.0.1:3008/live
curl --fail -H 'x-client-version: v1' http://127.0.0.1:3008/api/v1/compatibility
```

确认返回 `compatible: true`、`apiVersion: v1`。端口以 Compose 实际映射为准。

## 5. Dashboard 正常与部分失败

```sh
curl --fail -H 'x-actor-id:验收用户' -H 'x-roles:RESEARCH_READ' -H 'x-request-id:accept-001' http://127.0.0.1:3008/api/v1/dashboard
```

正常响应必须包含 DataVersion 的 `status`、`asOf` 和依赖状态。停止或隔离 market-data 后再次请求，必须返回 `UNAVAILABLE`，不能用空对象冒充正常数据；恢复后重新请求确认可恢复。

## 6. RBAC、审计和错误格式

不带 `RESEARCH_READ` 请求 Dashboard，确认返回 `FORBIDDEN` 语义；以 `ADMIN` 查询 `/api/v1/audit/events`，确认包含 actor、requestId、correlationId 和 action。使用不存在路由或非法输入，确认响应为 Problem Details 且包含 `requestId`。

## 7. Web 验证

访问 Web 页面，确认 Dashboard、加载态、错误提示、`STALE/UNAVAILABLE/FORBIDDEN` 标签和版本不兼容提示可见。设置 `VITE_USE_MOCK_API=true` 构建仅用于本地 Mock 验收；生产构建必须关闭该开关并指向 BFF。

## 8. 安全与回滚

检查 BFF 响应含 `nosniff`、`DENY`、`no-referrer` 和 `no-store` Headers；确认浏览器无法直接访问内部数据库、NATS 或模型密钥。失败时记录日志和镜像摘要，执行 `docker compose down`，回滚到上一个已验收 Commit，禁止手工修改领域数据库判定通过。
