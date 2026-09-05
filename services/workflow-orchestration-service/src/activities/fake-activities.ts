import { type ActivityRequest, type ActivityResponse, validateActivityRequest } from './activity-contract.js';
import type { DailyQuantActivityResult, DailyQuantActivities, DailyQuantRequest } from '../workflows/daily-quant.contract.js';
import type { NewsActivityResult, NewsAnalysisActivities, NewsWorkflowRequest } from '../workflows/news-analysis.contract.js';
import type { MarketMonitorActivities, MarketMonitorRequest, MarketMonitorStepResult } from '../workflows/market-monitor.contract.js';
import type { MarketRegimeActivities, MarketRegimeRequest, MarketRegimeStepResult } from '../workflows/market-regime.contract.js';
import type { InvestmentDecisionActivities, InvestmentDecisionRequest, InvestmentDecisionStepResult } from '../workflows/investment-decision.contract.js';

export interface HealthCheckPayload { dependency: string; }
export interface HealthCheckResult { status: 'UP'; dependency: string; }

export class FakeWorkflowActivities {
  private readonly completed = new Map<string, ActivityResponse<HealthCheckResult>>();

  public async verifyDependency(request: ActivityRequest<HealthCheckPayload>): Promise<ActivityResponse<HealthCheckResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const response: ActivityResponse<HealthCheckResult> = {
      correlationId: request.correlationId,
      result: { status: 'UP', dependency: request.payload.dependency },
      artifactRefs: [],
    };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}

export class FakeDailyQuantActivities implements DailyQuantActivities {
  private readonly completed = new Map<string, ActivityResponse<DailyQuantActivityResult>>();

  public async waitForDataVersion(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, undefined); }
  public async runDailyAnalysis(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, { uri: `artifact://daily-analysis/${request.payload.dataVersionId}`, sha256: 'a'.repeat(64) }); }
  public async runActiveStrategy(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, { uri: `artifact://daily-strategy/${request.payload.dataVersionId}`, sha256: 'b'.repeat(64) }); }
  public async publishSnapshots(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, { uri: `artifact://published/${request.payload.dataVersionId}`, sha256: 'c'.repeat(64) }); }

  private async complete(request: DailyQuantRequest, artifactRef: DailyQuantActivityResult['artifactRef']): Promise<ActivityResponse<DailyQuantActivityResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const response = { correlationId: request.correlationId, result: { dataVersionId: request.payload.dataVersionId, artifactRef }, artifactRefs: artifactRef ? [artifactRef] : [] };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}

export class FakeNewsAnalysisActivities implements NewsAnalysisActivities {
  private readonly completed = new Map<string, ActivityResponse<NewsActivityResult>>();

  public async collectNews(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>> { return await this.complete(request, 'news-source'); }
  public async buildCandidate(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>> { return await this.complete(request, 'news-candidate'); }
  public async analyzeNewsAgent(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>> { return await this.complete(request, 'financial-news-assessment'); }
  public async publishFinancialNewsEvent(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>> { return await this.complete(request, 'financial-news-event'); }

  private async complete(request: NewsWorkflowRequest, artifactName: string): Promise<ActivityResponse<NewsActivityResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const artifactRef = { uri: `artifact://${artifactName}/${request.payload.sourceWindow}`, sha256: `${request.idempotencyKey.replaceAll(/[^a-z0-9]/gi, '').padEnd(64, '0').slice(0, 64)}` };
    const response = { correlationId: request.correlationId, result: { artifactRef }, artifactRefs: [artifactRef] };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}

export class FakeMarketMonitorActivities implements MarketMonitorActivities {
  private readonly completed = new Map<string, ActivityResponse<MarketMonitorStepResult>>();
  public async checkMarketOpen(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>> { return await this.complete(request, 'market-open-check', true); }
  public async loadAnomalySnapshot(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>> { return await this.complete(request, 'anomaly-snapshot', request.payload.windowStart.includes('low') ? 'LOW' : 'HIGH'); }
  public async assessAnomaly(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>> { return await this.complete(request, 'anomaly-assessment', 'HIGH'); }
  public async publishMonitorAssessment(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>> { return await this.complete(request, 'monitor-assessment-event', 'HIGH'); }

  private async complete(request: MarketMonitorRequest, artifactName: string, value: true | MarketMonitorStepResult['severity']): Promise<ActivityResponse<MarketMonitorStepResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const artifactRef = { uri: `artifact://${artifactName}/${request.payload.windowStart}`, sha256: request.idempotencyKey.replaceAll(/[^a-z0-9]/gi, '').padEnd(64, '0').slice(0, 64) };
    const result: MarketMonitorStepResult = { artifactRef, ...(typeof value === 'boolean' ? { marketOpen: value } : { severity: value }) };
    const response = { correlationId: request.correlationId, result, artifactRefs: [artifactRef] };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}

export class FakeMarketRegimeActivities implements MarketRegimeActivities {
  private readonly completed = new Map<string, ActivityResponse<MarketRegimeStepResult>>();
  public async generateRegimeSnapshot(request: MarketRegimeRequest): Promise<ActivityResponse<MarketRegimeStepResult>> { return await this.complete(request, 'regime-snapshot', request.payload.universeVersion.includes('changed')); }
  public async analyzeMarketState(request: MarketRegimeRequest): Promise<ActivityResponse<MarketRegimeStepResult>> { return await this.complete(request, 'market-state-assessment', false); }
  public async publishRegimeAssessment(request: MarketRegimeRequest): Promise<ActivityResponse<MarketRegimeStepResult>> { return await this.complete(request, 'regime-assessment-event', false); }

  private async complete(request: MarketRegimeRequest, artifactName: string, changeDetected: boolean): Promise<ActivityResponse<MarketRegimeStepResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const artifactRef = { uri: `artifact://${artifactName}/${request.payload.asOf}`, sha256: request.idempotencyKey.replaceAll(/[^a-z0-9]/gi, '').padEnd(64, '0').slice(0, 64) };
    const response = { correlationId: request.correlationId, result: { artifactRef, changeDetected }, artifactRefs: [artifactRef] };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}

export class FakeInvestmentDecisionActivities implements InvestmentDecisionActivities {
  private readonly completed = new Map<string, ActivityResponse<InvestmentDecisionStepResult>>();
  public async validateDecisionGate(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>> { return await this.complete(request, 'decision-gate', { allowed: request.payload.scenario !== 'BLOCKED' }); }
  public async collectSpecialistEvidence(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>> { return await this.complete(request, 'specialist-evidence', {}); }
  public async runMainDecision(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>> { return await this.complete(request, 'main-proposal', { proposalAction: request.payload.scenario === 'HOLD' ? 'HOLD' : 'REBALANCE' }); }
  public async runRiskReview(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>> { return await this.complete(request, 'risk-review', { verdict: request.payload.scenario === 'RISK_REJECT' ? 'REJECT' : 'PASS' }); }
  public async runHardRiskEvaluation(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>> { return await this.complete(request, 'hard-risk', { hardRiskPassed: request.payload.scenario !== 'HARD_REJECT' }); }

  private async complete(request: InvestmentDecisionRequest, artifactName: string, fields: Omit<InvestmentDecisionStepResult, 'artifactRef'>): Promise<ActivityResponse<InvestmentDecisionStepResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const artifactRef = { uri: `artifact://${artifactName}/${request.payload.decisionAsOf}`, sha256: request.idempotencyKey.replaceAll(/[^a-z0-9]/gi, '').padEnd(64, '0').slice(0, 64) };
    const response = { correlationId: request.correlationId, result: { artifactRef, ...fields }, artifactRefs: [artifactRef] };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}
