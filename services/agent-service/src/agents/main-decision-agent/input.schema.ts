import { z } from 'zod';

const instantSchema = z.string().datetime({ offset: true });
const symbolSchema = z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/);
const evidenceSchema = z.array(z.string().min(1)).min(1);

const strategyRefSchema = z.object({
  snapshotId: z.string().min(1), status: z.literal('ACTIVE'), productionVerified: z.literal(true),
  validUntil: instantSchema, evidenceIds: evidenceSchema,
}).strict();

const specialistRefSchema = z.object({
  assessmentId: z.string().min(1),
  stance: z.enum(['SUPPORT', 'OPPOSE', 'NEUTRAL', 'RISK_ESCALATION']),
  validUntil: instantSchema,
  evidenceIds: evidenceSchema,
}).strict();

const targetLegSchema = z.object({
  legId: z.string().min(1), symbol: symbolSchema, side: z.enum(['BUY', 'SELL']),
  targetWeight: z.number().min(0).max(1), evidenceIds: evidenceSchema,
}).strict();

export const mainDecisionInputSchema = z.object({
  decisionAsOf: instantSchema,
  expiresAt: instantSchema,
  trigger: z.enum(['DAILY_TARGET', 'INTRADAY_RISK_REDUCTION', 'EXECUTION_CORRECTION']),
  quantSnapshotId: z.string().min(1),
  strategySnapshotIds: z.array(z.string().min(1)).min(1),
  strategies: z.array(strategyRefSchema).min(1),
  newsEventIds: z.array(z.string().min(1)),
  anomalyEventIds: z.array(z.string().min(1)),
  marketRegimeSnapshotId: z.string().min(1),
  portfolioSnapshotId: z.string().min(1),
  portfolioEvidenceIds: evidenceSchema,
  specialistAssessments: z.array(specialistRefSchema).min(1),
  contextHash: z.string().regex(/^[a-f0-9]{64}$/),
  strategyDecision: z.enum(['NO_REBALANCE', 'REBALANCE_CANDIDATE', 'RISK_REDUCTION']),
  targetPortfolioVersion: z.string().min(1),
  targetLegs: z.array(targetLegSchema),
  evidenceIds: evidenceSchema,
}).strict().superRefine((input, context) => {
  if (input.expiresAt <= input.decisionAsOf) context.addIssue({ code: z.ZodIssueCode.custom, message: 'expiresAt must be after decisionAsOf' });
  if (input.strategySnapshotIds.length !== input.strategies.length || input.strategySnapshotIds.some((id) => !input.strategies.some((strategy) => strategy.snapshotId === id))) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: 'strategySnapshotIds must resolve to ACTIVE strategy references' });
  }
  for (const strategy of input.strategies) if (strategy.validUntil < input.decisionAsOf) context.addIssue({ code: z.ZodIssueCode.custom, message: 'strategy evidence is expired' });
  for (const specialist of input.specialistAssessments) if (specialist.validUntil < input.decisionAsOf) context.addIssue({ code: z.ZodIssueCode.custom, message: 'specialist evidence is expired' });
  if (input.strategyDecision === 'NO_REBALANCE' && input.targetLegs.length > 0) context.addIssue({ code: z.ZodIssueCode.custom, message: 'NO_REBALANCE cannot carry target legs' });
  if (input.strategyDecision !== 'NO_REBALANCE' && input.targetLegs.length === 0) context.addIssue({ code: z.ZodIssueCode.custom, message: 'REBALANCE requires target legs' });
});

export type MainDecisionInput = z.infer<typeof mainDecisionInputSchema>;
