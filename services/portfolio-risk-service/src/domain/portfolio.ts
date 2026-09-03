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
export interface ReversalCommand {
  readonly portfolioId: string;
  readonly originalEntryId: string;
  readonly occurredAt: string;
  readonly availableAt: string;
  readonly sourceRef: string;
  readonly actorId: string;
  readonly reason: string;
  readonly expectedVersion: number;
  readonly idempotencyKey: string;
}

export class PortfolioLedger {
  private readonly versions = new Map<string, number>();
  private readonly snapshots = new Map<string, PortfolioSnapshot>();
  private readonly idempotency = new Map<string, PortfolioSnapshot>();
  private readonly entries = new Map<string, LedgerEntry>();
  private readonly reversals = new Set<string>();
  private readonly reversalIdempotency = new Map<string, LedgerEntry>();

  constructor(initialVersion = 0) {
    if (!Number.isInteger(initialVersion) || initialVersion < 0) throw new Error('invalid initial ledger version');
    this.defaultVersion = initialVersion;
  }
  private readonly defaultVersion: number;

  restoreVersion(portfolioId: string, version: number): void {
    const current = this.versions.get(portfolioId) ?? this.defaultVersion;
    if (!Number.isInteger(version) || version < current) throw new Error('cannot restore an older ledger version');
    this.versions.set(portfolioId, version);
  }

  restoreEntry(entry: LedgerEntry): void { this.entries.set(entry.entryId, entry); }
  restoreSnapshot(snapshot: PortfolioSnapshot): void {
    this.restoreVersion(snapshot.portfolioId, snapshot.ledgerVersion);
    this.snapshots.set(snapshot.snapshotId, snapshot);
  }

  importOpening(command: OpeningSnapshotCommand): PortfolioSnapshot {
    const repeated = this.idempotency.get(command.idempotencyKey);
    if (repeated) return repeated;
    const currentVersion = this.versions.get(command.portfolioId) ?? this.defaultVersion;
    if (command.expectedVersion !== currentVersion) throw new Error('ledger version conflict');
    validateCommand(command);
    const positions = [...command.positions]
      .sort((left, right) => left.securityId.localeCompare(right.securityId))
      .map((position) => ({ securityId: position.securityId, quantity: position.quantity, availableQuantity: position.quantity }));
    const nextVersion = currentVersion + 1;
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
    this.versions.set(command.portfolioId, nextVersion);
    this.entries.set(`ledger-entry-${snapshot.snapshotId}`, { entryId: `ledger-entry-${snapshot.snapshotId}`, portfolioId: command.portfolioId, type: 'OPENING', amount: command.cash, occurredAt: command.occurredAt, availableAt: command.availableAt, sourceRef: command.sourceRef, actorId: command.actorId, reason: command.reason });
    this.snapshots.set(snapshot.snapshotId, snapshot);
    this.idempotency.set(command.idempotencyKey, snapshot);
    return snapshot;
  }

  latest(portfolioId: string): PortfolioSnapshot | undefined {
    return [...this.snapshots.values()].filter((snapshot) => snapshot.portfolioId === portfolioId).sort((left, right) => right.ledgerVersion - left.ledgerVersion)[0];
  }

  reverse(command: ReversalCommand): LedgerEntry {
    const repeated = this.reversalIdempotency.get(`${command.portfolioId}:${command.idempotencyKey}`);
    if (repeated) return repeated;
    const original = this.entries.get(command.originalEntryId);
    if (!original || original.portfolioId !== command.portfolioId) throw new Error('original ledger entry not found');
    if (this.reversals.has(command.originalEntryId)) throw new Error('ledger entry already reversed');
    const currentVersion = this.versions.get(command.portfolioId) ?? this.defaultVersion;
    if (command.expectedVersion !== currentVersion) throw new Error('ledger version conflict');
    if (!command.sourceRef || !command.actorId || !command.reason || !command.idempotencyKey) throw new Error('required reversal field is missing');
    const entry: LedgerEntry = { entryId: `reversal-${command.originalEntryId}-${currentVersion + 1}`, portfolioId: command.portfolioId, type: 'REVERSAL', amount: negateDecimal(original.amount), occurredAt: command.occurredAt, availableAt: command.availableAt, sourceRef: command.sourceRef, actorId: command.actorId, reason: command.reason };
    this.reversals.add(command.originalEntryId);
    this.entries.set(entry.entryId, entry);
    this.reversalIdempotency.set(`${command.portfolioId}:${command.idempotencyKey}`, entry);
    this.versions.set(command.portfolioId, currentVersion + 1);
    return entry;
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
function negateDecimal(value: string): string { return value.startsWith('-') ? value.slice(1) : `-${value}`; }

function sha256(value: object): string {
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}
