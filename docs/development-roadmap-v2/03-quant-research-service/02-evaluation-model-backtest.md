# 03-02 因子评估、模型和回测

## 实施步骤

1. 实现IC、RankIC、分层收益、换手、相关性和稳定性报告。
2. 固化train/validation/test和Walk-forward时序切分，禁止随机打乱时间。
3. 建立ModelDefinition、ModelVersion、TrainingRun和EvaluationReport。
4. 首版使用简单线性/树模型作为基线，再接Qlib模型；复杂模型不得早于基线。
5. 回测纳入停牌、涨跌停、最小交易单位、成本、滑点和信号可成交时间。
6. 所有结果保存DataVersion、UniverseVersion、代码Hash、参数、随机种子和Artifact Hash。

## 测试

- 标签和特征时间错位会被泄漏检测拒绝。
- 无成本与成本后结果分开。
- 相同输入可复现；改变成本模型产生新评估版本。
- 过拟合、样本外失败和高换手不能晋升ACTIVE。

