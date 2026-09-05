import { z } from 'zod';

const instantSchema = z.string().datetime({ offset: true });

export const marketMonitorInputSchema = z.object({
  decisionAsOf: instantSchema,
  anomalyEvent: z.object({
    eventId: z.string().min(1),
    eventVersion: z.number().int().positive(),
    symbol: z.string().regex(/^(SSE|SZSE|BSE):\d{6}$/),
    detectedAt: instantSchema,
    windowStart: instantSchema,
    windowEnd: instantSchema,
    type: z.string().min(1),
    severity: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
    ruleHits: z.array(z.object({
      ruleId: z.string().min(1),
      ruleVersion: z.string().min(1),
      observedValue: z.number().optional(),
      threshold: z.number().optional(),
    }).strict()).min(1),
    observedFeatures: z.record(z.union([z.number(), z.string(), z.null()])),
    marketDataVersion: z.string().min(1),
    watchlistVersion: z.string().min(1),
    detectorVersion: z.string().min(1),
    freshness: z.literal('FRESH'),
    evidenceIds: z.array(z.string().min(1)).min(1),
  }).strict(),
}).strict().superRefine((input, context) => {
  const event = input.anomalyEvent;
  if (event.windowStart > event.windowEnd) context.addIssue({ code: z.ZodIssueCode.custom, message: 'anomaly window is invalid' });
  if (event.detectedAt > input.decisionAsOf || event.windowEnd > input.decisionAsOf) context.addIssue({ code: z.ZodIssueCode.custom, message: 'anomaly event cannot be in the future' });
});

export type MarketMonitorAgentInput = z.infer<typeof marketMonitorInputSchema>;
