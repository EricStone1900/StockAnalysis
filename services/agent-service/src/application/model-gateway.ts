export interface ModelCapabilities { structuredOutput: boolean; toolCalling: boolean; maxContextTokens: number; }
export interface CanonicalModelRequest { prompt: string; requireStructuredOutput: boolean; requireToolCalling: boolean; maxCostUsd: number; }
export interface CanonicalModelResponse { text: string; inputTokens: number; outputTokens: number; costUsd: number; }
export interface ModelProvider { id: string; capabilities(): ModelCapabilities; invoke(request: CanonicalModelRequest): Promise<CanonicalModelResponse>; }
export interface ModelProfile { id: string; providers: readonly string[]; }
export interface RoutedModelRun { modelRunId: string; providerId: string; response: CanonicalModelResponse; }

export class ModelGateway {
  public constructor(private readonly providers: readonly ModelProvider[]) {}

  public async invoke(profile: ModelProfile, request: CanonicalModelRequest): Promise<RoutedModelRun> {
    const errors: string[] = [];
    for (const providerId of profile.providers) {
      const provider = this.providers.find((candidate) => candidate.id === providerId);
      if (!provider || !supports(provider.capabilities(), request)) { errors.push(`${providerId}:unsupported`); continue; }
      try {
        const response = await provider.invoke(request);
        if (response.costUsd > request.maxCostUsd) { errors.push(`${providerId}:budget`); continue; }
        return { modelRunId: `model-run:${provider.id}:${crypto.randomUUID()}`, providerId: provider.id, response };
      } catch (error) { errors.push(`${providerId}:${error instanceof Error ? error.message : 'failed'}`); }
    }
    throw new Error(`all model providers failed: ${errors.join(',')}`);
  }
}

function supports(capabilities: ModelCapabilities, request: CanonicalModelRequest): boolean {
  return (!request.requireStructuredOutput || capabilities.structuredOutput) && (!request.requireToolCalling || capabilities.toolCalling);
}

export class FakeModelProvider implements ModelProvider {
  public constructor(public readonly id: string, private readonly value: CanonicalModelResponse, private readonly featureSet: ModelCapabilities, private readonly failure?: Error) {}
  public capabilities(): ModelCapabilities { return this.featureSet; }
  public async invoke(): Promise<CanonicalModelResponse> { if (this.failure) throw this.failure; return this.value; }
}
