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
  dailyAnalysisSnapshot: PartialResult<unknown>;
  agents: PartialResult<{ availableAgents: readonly string[]; mode: 'fast' | 'unavailable' }>;
  services: Record<string, PartialResult<{ status: 'UP' }>>;
}

export interface AgentRunResponse {
  runId: string;
  definitionId: string;
  correlationId: string;
  modelRun: { provider: string; modelId: string; promptVersion: string };
  toolCalls: readonly unknown[];
  output: unknown;
}

export class DashboardFacade {
  public constructor(
    private readonly marketData: MarketDataClient,
    private readonly agentServiceUrl = 'http://localhost:3010',
    private readonly quantResearchServiceUrl = 'http://localhost:8000',
  ) {}

  public async latest(principal: Principal): Promise<DashboardResponse> {
    if (!principal.roles.includes('RESEARCH_READ')) {
      return { dataVersion: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, dailyAnalysisSnapshot: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, agents: { status: 'FORBIDDEN', errorCode: 'RBAC_DENIED' }, services: {} };
    }
    const dataVersion = await this.latestDataVersion();
    const dailyAnalysisSnapshot = await this.latestDailyAnalysisSnapshot();
    const agents = await this.agentDirectory();
    return {
      dataVersion,
      dailyAnalysisSnapshot,
      agents,
      services: {
        'market-data-service': { status: dataVersion.status === 'OK' ? 'OK' : 'UNAVAILABLE' },
        'agent-service': { status: agents.status === 'OK' ? 'OK' : 'UNAVAILABLE' },
      },
    };
  }

  public async agentRun(correlationId: string, principal: Principal): Promise<AgentRunResponse | undefined> {
    if (!principal.roles.includes('RESEARCH_READ')) return undefined;
    try {
      const response = await fetch(new URL(`/internal/v1/agent-runs/${encodeURIComponent(correlationId)}`, this.agentServiceUrl));
      if (response.status === 404) return undefined;
      if (!response.ok) throw new Error(`agent service request failed: ${response.status}`);
      return await response.json() as AgentRunResponse;
    } catch {
      return undefined;
    }
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

  private async latestDailyAnalysisSnapshot(): Promise<PartialResult<unknown>> {
    try {
      const response = await fetch(new URL('/api/v1/daily-analysis-snapshots/latest', this.quantResearchServiceUrl));
      if (response.status === 404) return { status: 'UNAVAILABLE', errorCode: 'DAILY_ANALYSIS_NOT_READY' };
      if (!response.ok) return { status: 'UNAVAILABLE', errorCode: 'QUANT_RESEARCH_UNAVAILABLE' };
      const data = await response.json() as { as_of_date?: string; is_stale?: boolean };
      return { data, status: data.is_stale ? 'STALE' : 'OK', asOf: data.as_of_date };
    } catch {
      return { status: 'UNAVAILABLE', errorCode: 'QUANT_RESEARCH_UNAVAILABLE' };
    }
  }
}
