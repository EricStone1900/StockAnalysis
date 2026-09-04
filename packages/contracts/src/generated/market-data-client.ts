// Generated from packages/contracts/openapi/market-data.v1.yaml. Do not edit.
export interface MarketDataPrice {
  securityId: string;
  close: string;
  asOf: string;
  dataVersion: string;
}

export interface FetchResponse {
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}

export type FetchLike = (input: URL, init?: { method?: string }) => Promise<FetchResponse>;

export interface MarketDataClient {
  getPrice(symbol: string, dataVersion: string, asOf: string): Promise<MarketDataPrice>;
}

export class GeneratedMarketDataClient implements MarketDataClient {
  public constructor(private readonly baseUrl: string, private readonly fetchImpl: FetchLike = globalThis.fetch as unknown as FetchLike) {}

  public async getPrice(symbol: string, dataVersion: string, asOf: string): Promise<MarketDataPrice> {
    const url = new URL(`/api/v1/prices/${encodeURIComponent(symbol)}`, this.baseUrl);
    url.searchParams.set('dataVersion', dataVersion);
    url.searchParams.set('asOf', asOf);
    const response = await this.fetchImpl(url, { method: 'GET' });
    if (!response.ok) throw new Error(`market-data request failed: ${response.status}`);
    return await response.json() as MarketDataPrice;
  }
}
