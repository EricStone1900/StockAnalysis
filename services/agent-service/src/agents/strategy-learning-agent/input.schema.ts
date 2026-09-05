import { z } from 'zod';

const instantSchema = z.string().datetime({ offset: true });
const episodeSchema = z.enum(['FILLED', 'REJECTED', 'HOLD', 'EXPIRED', 'SHADOW']);

export const strategyLearningInputSchema = z.object({
  analysisAsOf: instantSchema,
  currentStrategy: z.object({ strategyId: z.string().min(1), strategyVersion: z.string().min(1), status: z.literal('ACTIVE'), evidenceIds: z.array(z.string().min(1)).min(1) }).strict(),
  outcomes: z.array(z.object({ decisionId: z.string().min(1), episodeType: episodeSchema, outcomeClass: z.enum(['SUCCESS', 'COUNTEREXAMPLE']), windowClosed: z.literal(true), availableAt: instantSchema, evidenceIds: z.array(z.string().min(1)).min(1) }).strict()).min(1),
  decisionMemoryIds: z.array(z.string().min(1)).min(1),
  humanFeedback: z.array(z.object({ feedbackId: z.string().min(1), kind: z.enum(['CONFIRMED', 'CORRECTED', 'REJECTED']), evidenceIds: z.array(z.string().min(1)).min(1) }).strict()),
  minimumSamples: z.number().int().min(3).default(3),
  minimumCounterexamples: z.number().int().min(1).default(1),
}).strict().superRefine((input, context) => {
  for (const outcome of input.outcomes) if (outcome.availableAt > input.analysisAsOf) context.addIssue({ code: z.ZodIssueCode.custom, message: 'learning input cannot include future outcome' });
  const counterexamples = input.outcomes.filter((outcome) => outcome.outcomeClass === 'COUNTEREXAMPLE');
  if (input.outcomes.length < input.minimumSamples || counterexamples.length < input.minimumCounterexamples || new Set(input.outcomes.map((outcome) => outcome.episodeType)).size < 2) context.addIssue({ code: z.ZodIssueCode.custom, message: 'insufficient learning evidence: require samples, counterexamples, and episode diversity' });
});

export type StrategyLearningInput = z.infer<typeof strategyLearningInputSchema>;
