import { CreateProposalCommand, ProposalAggregate, TradeProposal } from '../domain/proposal.js';

export class GovernanceService {
  public constructor(private readonly aggregate = new ProposalAggregate()) {}
  public createDraft(command: CreateProposalCommand): TradeProposal { return this.aggregate.createDraft(command); }
  public getProposal(proposalId: string, version?: number): TradeProposal | undefined { return this.aggregate.get(proposalId, version); }
}
