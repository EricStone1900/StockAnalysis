# 04-01 Platform API服务和API基础

## 目标

建立独立`platform-api-service`的NestJS BFF、认证、配置入口、审计、内部Client和统一API规范。

## 实施步骤

### 1. 模块结构

```ts
@Module({
  imports: [
    AuthModule,
    ConfigurationModule,
    PortfolioQueryModule,
    DecisionQueryModule,
    WorkflowControlModule,
    AuditModule,
  ],
})
export class PlatformApiModule {}
```

Query模块只通过生成的OpenAPI Client读取领域服务，不导入portfolio、decision或execution的Repository/Entity。

### 2. Fastify和全局校验

```ts
const app = await NestFactory.create<NestFastifyApplication>(
  PlatformApiModule,
  new FastifyAdapter(),
);
app.useGlobalPipes(new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true }));
```

Controller显式使用`api/v1/...`或`internal/v1/...`前缀，避免全局前缀把内部API错误嵌套到外部API下面；也不要通过字符串替换实现两类路由。

### 3. 认证与RBAC

初期角色：`ADMIN`、`ANALYST`、`APPROVER`、`VIEWER`。审批和风险策略发布必须单独权限。

### 4. 审计拦截器

所有写请求记录actorId、requestId、correlationId、commandType、targetId和结果。敏感字段进入审计前脱敏。

### 5. 内部Client

由OpenAPI生成research/news等Client，再用Adapter补超时、重试和Tracing。Controller不得直接使用裸HTTP客户端。

## 测试案例

1. 未认证不能访问持仓和配置。
2. VIEWER不能执行写操作。
3. 额外请求字段被拒绝。
4. 写操作成功和失败都产生审计事件。
5. 内部依赖超时返回统一Dependency Error。

## 完成条件

- 模块依赖方向清楚，无跨模块Repository访问。
- platform-api数据库只保存身份、UI配置和入口审计，不包含持仓、建议或订单事实表。
- OpenAPI可生成前端Client。
- 权限和审计测试通过。
