import { AgentRunner, type AgentDefinition, type AgentRun, type ArtifactRef } from './agent-kernel.js';
import { InMemoryAgentRunRepository, type AgentRunRepository } from './agent-run-repository.js';
import { financialNewsDefinition } from '../agents/financial-news-agent/definition.js';
import type { FinancialNewsAgentInput } from '../agents/financial-news-agent/input.schema.js';
import { marketMonitorDefinition } from '../agents/market-monitor-agent/definition.js';
import type { MarketMonitorAgentInput } from '../agents/market-monitor-agent/input.schema.js';
import { marketStateDefinition } from '../agents/market-state-agent/definition.js';
import type { MarketStateAgentInput } from '../agents/market-state-agent/input.schema.js';
import { stockAnalysisDefinition } from '../agents/stock-analysis-agent/definition.js';
import type { StockAnalysisAgentInput } from '../agents/stock-analysis-agent/input.schema.js';

export interface SpecialistCommand<TInput> {
  correlationId: string;
  input: TInput;
  inputArtifacts?: readonly ArtifactRef[];
}

export class SpecialistEntrypoints {
  public constructor(private readonly repository: AgentRunRepository = new InMemoryAgentRunRepository()) {}
  private readonly runner = new AgentRunner();

  public async stockAnalysis(command: SpecialistCommand<StockAnalysisAgentInput>): Promise<AgentRun<unknown>> {
    return await this.execute(command, stockAnalysisDefinition);
  }

  public async financialNews(command: SpecialistCommand<FinancialNewsAgentInput>): Promise<AgentRun<unknown>> {
    return await this.execute(command, financialNewsDefinition);
  }

  public async marketMonitor(command: SpecialistCommand<MarketMonitorAgentInput>): Promise<AgentRun<unknown>> {
    return await this.execute(command, marketMonitorDefinition);
  }

  public async marketState(command: SpecialistCommand<MarketStateAgentInput>): Promise<AgentRun<unknown>> {
    return await this.execute(command, marketStateDefinition);
  }

  public async get(correlationId: string): Promise<AgentRun<unknown> | undefined> {
    return await this.repository.get(correlationId);
  }

  private async execute<TInput, TOutput>(
    command: SpecialistCommand<TInput>,
    definition: AgentDefinition<TInput, TOutput>,
  ): Promise<AgentRun<TOutput>> {
    const existing = await this.repository.get(command.correlationId);
    if (existing) return existing as AgentRun<TOutput>;
    const run = await this.runner.run(definition, command.input, {
      correlationId: command.correlationId,
      inputArtifacts: command.inputArtifacts ?? [],
    });
    await this.repository.save(run);
    return run;
  }
}
