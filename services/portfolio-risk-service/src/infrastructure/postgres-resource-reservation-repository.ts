import type { Pool, PoolClient } from 'pg';
import { randomUUID } from 'node:crypto';
import type { ResourceReservationRequest, ResourceReservationStatus } from '@stock/contracts';
import type { PortfolioSnapshot } from '../domain/portfolio.js';
import { transitionReservation, type StoredResourceReservation } from '../domain/resource-reservation.js';
import type { ResourceReservationRepository } from '../application/resource-reservation-service.js';

export class PostgresResourceReservationRepository implements ResourceReservationRepository {
  constructor(private readonly pool: Pool) {}
  async reserve(request: ResourceReservationRequest, calculate: (snapshot: PortfolioSnapshot, active: readonly StoredResourceReservation[]) => StoredResourceReservation): Promise<StoredResourceReservation> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      await client.query("SELECT pg_advisory_xact_lock(hashtext('portfolio-resource:' || $1))", [request.portfolioId]);
      const repeated = await this.findByIdempotency(client, request.portfolioId, request.idempotencyKey);
      if (repeated) {
        const candidate = calculate(await this.lockSnapshot(client, request.portfolioId), []);
        if (candidate.requestHash !== repeated.requestHash) throw new Error('idempotency payload conflict');
        await client.query('COMMIT'); return repeated;
      }
      const snapshot = await this.lockSnapshot(client, request.portfolioId);
      const active = await this.active(client, request.portfolioId);
      const reservation = calculate(snapshot, active);
      await client.query(`INSERT INTO portfolio_resource_reservations (reservation_id, portfolio_id, ledger_version, decision_id, proposal_version, risk_evaluation_id, risk_policy_version, execution_content_hash, reserved_cash, reserved_sells, status, request_hash, idempotency_key, payload) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11,$12,$13,$14::jsonb)`, [reservation.reservationId, reservation.portfolioId, reservation.ledgerVersion, request.decisionId, request.proposalVersion, request.riskEvaluationId, request.riskPolicyVersion, reservation.executionContentHash, reservation.reservedCash, JSON.stringify(reservation.reservedSells), reservation.status, reservation.requestHash, request.idempotencyKey, JSON.stringify(reservation)]);
      await this.appendOutboxEvent(client, reservation, 'created');
      await client.query('COMMIT'); return reservation;
    } catch (error) { await client.query('ROLLBACK'); throw error; } finally { client.release(); }
  }
  async transition(reservationId: string, status: ResourceReservationStatus): Promise<StoredResourceReservation> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const identified = await client.query<{ portfolio_id: string }>('SELECT portfolio_id FROM portfolio_resource_reservations WHERE reservation_id = $1', [reservationId]);
      const portfolioId = identified.rows[0]?.portfolio_id; if (!portfolioId) throw new Error('resource reservation not found');
      await client.query("SELECT pg_advisory_xact_lock(hashtext('portfolio-resource:' || $1))", [portfolioId]);
      const result = await client.query<{ payload: StoredResourceReservation }>('SELECT payload FROM portfolio_resource_reservations WHERE reservation_id = $1 FOR UPDATE', [reservationId]);
      const current = result.rows[0]?.payload; if (!current) throw new Error('resource reservation not found');
      const next = transitionReservation(current, status);
      await client.query('UPDATE portfolio_resource_reservations SET status = $1, payload = $2::jsonb, updated_at = now() WHERE reservation_id = $3', [next.status, JSON.stringify(next), reservationId]);
      await this.appendOutboxEvent(client, next, 'status-changed');
      await client.query('COMMIT'); return next;
    } catch (error) { await client.query('ROLLBACK'); throw error; } finally { client.release(); }
  }
  async get(reservationId: string): Promise<StoredResourceReservation | undefined> { const result = await this.pool.query<{ payload: StoredResourceReservation }>('SELECT payload FROM portfolio_resource_reservations WHERE reservation_id = $1', [reservationId]); return result.rows[0]?.payload; }
  private async lockSnapshot(client: PoolClient, portfolioId: string): Promise<PortfolioSnapshot> { const result = await client.query<{ payload: PortfolioSnapshot }>('SELECT payload FROM portfolio_snapshots WHERE portfolio_id = $1 ORDER BY ledger_version DESC LIMIT 1 FOR UPDATE', [portfolioId]); const snapshot = result.rows[0]?.payload; if (!snapshot) throw new Error('portfolio snapshot not found'); return snapshot; }
  private async active(client: PoolClient, portfolioId: string): Promise<StoredResourceReservation[]> { const result = await client.query<{ payload: StoredResourceReservation }>("SELECT payload FROM portfolio_resource_reservations WHERE portfolio_id = $1 AND status NOT IN ('SETTLED', 'RELEASED') FOR UPDATE", [portfolioId]); return result.rows.map((row) => row.payload); }
  private async findByIdempotency(client: PoolClient, portfolioId: string, key: string): Promise<StoredResourceReservation | undefined> { const result = await client.query<{ payload: StoredResourceReservation }>('SELECT payload FROM portfolio_resource_reservations WHERE portfolio_id = $1 AND idempotency_key = $2', [portfolioId, key]); return result.rows[0]?.payload; }
  private async appendOutboxEvent(client: PoolClient, reservation: StoredResourceReservation, action: 'created' | 'status-changed'): Promise<void> {
    const occurredAt = new Date().toISOString();
    const event = { eventId: randomUUID(), subject: `stock.portfolio-risk.resource-reservation.${action}.v1`, schemaVersion: 1, occurredAt, availableAt: occurredAt, producer: 'portfolio-risk-service', correlationId: reservation.request.decisionId, payload: { reservation } };
    await client.query('INSERT INTO portfolio_outbox_events (event_id, subject, aggregate_id, payload, available_at) VALUES ($1, $2, $3, $4::jsonb, $5)', [event.eventId, event.subject, reservation.portfolioId, JSON.stringify(event), occurredAt]);
  }
}
