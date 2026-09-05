import type { MarketDataClient, MarketDataVersion } from '@stock/contracts';
import type { Principal } from './security.js';

export type DependencyStatus = 'OK' | 'STALE' | 'UNAVAILABLE' | 'FORBIDDEN';

export interface PartialResult<T> {
  data?: T;
  status: DependencyStatus;
  asOf?: string;
  errorCode?: string;
}

export interface DashboardResponse {
  dataVersion: PartialResult<MarketDataVersion>;
  dailyAnalysisSnapshot: PartialResult<never>;
  agents: PartialResult<{ availableAgents: readonly string[]; mode: 'fast' | 'unavailable' }>;
  services: Record<string, PartialResult<{ status: 'UP' }>>;
}

export class DashboardFacade {
  public constructor(private readonly marketData: MarketDataClient, private readonly agentServiceUrl = 'http://localhost:3010') {}

  public async latest(principal: Principal): Promise<DashboardResponse> {
    if (!principal.roles.includes('RESEARCH_READ')) {
      return { dataVersion: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, dailyAnalysisSnapshot: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, agents: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, services: {} };
    }
    const dataVersion = await this.latestDataVersion();
    const agents = await this.agentDirectory();
    return {
      dataVersion,
      dailyAnalysisSnapshot: { status: 'UNAVAILABLE', errorCode: 'GENERATED_CLIENT_NOT_AVAILABLE' },
      agents,
      services: {
        'market-data-service': { status: dataVersion.status === 'OK' ? 'OK' : 'UNAVAILABLE' },
        'agent-service': { status: agents.status === 'OK' ? 'OK' : 'UNAVAILABLE' },
      },
    };
  }

  private async agentDirectory(): Promise<PartialResult<{ availableAgents: readonly string[]; mode: 'fast' | 'unavailable' }>> {
    try {
      const response = await fetch(new URL('/version', this.agentServiceUrl));
      if (!response.ok) return { status: 'UNAVAILABLE', errorCode: 'AGENT_SERVICE_UNAVAILABLE' };
      return {
        status: 'OK',
        data: {
          availableAgents: ['stock-analysis', 'financial-news', 'market-monitor', 'market-state'],
          mode: 'fast',
        },
        asOf: new Date().toISOString(),
      };
    } catch {
      return { status: 'UNAVAILABLE', errorCode: 'AGENT_SERVICE_UNAVAILABLE' };
    }
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
