import type { AgentRun } from './agent-kernel.js';

export interface AgentRunRepository { get(correlationId: string): Promise<AgentRun<{ summary: string }> | undefined>; save(run: AgentRun<{ summary: string }>): Promise<void>; }

export class InMemoryAgentRunRepository implements AgentRunRepository {
  private readonly runs = new Map<string, AgentRun<{ summary: string }>>();
  public async get(correlationId: string): Promise<AgentRun<{ summary: string }> | undefined> { return this.runs.get(correlationId); }
  public async save(run: AgentRun<{ summary: string }>): Promise<void> { this.runs.set(run.correlationId, structuredClone(run)); }
}
