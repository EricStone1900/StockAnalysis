import { describe, expect, it, vi } from 'vitest';
import { HttpResourceReservationReader } from '../../src/application/resource-reservation-reader.js';

describe('HttpResourceReservationReader', () => {
  it('使用组合服务身份读取资源占用', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ reservationId: 'resource-1', status: 'DISPATCHING' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(new HttpResourceReservationReader('http://portfolio:3000/', 'portfolio-token').get('resource/1')).resolves.toMatchObject({ reservationId: 'resource-1' });
    expect(fetchMock).toHaveBeenCalledWith('http://portfolio:3000/internal/v1/portfolio-reservations/resource%2F1', { headers: { 'x-service-token': 'portfolio-token', accept: 'application/json' } });
    vi.unstubAllGlobals();
  });

  it('缺少服务身份或上游拒绝时失败关闭', async () => {
    await expect(new HttpResourceReservationReader('', '').get('resource-1')).rejects.toThrow('not configured');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 403 })));
    await expect(new HttpResourceReservationReader('http://portfolio:3000', 'wrong-token').get('resource-1')).rejects.toThrow('returned 403');
    vi.unstubAllGlobals();
  });
});
