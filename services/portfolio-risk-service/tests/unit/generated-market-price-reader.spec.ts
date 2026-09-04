import { describe, expect, it } from 'vitest';
import { GeneratedMarketPriceReader } from '../../src/application/generated-market-price-reader.js';

describe('GeneratedMarketPriceReader', () => {
  it('把生成 Client 的价格响应映射为估值端口', async () => {
    const reader = new GeneratedMarketPriceReader({
      getPrice: async (symbol, dataVersion, asOf) => ({ securityId: symbol, close: '12.34', dataVersion, asOf }),
    });
    await expect(reader.readPrices({ securityIds: ['SSE:600000'], marketDataVersion: 'v1', asOf: '2026-09-01' })).resolves.toEqual([
      { securityId: 'SSE:600000', close: '12.34', asOf: '2026-09-01' },
    ]);
  });

  it('拒绝跨版本或错误证券的响应', async () => {
    const reader = new GeneratedMarketPriceReader({
      getPrice: async () => ({ securityId: 'SSE:600001', close: '12.34', dataVersion: 'other', asOf: '2026-09-01' }),
    });
    await expect(reader.readPrices({ securityIds: ['SSE:600000'], marketDataVersion: 'v1', asOf: '2026-09-01' })).rejects.toThrow('identity mismatch');
  });
});
