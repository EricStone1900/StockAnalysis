# 03-01 隔离沙箱与实验流水线

## 目标

在独立`services/research-automation-service`中安全运行RD-Agent生成的候选因子/模型代码，并将结果保存为不可变实验Artifact。

## 实施步骤

### 1. 定义实验请求

```python
class ResearchExperimentRequest(BaseModel):
    hypothesis: str
    base_data_version: str
    allowed_datasets: list[str]
    cpu_limit: int = 2
    memory_mb: int = 4096
    timeout_seconds: int = 1800
```

请求不包含生产数据库URL、券商密钥或生产模型Provider Key。
本服务使用自己的Database/User，并且网络策略禁止连接quant-research、portfolio-risk和execution数据库端口。

### 2. 沙箱镜像

- 固定Python、Qlib和RD-Agent版本。
- 使用非root用户和只读根文件系统。
- 输入数据只读挂载。
- 输出只写临时实验目录。
- 默认禁止外网；需要模型API时通过受控代理和独立研究Key。

示意：

```yaml
read_only: true
network_mode: none
mem_limit: 4g
cpus: 2
security_opt:
  - no-new-privileges:true
```

实际调用模型时不能使用`network_mode: none`，应改为仅允许白名单代理，并通过ADR记录。

### 3. 产物清单

```text
experiment/{experimentId}/
  hypothesis.json
  generated-code/
  tests/
  metrics.json
  backtest-manifest.json
  logs/
  artifact-manifest.json
```

### 4. 静态和运行时检查

- 禁止文件系统越界、任意网络、子进程逃逸和动态下载。
- 执行单测、未来数据扫描、数值稳定和资源限制。
- 超时或OOM标记FAILED，不自动扩大资源重试。

## 测试案例

1. 候选代码尝试读取生产环境变量时失败。
2. 尝试写输入目录时失败。
3. 超时进程被终止并记录原因。
4. 相同实验输入保存明确的代码和配置Hash。
5. 部分产物不会被登记为CANDIDATE。

## 完成条件

- RD-Agent只能通过SandboxRunner执行。
- 实验Artifact可审计且不可变。
- 沙箱失败不影响每日生产Worker。
- 服务可以单独停机、迁移和重建，不影响quant-research每日任务。
