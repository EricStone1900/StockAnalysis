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
  readonly correlationId?: string;
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
  readonly correlationId?: string;
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
  readonly correlationId?: string;
}
export interface ConfirmedFillCommand {
  readonly portfolioId: string;
  readonly securityId: string;
  readonly side: 'BUY' | 'SELL';
  readonly quantity: string;
  readonly price: string;
  readonly fee: string;
  readonly occurredAt: string;
  readonly availableAt: string;
  readonly sourceRef: string;
  readonly actorId: string;
  readonly reason: string;
  readonly expectedVersion: number;
  readonly idempotencyKey: string;
  readonly correlationId?: string;
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
    this.entries.set(`ledger-entry-${snapshot.snapshotId}`, { entryId: `ledger-entry-${snapshot.snapshotId}`, portfolioId: command.portfolioId, type: 'OPENING', amount: command.cash, occurredAt: command.occurredAt, availableAt: command.availableAt, sourceRef: command.sourceRef, actorId: command.actorId, reason: command.reason, correlationId: command.correlationId });
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
    const entry: LedgerEntry = { entryId: `reversal-${command.originalEntryId}-${currentVersion + 1}`, portfolioId: command.portfolioId, type: 'REVERSAL', amount: negateDecimal(original.amount), occurredAt: command.occurredAt, availableAt: command.availableAt, sourceRef: command.sourceRef, actorId: command.actorId, reason: command.reason, correlationId: command.correlationId };
    this.reversals.add(command.originalEntryId);
    this.entries.set(entry.entryId, entry);
    this.reversalIdempotency.set(`${command.portfolioId}:${command.idempotencyKey}`, entry);
    this.versions.set(command.portfolioId, currentVersion + 1);
    return entry;
  }

  recordConfirmedFill(command: ConfirmedFillCommand): PortfolioSnapshot {
    const idempotencyKey = `${command.portfolioId}:${command.idempotencyKey}`;
    const repeated = this.idempotency.get(idempotencyKey);
    if (repeated) return repeated;
    const previous = this.latest(command.portfolioId);
    if (!previous) throw new Error('opening snapshot is required before a fill');
    const currentVersion = this.versions.get(command.portfolioId) ?? this.defaultVersion;
    if (command.expectedVersion !== currentVersion) throw new Error('ledger version conflict');
    validateFillCommand(command);
    const gross = multiplyDecimal(command.quantity, command.price);
    const currentPositions = new Map(previous.positions.map((position) => [position.securityId, position]));
    const current = currentPositions.get(command.securityId) ?? { securityId: command.securityId, quantity: '0', availableQuantity: '0' };
    const nextQuantity = command.side === 'BUY' ? addDecimal(current.quantity, command.quantity) : subtractDecimal(current.quantity, command.quantity);
    if (isNegative(nextQuantity)) throw new Error('sell quantity exceeds available position');
    if (isZero(nextQuantity)) currentPositions.delete(command.securityId);
    else currentPositions.set(command.securityId, { securityId: command.securityId, quantity: nextQuantity, availableQuantity: nextQuantity });
    const cashBeforeFee = command.side === 'BUY' ? subtractDecimal(previous.cash, gross) : addDecimal(previous.cash, gross);
    const cash = subtractDecimal(cashBeforeFee, command.fee);
    const nextVersion = currentVersion + 1;
    const snapshotWithoutHash = { snapshotId: `portfolio-snapshot-${command.portfolioId}-${nextVersion}`, portfolioId: command.portfolioId, accountId: previous.accountId, asOf: command.availableAt, cash, positions: [...currentPositions.values()].sort((left, right) => left.securityId.localeCompare(right.securityId)), ledgerVersion: nextVersion, sourceRef: command.sourceRef };
    const snapshot: PortfolioSnapshot = { ...snapshotWithoutHash, contentHash: sha256(snapshotWithoutHash) };
    const entry: LedgerEntry = { entryId: `ledger-entry-${command.portfolioId}-${nextVersion}`, portfolioId: command.portfolioId, type: command.side, securityId: command.securityId, quantity: command.quantity, amount: gross, occurredAt: command.occurredAt, availableAt: command.availableAt, sourceRef: command.sourceRef, actorId: command.actorId, reason: command.reason, correlationId: command.correlationId };
    this.versions.set(command.portfolioId, nextVersion);
    this.entries.set(entry.entryId, entry);
    if (!isZero(command.fee)) this.entries.set(`fee-${entry.entryId}`, { ...entry, entryId: `fee-${entry.entryId}`, type: 'FEE', amount: negateDecimal(command.fee), quantity: undefined, securityId: undefined });
    this.snapshots.set(snapshot.snapshotId, snapshot);
    this.idempotency.set(idempotencyKey, snapshot);
    return snapshot;
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
function validateFillCommand(command: ConfirmedFillCommand): void {
  for (const value of [command.quantity, command.price, command.fee]) validateDecimal(value);
  if (!command.portfolioId || !command.securityId || !command.sourceRef || !command.actorId || !command.reason || !command.idempotencyKey) throw new Error('required fill field is missing');
  if (decimalToNumber(command.quantity) <= 0 || decimalToNumber(command.price) <= 0 || decimalToNumber(command.fee) < 0) throw new Error('fill quantity and price must be positive and fee cannot be negative');
  if (!Date.parse(command.occurredAt) || !Date.parse(command.availableAt) || new Date(command.availableAt) < new Date(command.occurredAt)) throw new Error('invalid fill event time');
}

function decimalToNumber(value: string): number {
  return Number(value);
}
function negateDecimal(value: string): string { return value.startsWith('-') ? value.slice(1) : `-${value}`; }

const decimalScale = 100_000_000n;
function decimalToScaled(value: string): bigint {
  const negative = value.startsWith('-'); const [whole, fraction = ''] = (negative ? value.slice(1) : value).split('.');
  const scaled = BigInt(whole) * decimalScale + BigInt((fraction + '00000000').slice(0, 8));
  return negative ? -scaled : scaled;
}
function scaledToDecimal(value: bigint): string {
  const negative = value < 0n; const absolute = negative ? -value : value; const whole = absolute / decimalScale; const fraction = (absolute % decimalScale).toString().padStart(8, '0').replace(/0+$/, '');
  return `${negative ? '-' : ''}${whole}${fraction ? `.${fraction}` : ''}`;
}
function addDecimal(left: string, right: string): string { return scaledToDecimal(decimalToScaled(left) + decimalToScaled(right)); }
function subtractDecimal(left: string, right: string): string { return scaledToDecimal(decimalToScaled(left) - decimalToScaled(right)); }
function multiplyDecimal(left: string, right: string): string { return scaledToDecimal((decimalToScaled(left) * decimalToScaled(right)) / decimalScale); }
function isNegative(value: string): boolean { return decimalToScaled(value) < 0n; }
function isZero(value: string): boolean { return decimalToScaled(value) === 0n; }

function sha256(value: object): string {
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}
