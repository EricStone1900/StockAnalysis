export type DependencyStatus = 'OK' | 'STALE' | 'UNAVAILABLE' | 'FORBIDDEN';

export interface PartialResult<T> {
  data?: T;
  status: DependencyStatus;
  asOf?: string;
  errorCode?: string;
}

export interface DashboardData {
  dataVersion: PartialResult<{ versionId: string; status: string }>;
  dailyAnalysisSnapshot: PartialResult<never>;
  agents: PartialResult<{ availableAgents: readonly string[]; mode: 'fast' | 'unavailable' }>;
  services: Record<string, PartialResult<{ status: 'UP' }>>;
}

export function statusLabel(status: DependencyStatus): string {
  return { OK: '正常', STALE: '已过期', UNAVAILABLE: '不可用', FORBIDDEN: '无权限' }[status];
}
