export type BrokerOrderState = 'ACCEPTED' | 'REJECTED' | 'UNKNOWN';
export interface BrokerOrderCommand { readonly clientOrderId: string; readonly accountId: string; readonly securityId: string; readonly side: 'BUY' | 'SELL'; readonly quantity: string; readonly orderType: 'MARKET' | 'LIMIT'; readonly limitPrice?: string; }
export interface BrokerOrderResult { readonly clientOrderId: string; readonly state: BrokerOrderState; readonly externalOrderId?: string; readonly reason?: string; }
export interface BrokerPort { place(command: BrokerOrderCommand): Promise<BrokerOrderResult>; query(clientOrderId: string): Promise<BrokerOrderResult>; cancel(clientOrderId: string): Promise<BrokerOrderResult>; }
export interface AutoExecutionLeg { readonly legId: string; readonly securityId: string; readonly side: 'BUY' | 'SELL'; readonly quantity: string; readonly referencePrice: string; }
export interface AutoExecutionCommand { readonly rebalanceBatchId: string; readonly accountId: string; readonly strategyVersion: string; readonly approvalId: string; readonly riskEvaluationId: string; readonly budgetReservationId: string; readonly validUntil: string; readonly executionAsOf: string; readonly approvalComplete: boolean; readonly riskApproved: boolean; readonly budgetReserved: boolean; readonly priceWithinTolerance: boolean; readonly legs: readonly AutoExecutionLeg[]; }
export interface AutoExecutionPolicy { readonly enabled: boolean; readonly allowedAccountIds: readonly string[]; readonly allowedSecurityIds: readonly string[]; readonly allowedStrategyVersions: readonly string[]; readonly maxBatchNotional: number; readonly maxOrderNotional: number; readonly sessionStartUtc: string; readonly sessionEndUtc: string; readonly killSwitchOpen: boolean; }
export interface AutoExecutionResult { readonly rebalanceBatchId: string; readonly state: BrokerOrderState; readonly orders: readonly BrokerOrderResult[]; readonly reason?: string; }

export class ControlledAutoExecutor {
  private readonly completed = new Map<string, AutoExecutionResult>();
  public constructor(private readonly broker: BrokerPort, private readonly policy: AutoExecutionPolicy) {}

  public async submit(command: AutoExecutionCommand): Promise<AutoExecutionResult> {
    const existing = this.completed.get(command.rebalanceBatchId);
    if (existing) return existing;
    const rejection = validate(command, this.policy);
    if (rejection) return this.save({ rebalanceBatchId: command.rebalanceBatchId, state: 'REJECTED', orders: [], reason: rejection });
    const orders: BrokerOrderResult[] = [];
    for (const leg of command.legs) {
      const result = await this.broker.place({ clientOrderId: `${command.rebalanceBatchId}:${leg.legId}`, accountId: command.accountId, securityId: leg.securityId, side: leg.side, quantity: leg.quantity, orderType: 'MARKET' });
      orders.push(result);
      if (result.state === 'UNKNOWN') return this.save({ rebalanceBatchId: command.rebalanceBatchId, state: 'UNKNOWN', orders, reason: 'BROKER_RESPONSE_UNKNOWN_NO_RETRY' });
      if (result.state === 'REJECTED') return this.save({ rebalanceBatchId: command.rebalanceBatchId, state: 'REJECTED', orders, reason: result.reason ?? 'BROKER_REJECTED' });
    }
    return this.save({ rebalanceBatchId: command.rebalanceBatchId, state: 'ACCEPTED', orders });
  }

  private save(result: AutoExecutionResult): AutoExecutionResult { this.completed.set(result.rebalanceBatchId, result); return result; }
}

function validate(command: AutoExecutionCommand, policy: AutoExecutionPolicy): string | undefined {
  if (!policy.enabled) return 'AUTO_EXECUTION_DISABLED';
  if (!policy.killSwitchOpen) return 'KILL_SWITCH_CLOSED';
  if (!policy.allowedAccountIds.includes(command.accountId)) return 'ACCOUNT_NOT_WHITELISTED';
  if (!policy.allowedStrategyVersions.includes(command.strategyVersion)) return 'STRATEGY_VERSION_NOT_WHITELISTED';
  if (!command.approvalId || !command.riskEvaluationId || !command.budgetReservationId || !command.approvalComplete || !command.riskApproved || !command.budgetReserved) return 'PREFLIGHT_APPROVAL_INCOMPLETE';
  if (Date.parse(command.validUntil) <= Date.parse(command.executionAsOf)) return 'EXECUTION_APPROVAL_EXPIRED';
  const time = command.executionAsOf.slice(11, 16);
  if (time < policy.sessionStartUtc || time > policy.sessionEndUtc) return 'OUTSIDE_TRADING_SESSION';
  if (!command.priceWithinTolerance || command.legs.length === 0) return 'PRICE_OR_LEG_VALIDATION_FAILED';
  let total = 0;
  for (const leg of command.legs) {
    if (!policy.allowedSecurityIds.includes(leg.securityId)) return 'SECURITY_NOT_WHITELISTED';
    const notional = Number(leg.quantity) * Number(leg.referencePrice);
    if (!Number.isFinite(notional) || notional <= 0 || notional > policy.maxOrderNotional) return 'ORDER_NOTIONAL_LIMIT_EXCEEDED';
    total += notional;
  }
  if (total > policy.maxBatchNotional) return 'BATCH_NOTIONAL_LIMIT_EXCEEDED';
  return undefined;
}
