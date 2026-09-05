import { z } from 'zod';

export const riskReviewOutputSchema = z.object({
  decisionId: z.string().min(1), proposalVersion: z.number().int().positive(), evidencePacketHash: z.string().regex(/^[a-f0-9]{64}$/),
  verdict: z.enum(['PASS', 'PASS_WITH_CONDITIONS', 'REJECT', 'INSUFFICIENT_EVIDENCE']),
  riskLevel: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']), counterThesis: z.array(z.string()), evidenceIds: z.array(z.string().min(1)).min(1),
  validUntil: z.string().datetime({ offset: true }),
}).strict();

export type RiskReviewOutput = z.infer<typeof riskReviewOutputSchema>;
