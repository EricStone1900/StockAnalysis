import type { ResourceReservation } from '@stock/contracts';

export interface ResourceReservationReader { get(reservationId: string): Promise<ResourceReservation | undefined>; }

/** 组合服务读取适配器；未配置地址或服务身份时显式不可用。 */
export class HttpResourceReservationReader implements ResourceReservationReader {
  constructor(private readonly baseUrl: string, private readonly serviceToken: string) {}
  async get(reservationId: string): Promise<ResourceReservation | undefined> {
    if (!this.baseUrl || !this.serviceToken) throw new Error('portfolio resource reader is not configured');
    const response = await fetch(`${this.baseUrl.replace(/\/$/, '')}/internal/v1/portfolio-reservations/${encodeURIComponent(reservationId)}`, { headers: { 'x-service-token': this.serviceToken, accept: 'application/json' } });
    if (response.status === 404) return undefined;
    if (!response.ok) throw new Error(`portfolio resource reader returned ${response.status}`);
    return await response.json() as ResourceReservation;
  }
}
