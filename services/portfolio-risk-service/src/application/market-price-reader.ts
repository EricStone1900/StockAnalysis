import type { PricePoint } from '../domain/valuation.js';

/** 对应 market-data.v1.yaml 的价格查询契约；仅允许由生成 Client 的适配器实现。 */
export interface MarketPriceReader {
  readPrices(input: { securityIds: readonly string[]; marketDataVersion: string; asOf: string }): Promise<readonly PricePoint[]>;
}
