import { createHash } from 'node:crypto';

export type ProposalState = 'DRAFT' | 'RISK_REVIEWED' | 'RISK_PASSED' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'REVISION_REQUIRED' | 'REVIEW_BLOCKED';
export type ProposalKind = 'HOLD' | 'REBALANCE';
export interface EvidenceRef { readonly kind: 'quant' | 'strategy' | 'news' | 'regime' | 'portfolio' | 'anomaly'; readonly uri: string; readonly contentHash: string; readonly capturedAt: string; }
export interface RebalanceLeg { readonly securityId: string; readonly side: 'BUY' | 'SELL'; readonly quantity: string; readonly targetWeight?: string; }
export interface CreateProposalCommand { readonly proposalId: string; readonly kind: ProposalKind; readonly parentProposalVersion?: number; readonly agentRunId: string; readonly targetPortfolioVersion: number; readonly legs: readonly RebalanceLeg[]; readonly evidence: readonly EvidenceRef[]; readonly contentHash: string; readonly idempotencyKey: string; readonly createdAt: string; readonly correlationId?: string; }
export interface RiskReviewLink { readonly evaluationId: string; readonly policyVersion: string; readonly verdict: 'PASS' | 'REJECT'; readonly reviewedAt: string; }
export interface ApprovalRecord { readonly actorId: string; readonly decision: 'APPROVED' | 'REJECTED'; readonly reason: string; readonly decidedAt: string; }
export interface TradeProposal { readonly proposalId: string; readonly proposalVersion: number; readonly parentProposalVersion?: number; readonly kind: ProposalKind; readonly state: ProposalState; readonly agentRunId: string; readonly targetPortfolioVersion: number; readonly legs: readonly RebalanceLeg[]; readonly evidence: readonly EvidenceRef[]; readonly contentHash: string; readonly createdAt: string; readonly riskReview?: RiskReviewLink; readonly approval?: ApprovalRecord; }

export class ProposalAggregate {
  private readonly proposals = new Map<string, TradeProposal>();
  private readonly idempotency = new Map<string, TradeProposal>();

  /** 进程重启后由持久化适配器恢复，状态机仍只在聚合内迁移。 */
  restore(proposal: TradeProposal): void { this.proposals.set(`${proposal.proposalId}:${proposal.proposalVersion}`, proposal); }

  attachRiskReview(proposalId: string, proposalVersion: number, review: RiskReviewLink): TradeProposal {
    const key = `${proposalId}:${proposalVersion}`; const proposal = this.proposals.get(key);
    if (!proposal) throw new Error('proposal not found');
    if (proposal.state !== 'DRAFT' && proposal.state !== 'RISK_REVIEWED') throw new Error('proposal state does not allow risk review');
    if (!review.evaluationId || !review.policyVersion || !Date.parse(review.reviewedAt)) throw new Error('invalid risk review');
    const updated: TradeProposal = { ...proposal, state: 'RISK_REVIEWED', riskReview: review };
    this.proposals.set(key, updated); return updated;
  }

  markRiskPassed(proposalId: string, proposalVersion: number, evaluationId: string): TradeProposal {
    const key = `${proposalId}:${proposalVersion}`; const proposal = this.proposals.get(key);
    if (!proposal || proposal.state !== 'RISK_REVIEWED' || proposal.riskReview?.evaluationId !== evaluationId) throw new Error('risk review does not match proposal');
    if (proposal.riskReview.verdict !== 'PASS') throw new Error('risk evaluation is not PASS');
    const updated: TradeProposal = { ...proposal, state: 'RISK_PASSED' };
    this.proposals.set(key, updated); return updated;
  }

  decide(proposalId: string, proposalVersion: number, approval: ApprovalRecord): TradeProposal {
    const key = `${proposalId}:${proposalVersion}`; const proposal = this.proposals.get(key);
    if (!proposal || proposal.state !== 'RISK_PASSED') throw new Error('proposal is not ready for approval');
    if (!approval.actorId || !approval.reason || !Date.parse(approval.decidedAt)) throw new Error('invalid approval record');
    const updated: TradeProposal = { ...proposal, state: approval.decision, approval };
    this.proposals.set(key, updated); return updated;
  }

  createDraft(command: CreateProposalCommand): TradeProposal {
    const repeated = this.idempotency.get(command.idempotencyKey);
    if (repeated) return repeated;
    if (!command.proposalId || !command.agentRunId || !command.idempotencyKey || command.targetPortfolioVersion < 1) throw new Error('required proposal field is missing');
    if (command.kind === 'HOLD' && command.legs.length > 0) throw new Error('HOLD proposal must not contain legs');
    if (command.kind === 'REBALANCE' && command.legs.length === 0) throw new Error('REBALANCE proposal requires at least one leg');
    if (command.parentProposalVersion !== undefined && (!Number.isInteger(command.parentProposalVersion) || command.parentProposalVersion < 1)) throw new Error('invalid parent proposal version');
    for (const evidence of command.evidence) { if (!evidence.uri || !/^[a-f0-9]{64}$/.test(evidence.contentHash) || !Date.parse(evidence.capturedAt)) throw new Error('invalid evidence reference'); }
    const existing = [...this.proposals.values()].filter((proposal) => proposal.proposalId === command.proposalId).sort((left, right) => right.proposalVersion - left.proposalVersion)[0];
    const proposalVersion = existing ? existing.proposalVersion + 1 : 1;
    if (existing && command.parentProposalVersion !== existing.proposalVersion) throw new Error('parent proposal version conflict');
    const canonical = { proposalId: command.proposalId, proposalVersion, parentProposalVersion: command.parentProposalVersion, kind: command.kind, state: 'DRAFT' as const, agentRunId: command.agentRunId, targetPortfolioVersion: command.targetPortfolioVersion, legs: command.legs, evidence: command.evidence, createdAt: command.createdAt };
    const expectedHash = createHash('sha256').update(JSON.stringify(canonical)).digest('hex');
    if (expectedHash !== command.contentHash) throw new Error('proposal content hash mismatch');
    const proposal = { ...canonical, contentHash: command.contentHash };
    this.proposals.set(`${command.proposalId}:${proposalVersion}`, proposal);
    this.idempotency.set(command.idempotencyKey, proposal);
    return proposal;
  }
  get(proposalId: string, version?: number): TradeProposal | undefined { return [...this.proposals.values()].filter((proposal) => proposal.proposalId === proposalId && (version === undefined || proposal.proposalVersion === version)).sort((left, right) => right.proposalVersion - left.proposalVersion)[0]; }
}
