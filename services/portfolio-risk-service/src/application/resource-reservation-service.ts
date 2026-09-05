import type { ResourceReservationRequest, ResourceReservationStatus } from '@stock/contracts';
import { reserveResources, transitionReservation, type StoredResourceReservation } from '../domain/resource-reservation.js';
import type { PortfolioSnapshot } from '../domain/portfolio.js';

export interface ResourceReservationRepository {
  reserve(request: ResourceReservationRequest, calculate: (snapshot: PortfolioSnapshot, active: readonly StoredResourceReservation[]) => StoredResourceReservation): Promise<StoredResourceReservation>;
  transition(reservationId: string, next: ResourceReservationStatus): Promise<StoredResourceReservation>;
  get(reservationId: string): Promise<StoredResourceReservation | undefined>;
}
export class ResourceReservationService {
  private readonly stored = new Map<string, StoredResourceReservation>();
  constructor(private readonly snapshots: { latest(portfolioId: string): Promise<PortfolioSnapshot | undefined> }, private readonly repository?: ResourceReservationRepository) {}
  async reserve(request: ResourceReservationRequest): Promise<StoredResourceReservation> {
    if (this.repository) return this.repository.reserve(request, (snapshot, active) => reserveResources(snapshot, active, request));
    const snapshot = await this.snapshots.latest(request.portfolioId); if (!snapshot) throw new Error('portfolio snapshot not found');
    const existing = this.stored.get(request.reservationId); if (existing) return existing;
    const reservation = reserveResources(snapshot, [...this.stored.values()], request); this.stored.set(request.reservationId, reservation); return reservation;
  }
  async transition(reservationId: string, status: ResourceReservationStatus): Promise<StoredResourceReservation> {
    if (this.repository) return this.repository.transition(reservationId, status);
    const current = this.stored.get(reservationId); if (!current) throw new Error('resource reservation not found'); const next = transitionReservation(current, status); this.stored.set(reservationId, next); return next;
  }
  async get(reservationId: string): Promise<StoredResourceReservation | undefined> { return this.repository?.get(reservationId) ?? this.stored.get(reservationId); }
}
