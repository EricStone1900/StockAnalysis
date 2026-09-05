import { afterEach, describe, expect, it, vi } from 'vitest';

import { DashboardFacade } from '../../src/application/dashboard-facade.js';

const principal = { actorId: 'user-1', roles: ['RESEARCH_READ'] };
const dataVersion = { versionId: 'dv-1', status: 'READY', availableAt: '2026-09-04T00:00:00Z' };

describe('DashboardFacade', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('returns an explicit partial result when a downstream dependency fails', async () => {
    const facade = new DashboardFacade({ getLatestDataVersion: async () => { throw new Error('timeout'); }, getPrice: async () => { throw new Error('unused'); } });
    const result = await facade.latest(principal);
    expect(result.dataVersion).toEqual({ status: 'UNAVAILABLE', errorCode: 'MARKET_DATA_UNAVAILABLE' });
    expect(result.dailyAnalysisSnapshot.status).toBe('UNAVAILABLE');
  });

  it('denies aggregation to a principal without read permission', async () => {
    const facade = new DashboardFacade({ getLatestDataVersion: async () => dataVersion, getPrice: async () => { throw new Error('unused'); } });
    const result = await facade.latest({ actorId: 'user-2', roles: [] });
    expect(result.dataVersion.status).toBe('FORBIDDEN');
  });

  it('reads the latest daily analysis snapshot through the quant service', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: URL | string) => {
      if (String(input) === 'http://quant.test/api/v1/daily-analysis-snapshots/latest') return new Response(JSON.stringify({ snapshot_id: 'daily-1', as_of_date: '2026-09-05', is_stale: false }), { status: 200 });
      expect(String(input)).toBe('http://agent.test/version');
      return new Response(JSON.stringify({ service: 'agent-service', version: '0.1.0' }), { status: 200 });
    }));
    const facade = new DashboardFacade({ getLatestDataVersion: async () => dataVersion, getPrice: async () => { throw new Error('unused'); } }, 'http://agent.test', 'http://quant.test');
    const result = await facade.latest(principal);
    expect(result.dailyAnalysisSnapshot).toEqual({ status: 'OK', asOf: '2026-09-05', data: { snapshot_id: 'daily-1', as_of_date: '2026-09-05', is_stale: false } });
  });
});
