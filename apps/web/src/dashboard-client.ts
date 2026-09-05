import type { DashboardData } from './dashboard.js';

export interface DashboardQueryResult {
  data?: DashboardData;
  status: 'OK' | 'UNAVAILABLE' | 'FORBIDDEN' | 'STALE';
  error?: string;
  fetchedAt: number;
}

export async function fetchDashboard(fetchImpl: typeof fetch = fetch, now = Date.now()): Promise<DashboardQueryResult> {
  try {
    const response = await fetchImpl('/api/v1/dashboard', { headers: { 'x-roles': 'RESEARCH_READ' } });
    if (response.status === 403) return { status: 'FORBIDDEN', error: '没有访问权限', fetchedAt: now };
    if (!response.ok) return { status: 'UNAVAILABLE', error: `Dashboard 请求失败：${response.status}`, fetchedAt: now };
    const data = await response.json() as DashboardData;
    const status = data.dataVersion.status === 'STALE' ? 'STALE' : 'OK';
    return { data, status, fetchedAt: now };
  } catch {
    return { status: 'UNAVAILABLE', error: 'Dashboard 服务暂时不可用', fetchedAt: now };
  }
}
