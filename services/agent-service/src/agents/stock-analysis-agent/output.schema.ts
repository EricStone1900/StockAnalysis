import { z } from 'zod';

export const stockAnalysisAssessmentSchema = z.object({
  assessmentId: z.string().min(1),
  stockAnalysisSnapshotId: z.string().min(1),
  symbol: z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/),
  summary: z.string().min(1),
  opportunities: z.array(z.string()),
  risks: z.array(z.string()),
  supportingStrategySnapshotIds: z.array(z.string().min(1)),
  conflictingStrategySnapshotIds: z.array(z.string().min(1)),
  noTradeBaseline: z.enum(['SUPPORTS_TRADE', 'SUPPORTS_HOLD', 'NOT_AVAILABLE']),
  evidenceIds: z.array(z.string().min(1)).min(1),
  confidence: z.number().min(0).max(1),
  validUntil: z.string().datetime({ offset: true }),
});

export type StockAnalysisAssessment = z.infer<typeof stockAnalysisAssessmentSchema>;
