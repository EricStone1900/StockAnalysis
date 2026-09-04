import { CashDividendCommand, ConfirmedFillCommand, LedgerEntry, OpeningSnapshotCommand, PortfolioLedger, PortfolioSnapshot, ReversalCommand, StockSplitCommand } from '../domain/portfolio.js';
interface PortfolioPersistence {
  findByIdempotency(portfolioId: string, idempotencyKey: string): Promise<PortfolioSnapshot | undefined>;
  latest(portfolioId: string): Promise<PortfolioSnapshot | undefined>;
  findEntry?(entryId: string): Promise<LedgerEntry | undefined>;
  findReversalByIdempotency?(portfolioId: string, key: string): Promise<LedgerEntry | undefined>;
  appendOpening(command: OpeningSnapshotCommand, snapshot: PortfolioSnapshot): Promise<void>;
  appendReversal?(command: ReversalCommand, entry: LedgerEntry): Promise<void>;
  appendConfirmedFill?(command: ConfirmedFillCommand, snapshot: PortfolioSnapshot): Promise<void>;
  appendCashDividend?(command: CashDividendCommand, snapshot: PortfolioSnapshot): Promise<void>;
  appendStockSplit?(command: StockSplitCommand, snapshot: PortfolioSnapshot): Promise<void>;
}

export class PortfolioService {
  constructor(private readonly ledger: PortfolioLedger, private readonly repository?: PortfolioPersistence) {}

  async importOpening(command: OpeningSnapshotCommand): Promise<PortfolioSnapshot> {
    if (this.repository) {
      const repeated = await this.repository.findByIdempotency(command.portfolioId, command.idempotencyKey);
      if (repeated) return repeated;
      const latest = await this.repository.latest(command.portfolioId);
      if (latest) this.ledger.restoreSnapshot(latest);
    }
    const snapshot = this.ledger.importOpening(command);
    if (this.repository) {
      try {
        await this.repository.appendOpening(command, snapshot);
      } catch (error) {
        if (isUniqueViolation(error)) {
          const repeated = await readIdempotentWithRetry(this.repository, command.portfolioId, command.idempotencyKey);
          if (repeated) return repeated;
          throw new Error('ledger version conflict');
        }
        throw error;
      }
    }
    return snapshot;
  }

  async latest(portfolioId: string): Promise<PortfolioSnapshot | undefined> {
    return (await this.repository?.latest(portfolioId)) ?? this.ledger.latest(portfolioId);
  }

  async reverse(command: ReversalCommand): Promise<LedgerEntry> {
    const persisted = await this.repository?.findReversalByIdempotency?.(command.portfolioId, command.idempotencyKey);
    if (persisted) return persisted;
    if (this.repository?.findEntry) {
      const original = await this.repository.findEntry(command.originalEntryId);
      if (original) this.ledger.restoreEntry(original);
    }
    const entry = this.ledger.reverse(command);
    if (this.repository?.appendReversal) {
      try { await this.repository.appendReversal(command, entry); } catch (error) {
        if (isUniqueViolation(error)) {
          const repeated = await this.repository.findReversalByIdempotency?.(command.portfolioId, command.idempotencyKey);
          if (repeated) return repeated;
        }
        throw error;
      }
    }
    return entry;
  }

  async recordConfirmedFill(command: ConfirmedFillCommand): Promise<PortfolioSnapshot> {
    if (this.repository) {
      const repeated = await this.repository.findByIdempotency(command.portfolioId, command.idempotencyKey);
      if (repeated) return repeated;
      const latest = await this.repository.latest(command.portfolioId);
      if (latest) this.ledger.restoreSnapshot(latest);
    }
    const snapshot = this.ledger.recordConfirmedFill(command);
    if (this.repository?.appendConfirmedFill) {
      try { await this.repository.appendConfirmedFill(command, snapshot); }
      catch (error) {
        if (isUniqueViolation(error)) {
          const repeated = await readIdempotentWithRetry(this.repository, command.portfolioId, command.idempotencyKey);
          if (repeated) return repeated;
          throw new Error('ledger version conflict');
        }
        throw error;
      }
    }
    return snapshot;
  }

  async recordCashDividend(command: CashDividendCommand): Promise<PortfolioSnapshot> {
    if (this.repository) {
      const repeated = await this.repository.findByIdempotency(command.portfolioId, command.idempotencyKey);
      if (repeated) return repeated;
      const latest = await this.repository.latest(command.portfolioId);
      if (latest) this.ledger.restoreSnapshot(latest);
    }
    const snapshot = this.ledger.recordCashDividend(command);
    if (this.repository?.appendCashDividend) {
      try { await this.repository.appendCashDividend(command, snapshot); }
      catch (error) {
        if (isUniqueViolation(error)) {
          const repeated = await readIdempotentWithRetry(this.repository, command.portfolioId, command.idempotencyKey);
          if (repeated) return repeated;
          throw new Error('ledger version conflict');
        }
        throw error;
      }
    }
    return snapshot;
  }

  async recordStockSplit(command: StockSplitCommand): Promise<PortfolioSnapshot> {
    if (this.repository) {
      const repeated = await this.repository.findByIdempotency(command.portfolioId, command.idempotencyKey);
      if (repeated) return repeated;
      const latest = await this.repository.latest(command.portfolioId);
      if (latest) this.ledger.restoreSnapshot(latest);
    }
    const snapshot = this.ledger.recordStockSplit(command);
    if (this.repository?.appendStockSplit) {
      try { await this.repository.appendStockSplit(command, snapshot); }
      catch (error) {
        if (isUniqueViolation(error)) {
          const repeated = await readIdempotentWithRetry(this.repository, command.portfolioId, command.idempotencyKey);
          if (repeated) return repeated;
          throw new Error('ledger version conflict');
        }
        throw error;
      }
    }
    return snapshot;
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
