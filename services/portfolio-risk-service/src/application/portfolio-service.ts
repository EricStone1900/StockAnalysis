import { OpeningSnapshotCommand, PortfolioLedger, PortfolioSnapshot } from '../domain/portfolio.js';

export class PortfolioService {
  constructor(private readonly ledger: PortfolioLedger) {}

  importOpening(command: OpeningSnapshotCommand): PortfolioSnapshot {
    return this.ledger.importOpening(command);
  }

  latest(portfolioId: string): PortfolioSnapshot | undefined {
    return this.ledger.latest(portfolioId);
  }
}
