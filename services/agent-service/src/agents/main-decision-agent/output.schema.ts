import { z } from 'zod';

const legSchema = z.object({
  legId: z.string().min(1), symbol: z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/),
  side: z.enum(['BUY', 'SELL']), targetWeight: z.number().min(0).max(1), evidenceIds: z.array(z.string().min(1)).min(1),
}).strict();

export const mainDecisionOutputSchema = z.object({
  decisionId: z.string().min(1), proposalVersion: z.number().int().positive(), portfolioId: z.string().min(1),
  proposalAction: z.enum(['HOLD', 'REBALANCE']),
  rebalanceReason: z.enum(['DAILY_TARGET', 'INTRADAY_RISK_REDUCTION', 'EXECUTION_CORRECTION']).optional(),
  targetPortfolioVersion: z.string().min(1), legs: z.array(legSchema), confidence: z.number().min(0).max(1),
  reasons: z.array(z.string()).min(1), risks: z.array(z.string()), assumptions: z.array(z.string()),
  evidenceIds: z.array(z.string().min(1)).min(1), strategySnapshotIds: z.array(z.string().min(1)),
  validFrom: z.string().datetime({ offset: true }), expiresAt: z.string().datetime({ offset: true }),
}).strict().superRefine((proposal, context) => {
  if (proposal.proposalAction === 'HOLD' && proposal.legs.length > 0) context.addIssue({ code: z.ZodIssueCode.custom, message: 'HOLD proposal must have no legs' });
  if (proposal.proposalAction === 'REBALANCE' && proposal.legs.length === 0) context.addIssue({ code: z.ZodIssueCode.custom, message: 'REBALANCE proposal must have at least one leg' });
});

export type MainDecisionOutput = z.infer<typeof mainDecisionOutputSchema>;
