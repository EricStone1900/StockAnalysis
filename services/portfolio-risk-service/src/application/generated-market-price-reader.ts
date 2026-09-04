import type { MarketDataClient } from '@stock/contracts';
import type { MarketPriceReader } from './market-price-reader.js';

/** 将 contracts 包生成的 Client 适配为估值用的端口。 */
export class GeneratedMarketPriceReader implements MarketPriceReader {
  public constructor(private readonly client: MarketDataClient) {}

  public async readPrices(input: { securityIds: readonly string[]; marketDataVersion: string; asOf: string }) {
    return await Promise.all(input.securityIds.map(async (securityId) => {
      const point = await this.client.getPrice(securityId, input.marketDataVersion, input.asOf);
      if (point.securityId !== securityId || point.dataVersion !== input.marketDataVersion) {
        throw new Error(`market-data response identity mismatch for ${securityId}`);
      }
      return { securityId: point.securityId, close: point.close, asOf: point.asOf };
    }));
  }
}
