import { describe, expect, it } from 'vitest';

import { DashboardFacade } from '../../src/application/dashboard-facade.js';

const principal = { actorId: 'user-1', roles: ['RESEARCH_READ'] };
const dataVersion = { versionId: 'dv-1', status: 'READY', availableAt: '2026-09-04T00:00:00Z' };

describe('DashboardFacade', () => {
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
});
