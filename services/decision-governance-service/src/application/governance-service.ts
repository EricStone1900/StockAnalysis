import { Injectable } from '@nestjs/common';
import { ApprovalRecord, CreateProposalCommand, ProposalAggregate, RiskReviewLink, TradeProposal } from '../domain/proposal.js';
import type { PostgresProposalRepository } from '../infrastructure/postgres-proposal-repository.js';
import { DecisionBudgetReservation, type DecisionBudgetPolicy, type Reservation } from '../domain/decision-budget.js';

@Injectable()
export class GovernanceService {
  public constructor(private readonly aggregate = new ProposalAggregate(), private readonly repository?: PostgresProposalRepository, private readonly budget = new DecisionBudgetReservation()) {}
  public async createDraft(command: CreateProposalCommand): Promise<TradeProposal> { const repeated = await this.repository?.findByIdempotency(command.idempotencyKey); if (repeated) return repeated; const proposal = this.aggregate.createDraft(command); await this.repository?.append(command, proposal); return proposal; }
  public async getProposal(proposalId: string, version?: number): Promise<TradeProposal | undefined> { return version === undefined ? (await this.repository?.latest(proposalId)) ?? this.aggregate.get(proposalId) : this.aggregate.get(proposalId, version); }
  public async attachRiskReview(proposalId: string, proposalVersion: number, review: RiskReviewLink): Promise<TradeProposal> { const proposal = this.aggregate.attachRiskReview(proposalId, proposalVersion, review); await this.repository?.updateRiskReview(proposalId, proposalVersion, review, proposal.state); return proposal; }
  public async markRiskPassed(proposalId: string, proposalVersion: number, evaluationId: string): Promise<TradeProposal> { const proposal = this.aggregate.markRiskPassed(proposalId, proposalVersion, evaluationId); if (proposal.riskReview) await this.repository?.updateRiskReview(proposalId, proposalVersion, proposal.riskReview, proposal.state); return proposal; }
  public async decide(proposalId: string, proposalVersion: number, approval: ApprovalRecord): Promise<TradeProposal> { const proposal = this.aggregate.decide(proposalId, proposalVersion, approval); await this.repository?.updateApproval(proposalId, proposalVersion, approval, proposal.state); return proposal; }
  public reserveBudget(input: { reservationId: string; portfolioId: string; tradingDate: string; reason: string; proposalId: string; kind: 'HOLD' | 'REBALANCE'; idempotencyKey: string }, policy: DecisionBudgetPolicy): Reservation { return this.budget.reserve(input, policy); }
  public releaseBudget(reservationId: string): Reservation { return this.budget.release(reservationId); }
}
