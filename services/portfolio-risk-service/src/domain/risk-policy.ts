import type { PortfolioSnapshot } from './portfolio.js';

export interface RiskPolicy {
  readonly policyVersion: string;
  readonly maxPositionWeight: string;
  readonly maxTotalPositionWeight: string;
  readonly minCash: string;
  readonly maxTurnover: string;
  readonly maxDailyRebalanceBatches: number;
  readonly allowedSecondBatchReasons: readonly string[];
  readonly maxDrawdown: string;
  readonly paused: boolean;
}

export interface TradeProposalLeg {
  readonly securityId: string;
  readonly side: 'BUY' | 'SELL' | 'HOLD';
  readonly quantity: string;
  readonly price: string;
}

export interface RiskEvaluationInput {
  readonly proposalId: string;
  readonly reason: string;
  readonly legs: readonly TradeProposalLeg[];
  readonly portfolio: PortfolioSnapshot;
  readonly prices: Readonly<Record<string, string>>;
  readonly decisionBudget: { readonly rebalanceBatchesToday: number };
  readonly peakEquity: string;
  readonly policy: RiskPolicy;
  readonly correlationId?: string;
}

export interface RiskRuleResult {
  readonly ruleId: string;
  readonly policyVersion: string;
  readonly verdict: 'PASS' | 'REJECT';
  readonly actual: string;
  readonly limit: string;
  readonly reasonCode: string;
}

export interface RiskEvaluation {
  readonly evaluationId: string;
  readonly proposalId: string;
  readonly policyVersion: string;
  readonly verdict: 'PASS' | 'REJECT';
  readonly rules: readonly RiskRuleResult[];
  readonly before: { readonly cash: string; readonly totalEquity: string };
  readonly projectedAfter: { readonly cash: string; readonly totalEquity: string };
  readonly correlationId?: string;
}

const SCALE = 100_000_000n;
const toScaled = (value: string): bigint => {
  if (!/^-?\d+(?:\.\d{1,8})?$/.test(value)) throw new Error(`invalid decimal: ${value}`);
  const negative = value.startsWith('-');
  const unsigned = negative ? value.slice(1) : value;
  const [whole, fraction = ''] = unsigned.split('.');
  const result = BigInt(whole) * SCALE + BigInt((fraction + '00000000').slice(0, 8));
  return negative ? -result : result;
};
const fromScaled = (value: bigint): string => {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  const fraction = (absolute % SCALE).toString().padStart(8, '0').replace(/0+$/, '');
  return `${negative ? '-' : ''}${absolute / SCALE}${fraction ? `.${fraction}` : ''}`;
};
const add = (left: string, right: string): string => fromScaled(toScaled(left) + toScaled(right));
const subtract = (left: string, right: string): string => fromScaled(toScaled(left) - toScaled(right));
const multiply = (left: string, right: string): string => fromScaled((toScaled(left) * toScaled(right)) / SCALE);
const isNegative = (value: string): boolean => toScaled(value) < 0n;

function rule(policy: RiskPolicy, ruleId: string, actual: string, limit: string, pass: boolean, reasonCode: string): RiskRuleResult {
  return { ruleId, policyVersion: policy.policyVersion, verdict: pass ? 'PASS' : 'REJECT', actual, limit, reasonCode };
}

export function evaluateRisk(input: RiskEvaluationInput): RiskEvaluation {
  const { portfolio, policy } = input;
  if (!policy.policyVersion || input.legs.length === 0) throw new Error('invalid risk evaluation input');
  if (!Number.isInteger(input.decisionBudget.rebalanceBatchesToday) || input.decisionBudget.rebalanceBatchesToday < 0) throw new Error('invalid decision budget');
  const currentPositions = new Map(portfolio.positions.map((position) => [position.securityId, position.quantity]));
  const currentValues = new Map<string, string>();
  for (const position of portfolio.positions) {
    const price = input.prices[position.securityId];
    if (!price) throw new Error(`missing price for ${position.securityId}`);
    currentValues.set(position.securityId, multiply(position.quantity, price));
  }
  const currentMarketValue = [...currentValues.values()].reduce(add, '0');
  const beforeEquity = add(portfolio.cash, currentMarketValue);
  const projectedCash = { value: portfolio.cash };
  const projectedPositions = new Map(currentPositions);
  let turnover = '0';
  for (const leg of input.legs) {
    if (leg.side === 'HOLD') continue;
    const notional = multiply(leg.quantity, leg.price);
    turnover = add(turnover, notional);
    projectedCash.value = leg.side === 'BUY' ? subtract(projectedCash.value, notional) : add(projectedCash.value, notional);
    const existing = projectedPositions.get(leg.securityId) ?? '0';
    const next = leg.side === 'BUY' ? add(existing, leg.quantity) : subtract(existing, leg.quantity);
    if (isNegative(next)) throw new Error(`sell quantity exceeds position for ${leg.securityId}`);
    projectedPositions.set(leg.securityId, next);
  }
  const projectedMarketValue = [...projectedPositions].reduce((total, [securityId, quantity]) => add(total, multiply(quantity, input.prices[securityId] ?? '0')), '0');
  const projectedEquity = add(projectedCash.value, projectedMarketValue);
  const rules = [
    rule(policy, 'global-pause', policy.paused ? 'PAUSED' : 'ACTIVE', 'ACTIVE', !policy.paused, 'GLOBAL_PAUSE'),
    rule(policy, 'daily-rebalance-batches', String(input.decisionBudget.rebalanceBatchesToday), String(policy.maxDailyRebalanceBatches), input.decisionBudget.rebalanceBatchesToday < policy.maxDailyRebalanceBatches || (input.decisionBudget.rebalanceBatchesToday === 1 && policy.allowedSecondBatchReasons.includes(input.reason)), 'DAILY_BATCH_LIMIT'),
    rule(policy, 'minimum-cash', projectedCash.value, policy.minCash, toScaled(projectedCash.value) >= toScaled(policy.minCash), 'MIN_CASH'),
    rule(policy, 'turnover', turnover, policy.maxTurnover, toScaled(turnover) <= toScaled(policy.maxTurnover), 'MAX_TURNOVER'),
    rule(policy, 'drawdown', fromScaled(toScaled(input.peakEquity) - toScaled(projectedEquity)), policy.maxDrawdown, toScaled(input.peakEquity) - toScaled(projectedEquity) <= toScaled(policy.maxDrawdown), 'MAX_DRAWDOWN'),
  ];
  const equityForWeight = toScaled(projectedEquity);
  for (const [securityId, quantity] of projectedPositions) {
    const value = toScaled(multiply(quantity, input.prices[securityId] ?? '0'));
    rules.push(rule(policy, `position:${securityId}`, fromScaled(value), policy.maxPositionWeight, value <= (equityForWeight * toScaled(policy.maxPositionWeight)) / SCALE, 'MAX_POSITION_WEIGHT'));
  }
  rules.push(rule(policy, 'total-position-weight', projectedMarketValue, policy.maxTotalPositionWeight, toScaled(projectedMarketValue) <= (equityForWeight * toScaled(policy.maxTotalPositionWeight)) / SCALE, 'MAX_TOTAL_POSITION_WEIGHT'));
  return { evaluationId: `risk-evaluation-${input.proposalId}-${policy.policyVersion}`, proposalId: input.proposalId, policyVersion: policy.policyVersion, verdict: rules.every((item) => item.verdict === 'PASS') ? 'PASS' : 'REJECT', rules, before: { cash: portfolio.cash, totalEquity: beforeEquity }, projectedAfter: { cash: projectedCash.value, totalEquity: projectedEquity }, correlationId: input.correlationId };
}
