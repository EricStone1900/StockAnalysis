import type { CreateProposalCommand, TradeProposal } from '../domain/proposal.js';

export interface SqlClient { query<T extends Record<string, unknown> = Record<string, unknown>>(sql: string, parameters?: readonly unknown[]): Promise<{ rows: T[] }> }
export class PostgresProposalRepository {
  public constructor(private readonly client: SqlClient) {}
  public async findByIdempotency(key: string): Promise<TradeProposal | undefined> { const result = await this.client.query<{ payload: TradeProposal }>('SELECT payload FROM trade_proposals WHERE idempotency_key = $1', [key]); return result.rows[0]?.payload; }
  public async latest(proposalId: string): Promise<TradeProposal | undefined> { const result = await this.client.query<{ payload: TradeProposal }>('SELECT payload FROM trade_proposals WHERE proposal_id = $1 ORDER BY proposal_version DESC LIMIT 1', [proposalId]); return result.rows[0]?.payload; }
  public async append(command: CreateProposalCommand, proposal: TradeProposal): Promise<void> { await this.client.query(`INSERT INTO trade_proposals (proposal_id, proposal_version, proposal_kind, state, agent_run_id, target_portfolio_version, parent_proposal_version, legs, evidence, content_hash, payload, idempotency_key, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,$10,$11::jsonb,$12,$13)`, [proposal.proposalId, proposal.proposalVersion, proposal.kind, proposal.state, proposal.agentRunId, proposal.targetPortfolioVersion, proposal.parentProposalVersion, JSON.stringify(proposal.legs), JSON.stringify(proposal.evidence), proposal.contentHash, JSON.stringify(proposal), command.idempotencyKey, proposal.createdAt]); }
}
