import { z } from 'zod';

export const marketMonitorAssessmentSchema = z.object({
  assessmentId: z.string().min(1),
  anomalyEventId: z.string().min(1),
  assessment: z.enum(['IGNORE', 'WATCH', 'REASSESS', 'RISK_ESCALATION']),
  explanation: z.string().min(1),
  risks: z.array(z.string()),
  evidenceIds: z.array(z.string().min(1)).min(1),
  confidence: z.number().min(0).max(1),
  validUntil: z.string().datetime({ offset: true }),
});

export type MarketMonitorAssessment = z.infer<typeof marketMonitorAssessmentSchema>;
