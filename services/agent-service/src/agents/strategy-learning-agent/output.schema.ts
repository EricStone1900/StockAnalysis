import { z } from 'zod';

export const strategyLearningDraftSchema = z.object({
  title: z.string().min(1), hypothesis: z.string().min(1), applicability: z.object({ regimes: z.array(z.string()), horizons: z.array(z.number().int().positive()) }).strict(),
  supportingDecisionIds: z.array(z.string().min(1)).min(1), counterexampleDecisionIds: z.array(z.string().min(1)).min(1),
  sampleBreakdown: z.record(z.string(), z.number().int().nonnegative()), proposedExperiment: z.record(z.string(), z.unknown()), status: z.literal('DRAFT'),
}).strict();

export type StrategyLearningDraft = z.infer<typeof strategyLearningDraftSchema>;
