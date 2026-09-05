import type { AgentRun } from './agent-kernel.js';

export interface AgentRunRepository { get(correlationId: string): AgentRun<{ summary: string }> | undefined; save(run: AgentRun<{ summary: string }>): void; }

export class InMemoryAgentRunRepository implements AgentRunRepository {
  private readonly runs = new Map<string, AgentRun<{ summary: string }>>();
  public get(correlationId: string): AgentRun<{ summary: string }> | undefined { return this.runs.get(correlationId); }
  public save(run: AgentRun<{ summary: string }>): void { this.runs.set(run.correlationId, structuredClone(run)); }
}
