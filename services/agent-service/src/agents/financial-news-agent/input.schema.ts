import { z } from 'zod';

const instantSchema = z.string().datetime({ offset: true });
const symbolSchema = z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/);

export const financialNewsInputSchema = z.object({
  decisionAsOf: instantSchema,
  candidate: z.object({
    candidateId: z.string().min(1),
    newsIds: z.array(z.string().min(1)).min(1),
    representativeTitle: z.string().min(1),
    contentRefs: z.array(z.string().min(1)).min(1),
    candidateSymbols: z.array(z.object({ symbol: symbolSchema, confidence: z.number().min(0).max(1) }).strict()),
    sourceSummary: z.array(z.string().min(1)).min(1),
    publishedAtStart: instantSchema,
    publishedAtEnd: instantSchema,
    freshness: z.literal('FRESH'),
  }).strict(),
}).strict().superRefine((input, context) => {
  if (input.candidate.publishedAtStart > input.candidate.publishedAtEnd) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: 'candidate publication range is invalid' });
  }
  if (input.candidate.publishedAtEnd > input.decisionAsOf) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: 'candidate cannot be published after decisionAsOf' });
  }
});

export type FinancialNewsAgentInput = z.infer<typeof financialNewsInputSchema>;
