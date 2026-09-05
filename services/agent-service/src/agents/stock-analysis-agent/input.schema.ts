import { z } from 'zod';

const instantSchema = z.string().datetime({ offset: true });
const evidenceIdsSchema = z.array(z.string().min(1)).min(1);

export const stockAnalysisInputSchema = z.object({
  decisionAsOf: instantSchema,
  symbol: z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/),
  dailyAnalysisSnapshot: z.object({
    snapshotId: z.string().min(1),
    status: z.literal('READY'),
    isStale: z.literal(false),
    publishedAt: instantSchema,
    validUntil: instantSchema,
    analyses: z.array(z.object({
      symbol: z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/),
      signal: z.enum(['BUY', 'HOLD', 'SELL']),
      evidenceIds: evidenceIdsSchema,
    }).strict()).min(1),
    evidenceIds: evidenceIdsSchema,
  }).strict(),
  portfolio: z.object({
    snapshotId: z.string().min(1),
    heldSymbols: z.array(z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/)),
    evidenceIds: evidenceIdsSchema,
  }).strict(),
  activeStrategySnapshots: z.array(z.object({
    snapshotId: z.string().min(1),
    strategyId: z.string().min(1),
    status: z.literal('ACTIVE'),
    productionVerified: z.literal(true),
    publishedAt: instantSchema,
    validUntil: instantSchema,
    rebalanceDecision: z.enum(['NO_REBALANCE', 'REBALANCE_CANDIDATE', 'RISK_REDUCTION']),
    evidenceIds: evidenceIdsSchema,
  }).strict()),
}).strict().superRefine((input, context) => {
  if (!input.dailyAnalysisSnapshot.analyses.some((analysis) => analysis.symbol === input.symbol)) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: 'symbol must exist in DailyAnalysisSnapshot' });
  }
  if (input.dailyAnalysisSnapshot.publishedAt > input.decisionAsOf || input.dailyAnalysisSnapshot.validUntil < input.decisionAsOf) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: 'DailyAnalysisSnapshot must be published and valid at decisionAsOf' });
  }
  for (const snapshot of input.activeStrategySnapshots) {
    if (snapshot.publishedAt > input.decisionAsOf || snapshot.validUntil < input.decisionAsOf) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: 'ACTIVE strategy snapshot must be published and valid at decisionAsOf' });
    }
  }
});

export type StockAnalysisAgentInput = z.infer<typeof stockAnalysisInputSchema>;
