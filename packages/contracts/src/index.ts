/** Stage 01 contract marker. OpenAPI/AsyncAPI sources are introduced in 01-03. */
export interface CorrelationContext { correlationId: string; causationId?: string; }
export type { DomainEventEnvelope } from './generated/domain-event-envelope.js';
export {
  GeneratedMarketDataClient,
  type FetchLike,
  type FetchResponse,
  type MarketDataClient,
  type MarketDataPrice,
} from './generated/market-data-client.js';
export { InMemoryInbox } from './messaging.js';
export type { OutboxWriter, Transaction, UnitOfWork } from './messaging.js';
