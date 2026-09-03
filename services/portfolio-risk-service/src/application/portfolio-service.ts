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
          const repeated = await readIdempotentWithRetry(this.repository, command.portfolioId, command.idempotencyKey);
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

async function readIdempotentWithRetry(repository: PortfolioPersistence, portfolioId: string, key: string): Promise<PortfolioSnapshot | undefined> {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const snapshot = await repository.findByIdempotency(portfolioId, key);
    if (snapshot) return snapshot;
    if (attempt < 2) await new Promise((resolve) => setTimeout(resolve, 10));
  }
  return undefined;
}

function isUniqueViolation(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'code' in error && (error as { code?: unknown }).code === '23505';
}
