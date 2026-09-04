import { describe, expect, it } from 'vitest';
import { GeneratedMarketDataClient } from '../src/index.js';

describe('生成的 market-data Client', () => {
  it('按契约发送版本和估值时点参数', async () => {
    let requested: URL | undefined;
    const client = new GeneratedMarketDataClient('http://market-data:3000', async (input) => {
      requested = input;
      return { ok: true, status: 200, json: async () => ({ securityId: 'SSE:600000', close: '12.34', asOf: '2026-09-01', dataVersion: 'v1' }) };
    });

    await expect(client.getPrice('SSE:600000', 'v1', '2026-09-01')).resolves.toMatchObject({ close: '12.34' });
    expect(requested?.pathname).toBe('/api/v1/prices/SSE%3A600000');
    expect(requested?.searchParams.get('dataVersion')).toBe('v1');
    expect(requested?.searchParams.get('asOf')).toBe('2026-09-01');
  });

  it('将非成功响应转换为可诊断错误', async () => {
    const client = new GeneratedMarketDataClient('http://market-data:3000', async () => ({ ok: false, status: 404, json: async () => ({}) }));
    await expect(client.getPrice('SSE:600000', 'v1', '2026-09-01')).rejects.toThrow('market-data request failed: 404');
  });
});
