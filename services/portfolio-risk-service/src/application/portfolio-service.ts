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
      if (latest) this.ledger.restoreVersion(command.portfolioId, latest.ledgerVersion);
    }
    const snapshot = this.ledger.importOpening(command);
    if (this.repository) {
      try {
        await this.repository.appendOpening(command, snapshot);
      } catch (error) {
        if (isUniqueViolation(error)) {
          const repeated = await this.repository.findByIdempotency(command.portfolioId, command.idempotencyKey);
          if (repeated) return repeated;
        }
        throw error;
      }
    }
    return snapshot;
  }

  async latest(portfolioId: string): Promise<PortfolioSnapshot | undefined> {
    return (await this.repository?.latest(portfolioId)) ?? this.ledger.latest(portfolioId);
  }
}

function isUniqueViolation(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'code' in error && (error as { code?: unknown }).code === '23505';
}
