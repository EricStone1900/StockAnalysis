import { createHash } from 'node:crypto';
import type { ResourceReservation, ResourceReservationRequest, ResourceReservationStatus } from '@stock/contracts';
import type { PortfolioSnapshot } from './portfolio.js';

const scale = 100_000_000n;
function value(input: string): bigint { if (!/^\d+(?:\.\d{1,8})?$/.test(input)) throw new Error('invalid reservation decimal'); const [whole, fraction = ''] = input.split('.'); return BigInt(whole) * scale + BigInt(fraction.padEnd(8, '0')); }
function text(input: bigint): string { const whole = input / scale; const fraction = (input % scale).toString().padStart(8, '0').replace(/0+$/, ''); return `${whole}${fraction ? `.${fraction}` : ''}`; }
function hash(request: ResourceReservationRequest): string { return createHash('sha256').update(JSON.stringify({ ...request, idempotencyKey: undefined })).digest('hex'); }

export interface StoredResourceReservation extends ResourceReservation { readonly requestHash: string; readonly request: ResourceReservationRequest; }

export function reserveResources(snapshot: PortfolioSnapshot, active: readonly StoredResourceReservation[], request: ResourceReservationRequest): StoredResourceReservation {
  if (!request.reservationId || !request.portfolioId || !request.decisionId || !request.riskEvaluationId || !request.riskPolicyVersion || !/^[a-f0-9]{64}$/.test(request.executionContentHash) || request.proposalVersion < 1 || request.ledgerVersion < 1 || request.legs.length === 0) throw new Error('invalid resource reservation request');
  if (snapshot.portfolioId !== request.portfolioId || snapshot.ledgerVersion !== request.ledgerVersion) throw new Error('portfolio version conflict');
  if (active.some((item) => item.status !== 'RELEASED' && item.status !== 'SETTLED')) throw new Error('portfolio already has an active resource reservation');
  const reservedSells: Record<string, bigint> = {};
  let reservedCash = value(request.feeBuffer);
  if (reservedCash < 0n) throw new Error('invalid reservation decimal');
  for (const leg of request.legs) {
    if (!leg.legId || !leg.securityId || !['BUY', 'SELL'].includes(leg.side)) throw new Error('invalid reservation leg');
    const quantity = value(leg.quantity); const price = value(leg.limitPrice);
    if (quantity <= 0n || price <= 0n) throw new Error('invalid reservation leg');
    if (leg.side === 'BUY') reservedCash += (quantity * price) / scale;
    else reservedSells[leg.securityId] = (reservedSells[leg.securityId] ?? 0n) + quantity;
  }
  if (reservedCash > value(snapshot.cash)) throw new Error('insufficient available cash');
  const positions = new Map(snapshot.positions.map((position) => [position.securityId, value(position.availableQuantity)]));
  for (const [securityId, quantity] of Object.entries(reservedSells)) if (quantity > (positions.get(securityId) ?? 0n)) throw new Error('insufficient available sell quantity');
  return { reservationId: request.reservationId, portfolioId: request.portfolioId, ledgerVersion: request.ledgerVersion, decisionId: request.decisionId, proposalVersion: request.proposalVersion, riskEvaluationId: request.riskEvaluationId, riskPolicyVersion: request.riskPolicyVersion, executionContentHash: request.executionContentHash, reservedCash: text(reservedCash), reservedSells: Object.fromEntries(Object.entries(reservedSells).map(([id, quantity]) => [id, text(quantity)])), status: 'RESERVED', requestHash: hash(request), request };
}

export function transitionReservation(reservation: StoredResourceReservation, next: ResourceReservationStatus): StoredResourceReservation {
  const allowed: Record<ResourceReservationStatus, readonly ResourceReservationStatus[]> = { RESERVED: ['DISPATCHING', 'RELEASED'], DISPATCHING: ['IN_FLIGHT', 'UNKNOWN', 'RELEASED'], IN_FLIGHT: ['UNKNOWN', 'SETTLED'], UNKNOWN: ['IN_FLIGHT', 'SETTLED'], SETTLED: [], RELEASED: [] };
  if (!allowed[reservation.status].includes(next)) throw new Error('invalid resource reservation transition');
  return { ...reservation, status: next };
}
