import { Injectable } from '@nestjs/common';
import { CreateProposalCommand, ProposalAggregate, RiskReviewLink, TradeProposal } from '../domain/proposal.js';
import type { PostgresProposalRepository } from '../infrastructure/postgres-proposal-repository.js';

@Injectable()
export class GovernanceService {
  public constructor(private readonly aggregate = new ProposalAggregate(), private readonly repository?: PostgresProposalRepository) {}
  public async createDraft(command: CreateProposalCommand): Promise<TradeProposal> { const repeated = await this.repository?.findByIdempotency(command.idempotencyKey); if (repeated) return repeated; const proposal = this.aggregate.createDraft(command); await this.repository?.append(command, proposal); return proposal; }
  public async getProposal(proposalId: string, version?: number): Promise<TradeProposal | undefined> { return version === undefined ? (await this.repository?.latest(proposalId)) ?? this.aggregate.get(proposalId) : this.aggregate.get(proposalId, version); }
  public attachRiskReview(proposalId: string, proposalVersion: number, review: RiskReviewLink): TradeProposal { return this.aggregate.attachRiskReview(proposalId, proposalVersion, review); }
  public markRiskPassed(proposalId: string, proposalVersion: number, evaluationId: string): TradeProposal { return this.aggregate.markRiskPassed(proposalId, proposalVersion, evaluationId); }
}
