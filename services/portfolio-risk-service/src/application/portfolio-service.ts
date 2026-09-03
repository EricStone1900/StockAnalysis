import { OpeningSnapshotCommand, PortfolioLedger, PortfolioSnapshot } from '../domain/portfolio.js';
interface PortfolioPersistence {
  findByIdempotency(portfolioId: string, idempotencyKey: string): Promise<PortfolioSnapshot | undefined>;
  latest(portfolioId: string): Promise<PortfolioSnapshot | undefined>;
  appendOpening(command: OpeningSnapshotCommand, snapshot: PortfolioSnapshot): Promise<void>;
}

export class PortfolioService {
  constructor(private readonly ledger: PortfolioLedger, private readonly repository?: PortfolioPersistence) {}

  async importOpening(command: OpeningSnapshotCommand): Promise<PortfolioSnapshot> {
    if (this.repository) {
      const repeated = await this.repository.findByIdempotency(command.portfolioId, command.idempotencyKey);
      if (repeated) return repeated;
      const latest = await this.repository.latest(command.portfolioId);
      if (latest) this.ledger.restoreVersion(latest.ledgerVersion);
    }
    const snapshot = this.ledger.importOpening(command);
    if (this.repository) await this.repository.appendOpening(command, snapshot);
    return snapshot;
  }

  async latest(portfolioId: string): Promise<PortfolioSnapshot | undefined> {
    return (await this.repository?.latest(portfolioId)) ?? this.ledger.latest(portfolioId);
  }
}
