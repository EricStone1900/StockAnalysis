import { AgentRunner, fakeAnalysisDefinition, type AgentRun } from './agent-kernel.js';
import { InMemoryAgentRunRepository, type AgentRunRepository } from './agent-run-repository.js';

export interface FakeAnalysisCommand { correlationId: string; text: string; }

export class FakeAnalysisEntrypoints {
  public constructor(private readonly repository: AgentRunRepository = new InMemoryAgentRunRepository()) {}

  public async execute(command: FakeAnalysisCommand): Promise<AgentRun<{ summary: string }>> {
    const existing = await this.repository.get(command.correlationId);
    if (existing) return existing as AgentRun<{ summary: string }>;
    const result = await new AgentRunner().run(fakeAnalysisDefinition, { text: command.text }, { correlationId: command.correlationId, inputArtifacts: [] });
    await this.repository.save(result);
    return result;
  }

  public async consumeNats(command: FakeAnalysisCommand): Promise<AgentRun<{ summary: string }>> { return await this.execute(command); }
  public async temporalActivity(command: FakeAnalysisCommand): Promise<AgentRun<{ summary: string }>> { return await this.execute(command); }

  public async get(correlationId: string): Promise<AgentRun<{ summary: string }> | undefined> {
    const run = await this.repository.get(correlationId);
    return run as AgentRun<{ summary: string }> | undefined;
  }
}
