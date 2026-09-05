import { AgentRunner, fakeAnalysisDefinition, type AgentRun } from './agent-kernel.js';

export interface FakeAnalysisCommand { correlationId: string; text: string; }

export class FakeAnalysisEntrypoints {
  private readonly completed = new Map<string, AgentRun<{ summary: string }>>();

  public async execute(command: FakeAnalysisCommand): Promise<AgentRun<{ summary: string }>> {
    const existing = this.completed.get(command.correlationId);
    if (existing) return existing;
    const result = await new AgentRunner().run(fakeAnalysisDefinition, { text: command.text }, { correlationId: command.correlationId, inputArtifacts: [] });
    this.completed.set(command.correlationId, result);
    return result;
  }

  public async consumeNats(command: FakeAnalysisCommand): Promise<AgentRun<{ summary: string }>> { return await this.execute(command); }
  public async temporalActivity(command: FakeAnalysisCommand): Promise<AgentRun<{ summary: string }>> { return await this.execute(command); }
}
