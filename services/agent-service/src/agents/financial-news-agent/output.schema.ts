import { z } from 'zod';

export const financialNewsAssessmentSchema = z.object({
  assessmentId: z.string().min(1),
  candidateId: z.string().min(1),
  newsIds: z.array(z.string().min(1)).min(1),
  eventType: z.enum(['OTHER', 'EARNINGS', 'REGULATORY', 'CORPORATE_ACTION', 'INDUSTRY']),
  affectedSymbols: z.array(z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/)),
  impactDirection: z.enum(['POSITIVE', 'NEGATIVE', 'MIXED', 'UNCERTAIN']),
  impactMagnitude: z.enum(['LOW', 'MEDIUM', 'HIGH', 'UNCERTAIN']),
  impactHorizon: z.enum(['INTRADAY', 'SHORT_TERM', 'MEDIUM_TERM', 'UNCERTAIN']),
  sourceConflicts: z.array(z.string()),
  summary: z.string().min(1),
  risks: z.array(z.string()),
  evidenceIds: z.array(z.string().min(1)).min(1),
  confidence: z.number().min(0).max(1),
  validUntil: z.string().datetime({ offset: true }),
});

export type FinancialNewsAssessment = z.infer<typeof financialNewsAssessmentSchema>;
