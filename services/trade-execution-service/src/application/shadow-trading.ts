import { createHash } from 'node:crypto';

export type ShadowScenario = 'DAILY_FIXED_WINDOW' | 'DAILY_WITH_DELAY' | 'DAILY_WITH_RISK_REDUCTION' | 'DAILY_MAX_TWO_BATCHES' | 'NO_REBALANCE';
export interface ShadowLeg { legId: string; securityId: string; side: 'BUY' | 'SELL'; quantity: string; }
export interface ShadowMarket { availableAt: string; referencePrice: string; tradable: boolean; maxFillQuantity: string; }
export interface ShadowDecision { decisionId: string; proposalVersion: number; scenario: ShadowScenario; decisionAsOf: string; policyVersion: string; legs: readonly ShadowLeg[]; market: Readonly<Record<string, ShadowMarket>>; }
export interface ShadowLegResult { legId: string; securityId: string; executable: boolean; theoreticalQuantity: string; theoreticalPrice?: string; estimatedCost?: string; reason?: string; }
export interface ShadowReport { reportId: string; decisionId: string; proposalVersion: number; scenario: ShadowScenario; episodeType: 'SHADOW'; legResults: readonly ShadowLegResult[]; differences: readonly string[]; contentHash: string; }

export class ShadowTradingLedger {
  private readonly reports = new Map<string, ShadowReport>();

  public record(decision: ShadowDecision): ShadowReport {
    const existing = this.reports.get(`${decision.decisionId}:${decision.proposalVersion}:${decision.scenario}`);
    if (existing) return existing;
    const legResults = decision.legs.map((leg) => evaluateLeg(leg, decision.market[leg.securityId], decision.decisionAsOf));
    const reportBase = { reportId: `shadow:${decision.decisionId}:${decision.proposalVersion}:${decision.scenario}`, decisionId: decision.decisionId, proposalVersion: decision.proposalVersion, scenario: decision.scenario, episodeType: 'SHADOW' as const, legResults, differences: legResults.filter((result) => !result.executable).map((result) => `${result.legId}:${result.reason}`) };
    const contentHash = createHash('sha256').update(JSON.stringify(reportBase)).digest('hex');
    const report = { ...reportBase, contentHash };
    this.reports.set(`${decision.decisionId}:${decision.proposalVersion}:${decision.scenario}`, report);
    return report;
  }

  public get(reportId: string): ShadowReport | undefined { return [...this.reports.values()].find((report) => report.reportId === reportId); }
}

function evaluateLeg(leg: ShadowLeg, market: ShadowMarket | undefined, decisionAsOf: string): ShadowLegResult {
  if (!market) return { legId: leg.legId, securityId: leg.securityId, executable: false, theoreticalQuantity: '0', reason: 'MARKET_DATA_MISSING' };
  if (market.availableAt > decisionAsOf) return { legId: leg.legId, securityId: leg.securityId, executable: false, theoreticalQuantity: '0', reason: 'FUTURE_MARKET_DATA' };
  if (!market.tradable) return { legId: leg.legId, securityId: leg.securityId, executable: false, theoreticalQuantity: '0', reason: 'NOT_TRADABLE' };
  const quantity = Math.min(Number(leg.quantity), Number(market.maxFillQuantity));
  const price = Number(market.referencePrice);
  if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(price) || price <= 0) return { legId: leg.legId, securityId: leg.securityId, executable: false, theoreticalQuantity: '0', reason: 'INVALID_MARKET_OR_QUANTITY' };
  return { legId: leg.legId, securityId: leg.securityId, executable: true, theoreticalQuantity: quantity.toFixed(8), theoreticalPrice: price.toFixed(8), estimatedCost: (quantity * price * 0.0003).toFixed(8) };
}
