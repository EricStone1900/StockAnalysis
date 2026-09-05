import { createHash } from 'node:crypto';
import { z } from 'zod';

const instantSchema = z.string().datetime({ offset: true });
const evidenceSchema = z.array(z.string().min(1)).min(1);
const symbolSchema = z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/);

const legSchema = z.object({
  legId: z.string().min(1), symbol: symbolSchema, side: z.enum(['BUY', 'SELL']), targetWeight: z.number().min(0).max(1), evidenceIds: evidenceSchema,
}).strict();

export const riskReviewInputSchema = z.object({
  decisionAsOf: instantSchema,
  packet: z.object({
    decisionId: z.string().min(1), proposalVersion: z.number().int().positive(), portfolioId: z.string().min(1),
    proposalAction: z.enum(['HOLD', 'REBALANCE']), targetPortfolioVersion: z.string().min(1), legs: z.array(legSchema),
    proposalEvidenceIds: evidenceSchema, strategySnapshotIds: z.array(z.string().min(1)),
    portfolioSnapshotId: z.string().min(1), marketRegimeSnapshotId: z.string().min(1),
    evidenceIds: evidenceSchema, validUntil: instantSchema,
    contentHash: z.string().regex(/^[a-f0-9]{64}$/),
  }).strict(),
  riskMetrics: z.object({
    turnover: z.number().min(0).max(10), estimatedCost: z.number().min(0).max(1), estimatedSlippage: z.number().min(0).max(1),
    capacityUtilization: z.number().min(0).max(1), maxTurnover: z.number().min(0), maxCost: z.number().min(0), maxSlippage: z.number().min(0),
  }).strict(),
  noTradeBaseline: z.enum(['SUPPORTS_TRADE', 'SUPPORTS_HOLD', 'NOT_AVAILABLE']),
  providerAvailable: z.boolean(),
  secondReviewerVerdict: z.enum(['PASS', 'PASS_WITH_CONDITIONS', 'REJECT', 'INSUFFICIENT_EVIDENCE']).optional(),
}).strict().superRefine((input, context) => {
  if (input.packet.validUntil < input.decisionAsOf) context.addIssue({ code: z.ZodIssueCode.custom, message: 'evidence packet is expired' });
  if (input.packet.proposalAction === 'HOLD' && input.packet.legs.length > 0) context.addIssue({ code: z.ZodIssueCode.custom, message: 'HOLD packet cannot contain legs' });
  if (input.packet.proposalAction === 'REBALANCE' && input.packet.legs.length === 0) context.addIssue({ code: z.ZodIssueCode.custom, message: 'REBALANCE packet requires legs' });
  if (calculateEvidencePacketHash(input.packet) !== input.packet.contentHash) context.addIssue({ code: z.ZodIssueCode.custom, message: 'evidence packet hash mismatch' });
});

export type RiskReviewInput = z.infer<typeof riskReviewInputSchema>;

export function calculateEvidencePacketHash(packet: RiskReviewInput['packet']): string {
  const canonical = JSON.stringify(packet, (key, value: unknown) => key === 'contentHash' ? undefined : value);
  return createHash('sha256').update(canonical).digest('hex');
}
