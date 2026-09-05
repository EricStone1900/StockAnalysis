import { describe, expect, it } from 'vitest';
import { fetchDashboard } from './dashboard-client.js';

const response = (status: number, body: unknown): Response => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

describe('dashboard query', () => {
  it('maps downstream failures to explicit UI states', async () => {
    expect((await fetchDashboard(async () => response(403, {}), 1)).status).toBe('FORBIDDEN');
    expect((await fetchDashboard(async () => response(503, {}), 1)).status).toBe('UNAVAILABLE');
    expect((await fetchDashboard(async () => { throw new Error('offline'); }, 1)).status).toBe('UNAVAILABLE');
  });

  it('marks stale data without replacing it with an empty object', async () => {
    const result = await fetchDashboard(async () => response(200, { dataVersion: { status: 'STALE' }, dailyAnalysisSnapshot: { status: 'UNAVAILABLE' }, services: {} }), 1);
    expect(result.status).toBe('STALE');
    expect(result.data?.dataVersion.status).toBe('STALE');
  });
});
