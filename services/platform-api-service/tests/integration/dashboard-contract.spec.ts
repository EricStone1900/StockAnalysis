import { describe, expect, it } from 'vitest';
import { GeneratedMarketDataClient } from '@stock/contracts';
import { DashboardFacade } from '../../src/application/dashboard-facade.js';

describe('platform dashboard contract integration', () => {
  it('uses the generated client and preserves DataVersion freshness', async () => {
    const client = new GeneratedMarketDataClient('http://market-data.test', async (url) => {
      expect(url.pathname).toBe('/api/v1/data-versions/latest');
      return { ok: true, status: 200, json: async () => ({ versionId: 'dv-1', status: 'READY', availableAt: '2026-09-04T00:00:00Z' }) };
    });
    const result = await new DashboardFacade(client).latest({ actorId: 'user-1', roles: ['RESEARCH_READ'] });
    expect(result.dataVersion.status).toBe('OK');
    expect(result.dataVersion.asOf).toBe('2026-09-04T00:00:00Z');
    expect(result.dailyAnalysisSnapshot.status).toBe('UNAVAILABLE');
  });
});
