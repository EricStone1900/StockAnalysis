import { z } from 'zod';

const instantSchema = z.string().datetime({ offset: true });

export const marketStateInputSchema = z.object({
  decisionAsOf: instantSchema,
  regimeSnapshot: z.object({
    snapshotId: z.string().min(1),
    asOf: instantSchema,
    frequency: z.enum(['DAILY', 'INTRADAY']),
    publishedAt: instantSchema,
    overallRegime: z.enum(['RISK_ON', 'NEUTRAL', 'RISK_OFF', 'STRESS']),
    regimeConfidence: z.number().min(0).max(1),
    previousRegime: z.enum(['RISK_ON', 'NEUTRAL', 'RISK_OFF', 'STRESS']).nullable(),
    changeDetected: z.boolean(),
    transitionReason: z.string().min(1),
    trend: z.number(),
    breadth: z.number(),
    volatility: z.number(),
    liquidity: z.number(),
    dataVersion: z.string().min(1),
    featureVersion: z.string().min(1),
    regimeDefinitionVersion: z.string().min(1),
    freshness: z.literal('FRESH'),
    evidenceIds: z.array(z.string().min(1)).min(1),
  }).strict(),
  portfolioExposure: z.object({
    snapshotId: z.string().min(1),
    grossExposure: z.number().min(0).max(1),
    industries: z.array(z.object({ industry: z.string().min(1), weight: z.number().min(0).max(1) }).strict()),
    evidenceIds: z.array(z.string().min(1)).min(1),
  }).strict(),
}).strict().superRefine((input, context) => {
  if (input.regimeSnapshot.publishedAt > input.decisionAsOf || input.regimeSnapshot.asOf > input.decisionAsOf) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: 'regime snapshot cannot be in the future' });
  }
});

export type MarketStateAgentInput = z.infer<typeof marketStateInputSchema>;
