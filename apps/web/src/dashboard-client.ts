import type { DashboardData } from './dashboard.js';

export interface DashboardQueryResult {
  data?: DashboardData;
  status: 'OK' | 'UNAVAILABLE' | 'FORBIDDEN' | 'STALE';
  error?: string;
  fetchedAt: number;
}

export const mockDashboard: DashboardData = {
  dataVersion: { status: 'OK', data: { versionId: 'mock-dv-1', status: 'READY' }, asOf: '2026-09-04T00:00:00Z' },
  dailyAnalysisSnapshot: { status: 'UNAVAILABLE', errorCode: 'MOCK_NOT_CONFIGURED' },
  services: { 'market-data-service': { status: 'OK', data: { status: 'UP' } } },
};

export async function fetchDashboard(fetchImpl: typeof fetch = fetch, now = Date.now()): Promise<DashboardQueryResult> {
  try {
    // 本地开发身份仅用于阶段07的只读页面验证；生产认证由BFF/网关提供。
    const response = await fetchImpl('/api/v1/dashboard', {
      headers: { 'x-actor-id': 'web-user', 'x-roles': 'RESEARCH_READ' },
    });
    if (response.status === 403) return { status: 'FORBIDDEN', error: '没有访问权限', fetchedAt: now };
    if (!response.ok) return { status: 'UNAVAILABLE', error: `Dashboard 请求失败：${response.status}`, fetchedAt: now };
    const data = await response.json() as DashboardData;
    const status = data.dataVersion.status === 'STALE' ? 'STALE' : 'OK';
    return { data, status, fetchedAt: now };
  } catch {
    return { status: 'UNAVAILABLE', error: 'Dashboard 服务暂时不可用', fetchedAt: now };
  }
}

export async function fetchConfiguredDashboard(fetchImpl: typeof fetch = fetch): Promise<DashboardQueryResult> {
  if (import.meta.env?.VITE_USE_MOCK_API === 'true') return { data: mockDashboard, status: 'OK', fetchedAt: Date.now() };
  return await fetchDashboard(fetchImpl);
}

export async function checkCompatibility(fetchImpl: typeof fetch = fetch): Promise<boolean> {
  try {
    const response = await fetchImpl('/api/v1/compatibility', { headers: { 'x-client-version': 'v1' } });
    if (!response.ok) return false;
    return (await response.json() as { compatible?: boolean }).compatible === true;
  } catch {
    return false;
  }
}
