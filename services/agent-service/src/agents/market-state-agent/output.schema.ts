import { z } from 'zod';

export const marketStateAssessmentSchema = z.object({
  assessmentId: z.string().min(1),
  regimeSnapshotId: z.string().min(1),
  interpretation: z.string().min(1),
  suggestedRiskBias: z.enum(['NORMAL', 'CONSERVATIVE', 'DEFENSIVE']),
  allowNewPositions: z.boolean(),
  preferredIndustries: z.array(z.string()),
  avoidedIndustries: z.array(z.string()),
  portfolioImplications: z.array(z.string()),
  risks: z.array(z.string()),
  evidenceIds: z.array(z.string().min(1)).min(1),
  confidence: z.number().min(0).max(1),
  validUntil: z.string().datetime({ offset: true }),
});

export type MarketStateAssessment = z.infer<typeof marketStateAssessmentSchema>;
