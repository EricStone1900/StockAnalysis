import type { MarketDataClient, MarketDataVersion } from '@stock/contracts';

export type DependencyStatus = 'OK' | 'STALE' | 'UNAVAILABLE' | 'FORBIDDEN';

export interface PartialResult<T> {
  data?: T;
  status: DependencyStatus;
  asOf?: string;
  errorCode?: string;
}

export interface Principal {
  actorId: string;
  roles: readonly string[];
}

export interface DashboardResponse {
  dataVersion: PartialResult<MarketDataVersion>;
  dailyAnalysisSnapshot: PartialResult<never>;
  services: Record<string, PartialResult<{ status: 'UP' }>>;
}

export class DashboardFacade {
  public constructor(private readonly marketData: MarketDataClient) {}

  public async latest(principal: Principal): Promise<DashboardResponse> {
    if (!principal.roles.includes('RESEARCH_READ')) {
      return { dataVersion: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, dailyAnalysisSnapshot: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, services: {} };
    }
    const dataVersion = await this.latestDataVersion();
    return {
      dataVersion,
      dailyAnalysisSnapshot: { status: 'UNAVAILABLE', errorCode: 'GENERATED_CLIENT_NOT_AVAILABLE' },
      services: { 'market-data-service': { status: dataVersion.status === 'OK' ? 'OK' : 'UNAVAILABLE' } },
    };
  }

  private async latestDataVersion(): Promise<PartialResult<MarketDataVersion>> {
    try {
      const data = await this.marketData.getLatestDataVersion();
      return { data, status: 'OK', asOf: data.availableAt };
    } catch {
      return { status: 'UNAVAILABLE', errorCode: 'MARKET_DATA_UNAVAILABLE' };
    }
  }
}
