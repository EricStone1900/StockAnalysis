import { createHash } from 'node:crypto';

export type PaperOrderStatus = 'FILLED' | 'PARTIALLY_FILLED' | 'REJECTED' | 'CANCELLED';
export interface PaperMarketSnapshot { availableAt: string; referencePrice: string; tradable: boolean; upperLimit?: string; lowerLimit?: string; maxFillQuantity: string; }
export interface PaperOrderCommand { paperAccountId: string; clientOrderId: string; rebalanceBatchId: string; intentId: string; securityId: string; side: 'BUY' | 'SELL'; quantity: string; limitPrice?: string; market: PaperMarketSnapshot; }
export interface PaperFill { fillId: string; quantity: string; price: string; fee: string; slippage: string; occurredAt: string; }
export interface PaperOrderResult { clientOrderId: string; status: PaperOrderStatus; fills: readonly PaperFill[]; rejectionReason?: string; }

export class PaperBrokerAdapter {
  private readonly orders = new Map<string, PaperOrderResult>();

  public constructor(private readonly seed: string, private readonly feeRate = 0.0003, private readonly slippageBps = 2) {}

  public place(command: PaperOrderCommand): PaperOrderResult {
    const existing = this.orders.get(command.clientOrderId);
    if (existing) return existing;
    const rejected = validate(command);
    if (rejected) return this.store({ clientOrderId: command.clientOrderId, status: 'REJECTED', fills: [], rejectionReason: rejected });
    const requested = Number(command.quantity);
    const filled = Math.min(requested, Number(command.market.maxFillQuantity));
    if (filled <= 0) return this.store({ clientOrderId: command.clientOrderId, status: 'REJECTED', fills: [], rejectionReason: 'NO_LIQUIDITY' });
    const reference = Number(command.market.referencePrice);
    const direction = command.side === 'BUY' ? 1 : -1;
    const deterministicNoise = hashUnit(`${this.seed}:${command.clientOrderId}`) * 0.1;
    const slippage = reference * (this.slippageBps / 10_000 + deterministicNoise / 10_000) * direction;
    const price = reference + slippage;
    const fee = Math.abs(price * filled * this.feeRate);
    const fill: PaperFill = { fillId: `paper-fill:${command.clientOrderId}`, quantity: format(filled), price: format(price), fee: format(fee), slippage: format(Math.abs(slippage)), occurredAt: command.market.availableAt };
    return this.store({ clientOrderId: command.clientOrderId, status: filled === requested ? 'FILLED' : 'PARTIALLY_FILLED', fills: [fill] });
  }

  public query(clientOrderId: string): PaperOrderResult | undefined { return this.orders.get(clientOrderId); }

  public cancel(clientOrderId: string): PaperOrderResult {
    const existing = this.orders.get(clientOrderId);
    if (!existing) throw new Error('paper order not found');
    if (existing.status === 'FILLED' || existing.status === 'REJECTED') return existing;
    return this.store({ ...existing, status: 'CANCELLED' });
  }

  private store(result: PaperOrderResult): PaperOrderResult { this.orders.set(result.clientOrderId, result); return result; }
}

function validate(command: PaperOrderCommand): string | undefined {
  if (!command.paperAccountId.startsWith('paper-')) return 'PAPER_ACCOUNT_REQUIRED';
  if (!command.clientOrderId || !command.rebalanceBatchId || !command.intentId || !command.securityId) return 'REQUIRED_IDENTIFIER_MISSING';
  const quantity = Number(command.quantity); const reference = Number(command.market.referencePrice);
  if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(reference) || reference <= 0 || !Date.parse(command.market.availableAt)) return 'INVALID_ORDER_OR_MARKET';
  if (!command.market.tradable) return 'NOT_TRADABLE';
  const limit = command.limitPrice === undefined ? undefined : Number(command.limitPrice);
  if (limit !== undefined && (!Number.isFinite(limit) || limit <= 0 || (command.side === 'BUY' && limit < reference) || (command.side === 'SELL' && limit > reference))) return 'LIMIT_PRICE_NOT_MARKETABLE';
  if (command.market.upperLimit && reference > Number(command.market.upperLimit)) return 'UPPER_LIMIT_BREACH';
  if (command.market.lowerLimit && reference < Number(command.market.lowerLimit)) return 'LOWER_LIMIT_BREACH';
  return undefined;
}

function hashUnit(input: string): number { return Number.parseInt(createHash('sha256').update(input).digest('hex').slice(0, 8), 16) / 0xffff_ffff; }
function format(value: number): string { return value.toFixed(8); }
