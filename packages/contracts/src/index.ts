/** Stage 01 contract marker. OpenAPI/AsyncAPI sources are introduced in 01-03. */
export interface CorrelationContext { correlationId: string; causationId?: string; }
