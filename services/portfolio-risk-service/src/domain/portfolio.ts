import { createHash } from 'node:crypto';

export type LedgerEntryType = 'OPENING' | 'BUY' | 'SELL' | 'FEE' | 'DIVIDEND' | 'REVERSAL';

export interface LedgerEntry {
  readonly entryId: string;
  readonly portfolioId: string;
  readonly type: LedgerEntryType;
  readonly securityId?: string;
  readonly quantity?: string;
  readonly amount: string;
  readonly occurredAt: string;
  readonly availableAt: string;
  readonly sourceRef: string;
  readonly actorId: string;
  readonly reason: string;
}

export interface Position {
  readonly securityId: string;
  readonly quantity: string;
  readonly availableQuantity: string;
}

export interface PortfolioSnapshot {
  readonly snapshotId: string;
  readonly portfolioId: string;
  readonly accountId: string;
  readonly asOf: string;
  readonly cash: string;
  readonly positions: readonly Position[];
  readonly ledgerVersion: number;
  readonly sourceRef: string;
  readonly contentHash: string;
}

export interface OpeningPosition {
  readonly securityId: string;
  readonly quantity: string;
}

export interface OpeningSnapshotCommand {
  readonly portfolioId: string;
  readonly accountId: string;
  readonly cash: string;
  readonly positions: readonly OpeningPosition[];
  readonly occurredAt: string;
  readonly availableAt: string;
  readonly sourceRef: string;
  readonly actorId: string;
  readonly reason: string;
  readonly expectedVersion: number;
  readonly idempotencyKey: string;
}

export class PortfolioLedger {
  private version: number;
  private readonly snapshots = new Map<string, PortfolioSnapshot>();
  private readonly idempotency = new Map<string, PortfolioSnapshot>();

  constructor(initialVersion = 0) {
    if (!Number.isInteger(initialVersion) || initialVersion < 0) throw new Error('invalid initial ledger version');
    this.version = initialVersion;
  }

  restoreVersion(version: number): void {
    if (!Number.isInteger(version) || version < this.version) throw new Error('cannot restore an older ledger version');
    this.version = version;
  }

  importOpening(command: OpeningSnapshotCommand): PortfolioSnapshot {
    const repeated = this.idempotency.get(command.idempotencyKey);
    if (repeated) return repeated;
    if (command.expectedVersion !== this.version) throw new Error('ledger version conflict');
    validateCommand(command);
    const positions = [...command.positions]
      .sort((left, right) => left.securityId.localeCompare(right.securityId))
      .map((position) => ({ securityId: position.securityId, quantity: position.quantity, availableQuantity: position.quantity }));
    const nextVersion = this.version + 1;
    const snapshotWithoutHash = {
      snapshotId: `portfolio-snapshot-${command.portfolioId}-${nextVersion}`,
      portfolioId: command.portfolioId,
      accountId: command.accountId,
      asOf: command.availableAt,
      cash: command.cash,
      positions,
      ledgerVersion: nextVersion,
      sourceRef: command.sourceRef,
    };
    const snapshot: PortfolioSnapshot = {
      ...snapshotWithoutHash,
      contentHash: sha256(snapshotWithoutHash),
    };
    this.version = nextVersion;
    this.snapshots.set(snapshot.snapshotId, snapshot);
    this.idempotency.set(command.idempotencyKey, snapshot);
    return snapshot;
  }

  latest(portfolioId: string): PortfolioSnapshot | undefined {
    return [...this.snapshots.values()].filter((snapshot) => snapshot.portfolioId === portfolioId).at(-1);
  }
}

function validateCommand(command: OpeningSnapshotCommand): void {
  for (const value of [command.cash, ...command.positions.map((position) => position.quantity)]) validateDecimal(value);
  if (!command.portfolioId || !command.accountId || !command.sourceRef || !command.actorId || !command.reason || !command.idempotencyKey) throw new Error('required opening snapshot field is missing');
  if (command.positions.some((position) => !position.securityId || decimalToNumber(position.quantity) <= 0)) throw new Error('position quantity must be positive');
  if (!Date.parse(command.occurredAt) || !Date.parse(command.availableAt)) throw new Error('invalid event time');
  if (new Date(command.availableAt) < new Date(command.occurredAt)) throw new Error('availableAt cannot precede occurredAt');
}

function validateDecimal(value: string): void {
  if (!/^-?\d+(?:\.\d{1,8})?$/.test(value)) throw new Error('amount and quantity must be Decimal strings with at most 8 places');
}

function decimalToNumber(value: string): number {
  return Number(value);
}

function sha256(value: object): string {
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}
