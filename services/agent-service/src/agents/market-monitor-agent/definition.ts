import type { AgentDefinition } from '../../application/agent-kernel.js';
import { marketMonitorInputSchema, type MarketMonitorAgentInput } from './input.schema.js';
import { marketMonitorAssessmentSchema, type MarketMonitorAssessment } from './output.schema.js';

export const marketMonitorDefinition: AgentDefinition<MarketMonitorAgentInput, MarketMonitorAssessment> = {
  id: 'market-monitor',
  version: 'v1',
  promptVersion: 'market-monitor-v1',
  maxToolCalls: 0,
  outputSchema: marketMonitorAssessmentSchema,
  async invoke(untrustedInput) {
    const input = marketMonitorInputSchema.parse(untrustedInput);
    const event = input.anomalyEvent;
    const assessment = event.severity === 'CRITICAL'
      ? 'RISK_ESCALATION'
      : event.severity === 'HIGH'
        ? 'REASSESS'
        : event.severity === 'MEDIUM' ? 'WATCH' : 'IGNORE';
    return {
      output: {
        assessmentId: `monitor-assessment:${event.eventId}:${event.eventVersion}`,
        anomalyEventId: event.eventId,
        assessment,
        explanation: `基于异常事件 ${event.eventId} 的 ${event.severity} 严重度生成确定性 Fake 评估。`,
        risks: event.severity === 'LOW' ? [] : ['异常需要由后续流程结合组合和风险证据复核。'],
        evidenceIds: event.evidenceIds,
        confidence: event.severity === 'LOW' ? 0.7 : 0.8,
        validUntil: input.decisionAsOf,
      },
      toolCalls: [],
    };
  },
};
