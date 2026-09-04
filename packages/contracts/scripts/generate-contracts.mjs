import { readFile, writeFile } from 'node:fs/promises';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new globalThis.URL('../', import.meta.url));
const schema = JSON.parse(await readFile(`${root}schemas/domain-event-envelope.schema.json`, 'utf8'));
const required = new Set(schema.required);
const fields = Object.keys(schema.properties).map((name) => `  ${name}${required.has(name) ? '' : '?'}: ${name === 'schemaVersion' ? 'number' : name === 'payload' ? 'Record<string, unknown>' : 'string'};`).join('\n');
const ts = `// Generated from schemas/domain-event-envelope.schema.json. Do not edit.\nexport interface DomainEventEnvelope {\n${fields}\n}\n`;
const python = `# Generated from schemas/domain-event-envelope.schema.json. Do not edit.\nfrom typing import Any\nfrom pydantic import BaseModel\n\nclass DomainEventEnvelope(BaseModel):\n${Object.keys(schema.properties).map((name) => `    ${name}: ${name === 'schemaVersion' ? 'int' : name === 'payload' ? 'dict[str, Any]' : 'str'}${required.has(name) ? '' : ' | None = None'}`).join('\n')}\n`;
const marketDataClient = `// Generated from packages/contracts/openapi/market-data.v1.yaml. Do not edit.\nexport interface MarketDataPrice {\n  securityId: string;\n  close: string;\n  asOf: string;\n  dataVersion: string;\n}\n\nexport interface MarketDataVersion {\n  versionId: string;\n  status: string;\n  availableAt: string;\n}\n\nexport interface FetchResponse {\n  ok: boolean;\n  status: number;\n  json(): Promise<unknown>;\n}\n\nexport type FetchLike = (input: URL, init?: { method?: string }) => Promise<FetchResponse>;\n\nexport interface MarketDataClient {\n  getLatestDataVersion(): Promise<MarketDataVersion>;\n  getPrice(symbol: string, dataVersion: string, asOf: string): Promise<MarketDataPrice>;\n}\n\nexport class GeneratedMarketDataClient implements MarketDataClient {\n  public constructor(private readonly baseUrl: string, private readonly fetchImpl: FetchLike = globalThis.fetch as unknown as FetchLike) {}\n\n  public async getLatestDataVersion(): Promise<MarketDataVersion> {\n    const response = await this.fetchImpl(new URL('/api/v1/data-versions/latest', this.baseUrl), { method: 'GET' });\n    if (!response.ok) throw new Error(\`market-data request failed: \${response.status}\`);\n    return await response.json() as MarketDataVersion;\n  }\n\n  public async getPrice(symbol: string, dataVersion: string, asOf: string): Promise<MarketDataPrice> {\n    const url = new URL(\`/api/v1/prices/\${encodeURIComponent(symbol)}\`, this.baseUrl);\n    url.searchParams.set('dataVersion', dataVersion);\n    url.searchParams.set('asOf', asOf);\n    const response = await this.fetchImpl(url, { method: 'GET' });\n    if (!response.ok) throw new Error(\`market-data request failed: \${response.status}\`);\n    return await response.json() as MarketDataPrice;\n  }\n}\n`;
const outputs = [
  [`${root}src/generated/domain-event-envelope.ts`, ts],
  [`${root}src/generated/market-data-client.ts`, marketDataClient],
  [`${root}generated/domain_event_envelope.py`, python],
];
const check = process.argv.includes('--check');
for (const [path, content] of outputs) {
  const existing = await readFile(path, 'utf8').catch(() => '');
  if (check && existing !== content) throw new Error(`Generated contract drift: ${path}`);
  if (!check) await writeFile(path, content);
}
