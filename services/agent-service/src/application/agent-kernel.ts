import { z, type ZodType } from 'zod';

export interface ArtifactRef { uri: string; sha256: string; }
export interface AgentExecutionContext { correlationId: string; inputArtifacts: readonly ArtifactRef[]; }
export interface ToolCall { toolId: string; input: unknown; output: unknown; }
export interface ModelRun { provider: string; modelId: string; promptVersion: string; }
export interface AgentRun<TOutput> { runId: string; definitionId: string; correlationId: string; modelRun: ModelRun; toolCalls: readonly ToolCall[]; output: TOutput; }
export interface AgentDefinition<TInput, TOutput> {
  id: string;
  version: string;
  promptVersion: string;
  outputSchema: ZodType<TOutput>;
  maxToolCalls: number;
  invoke(input: TInput, context: AgentExecutionContext): Promise<{ output: unknown; toolCalls?: readonly ToolCall[] }>;
}

export class AgentRunner {
  public async run<TInput, TOutput>(definition: AgentDefinition<TInput, TOutput>, input: TInput, context: AgentExecutionContext): Promise<AgentRun<TOutput>> {
    const invocation = await definition.invoke(input, context);
    const toolCalls = invocation.toolCalls ?? [];
    if (toolCalls.length > definition.maxToolCalls) throw new Error('tool call budget exceeded');
    const parsed = definition.outputSchema.safeParse(invocation.output);
    if (!parsed.success) throw new Error(`structured output validation failed: ${parsed.error.issues[0]?.message ?? 'unknown error'}`);
    return { runId: `agent-run:${definition.id}:${context.correlationId}`, definitionId: `${definition.id}:${definition.version}`, correlationId: context.correlationId, modelRun: { provider: 'fake', modelId: 'fake-analysis-v1', promptVersion: definition.promptVersion }, toolCalls, output: parsed.data };
  }
}

export const fakeAnalysisDefinition: AgentDefinition<{ text: string }, { summary: string }> = {
  id: 'fake-analysis', version: 'v1', promptVersion: 'fake-prompt-v1', maxToolCalls: 1,
  outputSchema: z.object({ summary: z.string().min(1) }),
  async invoke(input) { return { output: { summary: `echo:${input.text}` }, toolCalls: [] }; },
};
