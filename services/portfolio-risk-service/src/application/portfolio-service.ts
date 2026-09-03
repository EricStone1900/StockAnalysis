import { OpeningSnapshotCommand, PortfolioLedger, PortfolioSnapshot } from '../domain/portfolio.js';
import type { PostgresPortfolioRepository } from '../infrastructure/postgres-portfolio-repository.js';

export class PortfolioService {
  constructor(private readonly ledger: PortfolioLedger, private readonly repository?: PostgresPortfolioRepository) {}

  async importOpening(command: OpeningSnapshotCommand): Promise<PortfolioSnapshot> {
    if (this.repository) {
      const repeated = await this.repository.findByIdempotency(command.portfolioId, command.idempotencyKey);
      if (repeated) return repeated;
    }
    const snapshot = this.ledger.importOpening(command);
    if (this.repository) await this.repository.appendOpening(command, snapshot);
    return snapshot;
  }

  async latest(portfolioId: string): Promise<PortfolioSnapshot | undefined> {
    return (await this.repository?.latest(portfolioId)) ?? this.ledger.latest(portfolioId);
  }
}
