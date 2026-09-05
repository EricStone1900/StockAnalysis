import { createHash } from 'node:crypto';
import { z, type ZodType } from 'zod';

export interface ToolDefinition<TInput = unknown, TOutput = unknown> { id: string; inputSchema: ZodType<TInput>; outputSchema: ZodType<TOutput>; timeoutMs: number; sideEffect: boolean; invoke(input: TInput): Promise<TOutput>; }
export interface ToolPolicy { agentId: string; allowedTools: readonly string[]; maxCalls: number; denySideEffects: boolean; }

export class ToolRegistry {
  public constructor(private readonly tools: readonly ToolDefinition[]) {}
  public async call(policy: ToolPolicy, toolId: string, input: unknown): Promise<unknown> {
    if (!policy.allowedTools.includes(toolId)) throw new Error('tool is not authorized');
    const tool = this.tools.find((candidate) => candidate.id === toolId);
    if (!tool) throw new Error('tool is not registered');
    if (policy.denySideEffects && tool.sideEffect) throw new Error('side-effect tool is denied');
    const parsedInput = tool.inputSchema.safeParse(input);
    if (!parsedInput.success) throw new Error('tool input validation failed');
    const output = await tool.invoke(parsedInput.data);
    const parsedOutput = tool.outputSchema.safeParse(output);
    if (!parsedOutput.success) throw new Error('tool output validation failed');
    return parsedOutput.data;
  }
}

export interface PromptDefinition { agentId: string; agentVersion: string; promptVersion: string; template: string; status: 'APPROVED' | 'DRAFT'; }
export class PromptRegistry {
  public constructor(private readonly prompts: readonly PromptDefinition[]) {}
  public get(agentId: string, agentVersion: string): PromptDefinition {
    const prompt = this.prompts.find((item) => item.agentId === agentId && item.agentVersion === agentVersion && item.status === 'APPROVED');
    if (!prompt) throw new Error('approved prompt not found');
    return prompt;
  }
  public templateHash(prompt: PromptDefinition): string { return createHash('sha256').update(prompt.template).digest('hex'); }
}

export interface ContextRef { id: string; freshness: 'FRESH' | 'STALE' | 'FUTURE' | 'UNRESOLVED'; untrusted: boolean; }
export function contextHash(refs: readonly ContextRef[]): string {
  if (refs.some((ref) => ref.freshness === 'FUTURE' || ref.freshness === 'UNRESOLVED')) throw new Error('context contains unresolved or future evidence');
  return createHash('sha256').update(JSON.stringify([...refs].sort((left, right) => left.id.localeCompare(right.id)))).digest('hex');
}

export class RunMemoryM0 {
  private readonly values = new Map<string, unknown>();
  public put(runId: string, value: unknown): void { this.values.set(runId, value); }
  public get(runId: string): unknown { return this.values.get(runId); }
  public clear(runId: string): void { this.values.delete(runId); }
}

export const stringTool = (id: string, sideEffect = false): ToolDefinition<{ value: string }, { value: string }> => ({ id, sideEffect, timeoutMs: 1_000, inputSchema: z.object({ value: z.string().min(1) }), outputSchema: z.object({ value: z.string().min(1) }), async invoke(input) { return input; } });
