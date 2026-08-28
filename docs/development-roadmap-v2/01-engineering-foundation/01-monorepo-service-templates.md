# 01-01 Monorepo和服务模板

## 目录目标

```text
apps/web/
services/{service-name}/
packages/contracts/
packages/config/
packages/observability/
packages/testing/
infra/compose/
infra/otel/
scripts/
```

## 实施步骤

1. 配置pnpm workspace、Node 22+、TypeScript strict、ESLint和Vitest。
2. 建立NestJS轻量模板，包含bootstrap、配置Schema、Problem Details、健康和观测。
3. 配置Python 3.11+、uv、FastAPI、Pydantic、Ruff、mypy和pytest模板。
4. Domain包不得依赖NestJS、FastAPI、数据库或消息SDK；添加架构测试。
5. 所有服务创建独立Dockerfile、迁移目录和README运行说明。
6. 用生成器或模板验证新服务创建结果，但生成后的项目仍能独立发布。

TypeScript启动端口示例：

```ts
export interface HealthProbe {
  live(): Promise<'UP'>;
  ready(): Promise<{ status: 'UP' | 'DOWN'; dependencies: object }>;
}
```

## 测试

- TypeScript/Python模板分别创建示例服务并通过lint、typecheck、unit和Docker build。
- 删除其他服务后单个服务仍能安装依赖和启动。
- 架构测试阻止Domain导入Adapter。

