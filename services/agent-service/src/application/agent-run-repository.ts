import type { AgentRun } from './agent-kernel.js';

export interface AgentRunRepository { get(correlationId: string): Promise<AgentRun<unknown> | undefined>; save(run: AgentRun<unknown>): Promise<void>; }

export class InMemoryAgentRunRepository implements AgentRunRepository {
  private readonly runs = new Map<string, AgentRun<unknown>>();
  public async get(correlationId: string): Promise<AgentRun<unknown> | undefined> { return this.runs.get(correlationId); }
  public async save(run: AgentRun<unknown>): Promise<void> { this.runs.set(run.correlationId, structuredClone(run)); }
}
