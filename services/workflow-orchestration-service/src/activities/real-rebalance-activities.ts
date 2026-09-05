import { createHash } from 'node:crypto';
import type { ActivityResponse, ArtifactRef } from './activity-contract.js';
import { validateActivityRequest } from './activity-contract.js';
import type { RebalanceExecutionActivities, RebalanceExecutionRequest, RebalanceStepResult } from '../workflows/rebalance-execution.contract.js';

interface HttpResponse { status: number; json(): Promise<unknown>; text(): Promise<string>; }
interface HttpClient { fetch(input: string, init?: RequestInit): Promise<HttpResponse>; }
const nativeHttp: HttpClient = { fetch: (input, init) => fetch(input, init) };

export interface RealRebalanceActivityConfig { governanceBaseUrl: string; portfolioBaseUrl: string; executionBaseUrl: string; governanceToken: string; portfolioToken: string; executionToken: string; }

/** 真实人工调仓 Activity；所有写请求均携带服务身份和幂等键。 */
export class HttpRebalanceExecutionActivities implements RebalanceExecutionActivities {
  constructor(private readonly config: RealRebalanceActivityConfig, private readonly http: HttpClient = nativeHttp) {}
  async reserveBudget(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>> {
    const p = this.require(request); if (!p.proposalId || !p.budgetReservationId) throw new Error('real rebalance requires proposalId and budgetReservationId');
    const body = { reservationId: p.budgetReservationId, portfolioId: p.portfolioId, tradingDate: p.tradingDate, reason: p.reason, kind: 'REBALANCE', idempotencyKey: request.idempotencyKey, policy: { maxDailyRebalanceBatches: 2, allowedSecondBatchReasons: ['INTRADAY_RISK_REDUCTION', 'EXECUTION_CORRECTION'] } };
    const result = await this.post(`${this.config.governanceBaseUrl}/api/v1/proposals/${encodeURIComponent(p.proposalId)}/budget-reservations`, body, this.config.governanceToken, p.budgetReservationId);
    await this.post(`${this.config.governanceBaseUrl}/api/v1/proposals/${encodeURIComponent(p.proposalId)}/budget-reservations/${encodeURIComponent(p.budgetReservationId)}/dispatching`, {}, this.config.governanceToken, `${p.budgetReservationId}:dispatching`);
    await this.post(`${this.config.portfolioBaseUrl}/internal/v1/portfolio-reservations/${encodeURIComponent(p.resourceReservationId ?? '')}/status`, { status: 'DISPATCHING' }, this.config.portfolioToken, `${p.resourceReservationId}:dispatching`);
    return this.response(request, result, { reservationStatus: 'RESERVED' });
  }
  async createRebalanceBatch(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>> {
    const p = this.require(request); if (!p.approvalId || !p.budgetReservationId || !p.resourceReservationId || !p.riskEvaluationId || !p.executionContentHash || !p.targetPortfolioVersion || !p.validUntil || !p.legs) throw new Error('real rebalance execution command is incomplete');
    const result = await this.post(`${this.config.executionBaseUrl}/api/v1/execution/batches`, { rebalanceBatchId: `rebalance-${request.workflowId}`, decisionId: p.decisionId, proposalId: p.proposalId, portfolioId: p.portfolioId, proposalVersion: p.proposalVersion, approvalId: p.approvalId, riskEvaluationId: p.riskEvaluationId, budgetReservationId: p.budgetReservationId, resourceReservationId: p.resourceReservationId, targetPortfolioVersion: p.targetPortfolioVersion, validUntil: p.validUntil, legs: p.legs.map(({ legId, securityId, side, quantity }) => ({ legId, securityId, side, quantity })), contentHash: p.executionContentHash, idempotencyKey: request.idempotencyKey }, this.config.executionToken, request.idempotencyKey);
    return this.response(request, result, { accepted: true });
  }
  async createManualOrderIntents(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>> {
    this.require(request); const batchId = `rebalance-${request.workflowId}`; const response = await this.http.fetch(`${this.config.executionBaseUrl}/api/v1/execution/batches/${encodeURIComponent(batchId)}`, { headers: { 'x-service-token': this.config.executionToken, authorization: `Bearer ${this.config.executionToken}`, accept: 'application/json' } }); if (!response || response.status < 200 || response.status >= 300) throw new Error(`activity HTTP request failed: ${response?.status ?? 'no-response'}`); const result = await response.json() as { intents?: readonly { intentId: string }[] };
    for (const intent of ((result as { intents?: readonly { intentId: string }[] }).intents ?? [])) await this.post(`${this.config.executionBaseUrl}/api/v1/execution/batches/${encodeURIComponent(batchId)}/intents/${encodeURIComponent(intent.intentId)}/status`, { status: 'SUBMITTED_MANUALLY' }, this.config.executionToken, `${request.idempotencyKey}:intent:${intent.intentId}`);
    return this.response(request, result, { accepted: true });
  }
  async recordFills(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>> {
    const p = this.require(request); if (!p.fills?.length) throw new Error('real rebalance requires explicit fills'); const batchId = `rebalance-${request.workflowId}`;
    for (const fill of p.fills) await this.post(`${this.config.executionBaseUrl}/api/v1/execution/batches/${encodeURIComponent(batchId)}/fills`, { fillId: fill.fillId, intentId: fill.intentId, filledQuantity: fill.filledQuantity, fillPrice: fill.fillPrice, occurredAt: fill.occurredAt, idempotencyKey: fill.idempotencyKey }, this.config.executionToken, fill.idempotencyKey);
    return this.response(request, { fills: p.fills }, { fillStatus: p.fills.every((fill) => fill.filledQuantity === p.legs?.find((leg) => `order-intent-${batchId}-${leg.legId}` === fill.intentId)?.quantity) ? 'COMPLETE' : 'PARTIAL' });
  }
  async releaseBudget(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>> {
    const p = this.require(request); if (!p.proposalId || !p.budgetReservationId) throw new Error('real rebalance requires proposalId and budgetReservationId'); const result = await this.post(`${this.config.governanceBaseUrl}/api/v1/proposals/${encodeURIComponent(p.proposalId)}/budget-reservations/${encodeURIComponent(p.budgetReservationId)}/release`, {}, this.config.governanceToken, `${request.idempotencyKey}:release`); return this.response(request, result, { reservationStatus: 'RELEASED' });
  }
  private require(request: RebalanceExecutionRequest) { return validateActivityRequest(request).payload; }
  private async post(url: string, body: unknown, token: string, idempotencyKey: string): Promise<unknown> { const response = await this.http.fetch(url, { method: 'POST', headers: { 'content-type': 'application/json', 'x-service-token': token, authorization: `Bearer ${token}`, 'Idempotency-Key': idempotencyKey, 'X-Correlation-Id': idempotencyKey }, body: JSON.stringify(body) }); if (!response || response.status < 200 || response.status >= 300) { const detail = response ? await response.text().catch(() => '') : ''; throw new Error(`activity HTTP request failed: ${response?.status ?? 'no-response'}${detail ? ` ${detail}` : ''}`); } return response.json(); }
  private response(request: RebalanceExecutionRequest, body: unknown, result: Omit<RebalanceStepResult, 'artifactRef'>): ActivityResponse<RebalanceStepResult> { const sha256 = createHash('sha256').update(JSON.stringify(body)).digest('hex'); const artifactRef: ArtifactRef = { uri: `artifact://workflow/${request.workflowId}/${request.idempotencyKey}`, sha256 }; return { correlationId: request.correlationId, result: { ...result, artifactRef }, artifactRefs: [artifactRef] }; }
}
