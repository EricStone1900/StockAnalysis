import type { PricePoint } from '../domain/valuation.js';

/** 仅允许由 market-data OpenAPI 生成 Client 实现；禁止业务层手写跨服务 HTTP。 */
export interface MarketPriceReader {
  readPrices(input: { securityIds: readonly string[]; marketDataVersion: string; asOf: string }): Promise<readonly PricePoint[]>;
}
