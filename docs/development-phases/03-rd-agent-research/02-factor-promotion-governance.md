# 03-02 因子准入、批准、回滚和审计

## 目标

由research-automation-service把实验结果转换为PromotionRequest；由quant-research-service独立复验、登记CANDIDATE，并通过明确门禁和人工批准进入生产。

## 实施步骤

### 1. 准入报告

```python
class PromotionReport(BaseModel):
    candidate_id: str
    pit_check: CheckResult
    coverage_check: CheckResult
    stability_check: CheckResult
    out_of_sample_check: CheckResult
    correlation_check: CheckResult
    turnover_check: CheckResult
    cost_adjusted_backtest: CheckResult
    overall: Literal["PASS", "FAIL", "REQUIRES_REVIEW"]
```

所有门禁阈值来自版本化配置，不能由RD-Agent自行给出及批准。

### 2. 跨服务命令边界

```text
research-automation: createPromotionRequest
quant-research: registerCandidate
quant-research: validateCandidate
quant-research: approveCandidate
quant-research: activateFactorSet
quant-research: deprecateFactor
quant-research: rollbackFactorSet
```

每个命令写operatorId、reason、previousVersion和newVersion。research-automation身份只允许创建PromotionRequest，不能调用其余生产命令。

### 3. 生产加载

```python
def load_active_factor_set(as_of: datetime) -> FactorSet:
    factor_set = registry.find_published(as_of)
    if factor_set.status != "ACTIVE":
        raise ProductionConfigurationError()
    return factor_set
```

生产任务不能通过candidateId直接加载因子。

### 4. 回滚

回滚是发布一个指向上一已批准组合的新FactorSetVersion，不修改历史ACTIVE记录。

## 测试案例

1. 任一必选门禁FAIL时不能批准。
2. RD-Agent身份不能调用approve命令。
3. 未批准因子即使文件存在也不能被生产加载。
4. 回滚后新任务使用旧因子组合的新发布版本。
5. 历史快照仍引用当时的FactorSetVersion。

## 完成条件

- 候选、批准和ACTIVE状态不可跳跃。
- 有可操作的人工批准API或管理命令。
- 所有状态变化有完整审计。
