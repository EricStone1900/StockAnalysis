# 00-01 Monorepo与空应用骨架

## 目标

创建与整体设计一致的目录、Workspace和最小可启动应用，不实现领域逻辑。

## 前置条件

- Node.js LTS、pnpm、Python 3.11+、Docker和Git可用。
- 当前位于仓库根目录。

## 实施步骤

### 1. 创建目录

```bash
mkdir -p apps/web
mkdir -p services/{platform-api-service,workflow-orchestration-service,agent-service,market-data-service,quant-research-service,research-automation-service,news-intelligence-service,market-monitor-service,market-regime-service,portfolio-risk-service,decision-governance-service,trade-execution-service}
mkdir -p packages/{contracts,agent-kernel,model-gateway,agent-tools,evidence-sdk,temporal-common,nats-common,observability,config,test-kit}
mkdir -p python/packages contracts/{openapi,asyncapi,schemas,examples,compatibility}
mkdir -p infra/{docker,compose,nats,temporal,observability,storage,deployment}
mkdir -p tests/{contract,integration,e2e,replay,golden,failure,fixtures} scripts
```

执行前先确认目标是当前仓库，不要在`~`或其他上级目录运行。

### 2. 建立pnpm Workspace

`pnpm-workspace.yaml`：

```yaml
packages:
  - apps/*
  - packages/*
  - services/*
```

根`package.json`建议：

```json
{
  "name": "stock-analysis-platform",
  "private": true,
  "packageManager": "pnpm@10",
  "scripts": {
    "build": "pnpm -r build",
    "test": "pnpm -r test",
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r typecheck",
    "contracts:generate": "pnpm --filter @stock/contracts generate"
  }
}
```

不要在根包加入具体Web框架依赖；依赖应归属实际应用或公共包。

### 3. 创建Node应用

- `apps/web`：React + Vite + TypeScript。
- `services/platform-api-service`、`portfolio-risk-service`、`decision-governance-service`和`trade-execution-service`：独立NestJS + Fastify项目。
- `services/workflow-orchestration-service`：Temporal TypeScript Worker。
- `services/agent-service`：通用Agent Kernel入口，同一镜像以六组配置独立部署。

每个包至少提供`build/test/lint/typecheck`脚本和独立`tsconfig.json`。

示例空健康接口：

```ts
@Controller('health')
export class HealthController {
  @Get('live')
  live() {
    return { status: 'ok' as const };
  }
}
```

### 4. 创建Python服务骨架

每个服务使用`src`布局：

```toml
[project]
name = "market-data-service"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["fastapi", "uvicorn"]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

最小入口：

```python
from fastapi import FastAPI

app = FastAPI(title="market-data-service")

@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}
```

### 5. 根README

写清楚环境要求、启动顺序、常用命令和文档入口。此时不得声称业务功能已经完成。

## 测试

```bash
pnpm install
pnpm build
pnpm test
python -m pytest services
```

## 测试案例

1. 空仓库安装依赖成功。
2. 每个Node服务可以独立构建镜像并通过健康检查。
3. 每个Python服务可以独立导入FastAPI应用和构建镜像。
4. 访问每个服务`/health/live`返回200。

## 完成条件

- 目录与整体设计一致。
- 每个服务有独立Dockerfile、迁移目录、测试目录、契约入口和数据库配置变量。
- 根命令不会隐式下载或运行业务数据任务。
- 所有空应用构建和测试通过。
- README可让另一位开发者在新环境复现。
