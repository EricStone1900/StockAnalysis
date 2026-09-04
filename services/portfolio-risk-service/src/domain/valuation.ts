import { createHash } from 'node:crypto';
import type { PortfolioSnapshot } from './portfolio.js';

export interface PricePoint {
  readonly securityId: string;
  readonly close: string;
  readonly asOf: string;
}

export interface PortfolioValuation {
  readonly portfolioId: string;
  readonly portfolioSnapshotId: string;
  readonly ledgerVersion: number;
  readonly marketDataVersion: string;
  readonly asOf: string;
  readonly marketValue: string;
  readonly totalEquity: string;
  readonly positionValues: readonly { securityId: string; marketValue: string }[];
  readonly contentHash: string;
}

export function valuePortfolio(snapshot: PortfolioSnapshot, prices: readonly PricePoint[], marketDataVersion: string, asOf: string, maxPriceAgeMinutes: number): PortfolioValuation {
  if (!marketDataVersion || !Date.parse(asOf) || !Number.isInteger(maxPriceAgeMinutes) || maxPriceAgeMinutes < 0) throw new Error('invalid valuation input');
  const priceBySecurity = new Map(prices.map((price) => [price.securityId, price]));
  const positionValues = snapshot.positions.map((position) => {
    const price = priceBySecurity.get(position.securityId);
    if (!price) throw new Error(`missing price for ${position.securityId}`);
    if (!isPositiveDecimal(price.close)) throw new Error(`invalid price for ${position.securityId}`);
    if (!Date.parse(price.asOf) || new Date(asOf).getTime() - new Date(price.asOf).getTime() > maxPriceAgeMinutes * 60_000) throw new Error(`stale price for ${position.securityId}`);
    return { securityId: position.securityId, marketValue: multiplyDecimal(position.quantity, price.close) };
  });
  const marketValue = positionValues.reduce((total, position) => addDecimal(total, position.marketValue), '0');
  const withoutHash = { portfolioId: snapshot.portfolioId, portfolioSnapshotId: snapshot.snapshotId, ledgerVersion: snapshot.ledgerVersion, marketDataVersion, asOf, marketValue, totalEquity: addDecimal(snapshot.cash, marketValue), positionValues };
  return { ...withoutHash, contentHash: createHash('sha256').update(JSON.stringify(withoutHash)).digest('hex') };
}

const scale = 100_000_000n;
function scaled(value: string): bigint { const negative = value.startsWith('-'); const [whole, fraction = ''] = (negative ? value.slice(1) : value).split('.'); const result = BigInt(whole) * scale + BigInt((fraction + '00000000').slice(0, 8)); return negative ? -result : result; }
function decimal(value: bigint): string { const negative = value < 0n; const absolute = negative ? -value : value; const fraction = (absolute % scale).toString().padStart(8, '0').replace(/0+$/, ''); return `${negative ? '-' : ''}${absolute / scale}${fraction ? `.${fraction}` : ''}`; }
function addDecimal(left: string, right: string): string { return decimal(scaled(left) + scaled(right)); }
function multiplyDecimal(left: string, right: string): string { return decimal((scaled(left) * scaled(right)) / scale); }
function isPositiveDecimal(value: string): boolean { return /^\d+(?:\.\d{1,8})?$/.test(value) && scaled(value) > 0n; }
