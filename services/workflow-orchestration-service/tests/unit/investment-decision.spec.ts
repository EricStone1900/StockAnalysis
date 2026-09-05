import { describe, expect, it } from 'vitest';
import { FakeInvestmentDecisionActivities } from '../../src/activities/fake-activities.js';
import { buildInvestmentDecisionRequests, validateInvestmentDecisionResult, type InvestmentDecisionRequest } from '../../src/workflows/investment-decision.contract.js';

const base: InvestmentDecisionRequest = { workflowId: 'decision-1', runId: 'run-1', correlationId: 'corr-decision-1', idempotencyKey: 'decision-1', payload: { decisionAsOf: '2026-09-05T08:00:00Z', trigger: 'DAILY_TARGET', scenario: 'PASS' } };

describe('InvestmentDecisionWorkflow contract', () => {
  it('blocks before specialist or model calls when the gate rejects', async () => {
    const activities = new FakeInvestmentDecisionActivities();
    const requests = buildInvestmentDecisionRequests({ ...base, payload: { ...base.payload, scenario: 'BLOCKED' } });
    const gate = await activities.validateDecisionGate(requests[0]);
    expect(gate.result.allowed).toBe(false);
    expect(validateInvestmentDecisionResult('BLOCKED', [gate]).status).toBe('BLOCKED');
  });

  it('ends HOLD before risk review and hard risk', async () => {
    const activities = new FakeInvestmentDecisionActivities();
    const requests = buildInvestmentDecisionRequests({ ...base, payload: { ...base.payload, scenario: 'HOLD' } });
    const gate = await activities.validateDecisionGate(requests[0]);
    const specialists = await activities.collectSpecialistEvidence(requests[1]);
    const main = await activities.runMainDecision(requests[2]);
    expect(main.result.proposalAction).toBe('HOLD');
    expect(validateInvestmentDecisionResult('HOLD', [gate, specialists, main]).artifactRefs).toHaveLength(3);
  });

  it('requires both independent risk review and hard risk before approval', async () => {
    const activities = new FakeInvestmentDecisionActivities();
    const requests = buildInvestmentDecisionRequests(base);
    const results = await Promise.all([activities.validateDecisionGate(requests[0]), activities.collectSpecialistEvidence(requests[1]), activities.runMainDecision(requests[2]), activities.runRiskReview(requests[3]), activities.runHardRiskEvaluation(requests[4])]);
    expect(validateInvestmentDecisionResult('READY_FOR_APPROVAL', results).artifactRefs).toHaveLength(5);
    const rejected = { ...base, idempotencyKey: 'decision-risk-reject', payload: { ...base.payload, scenario: 'RISK_REJECT' as const } };
    const riskRequests = buildInvestmentDecisionRequests(rejected);
    const risk = await activities.runRiskReview(riskRequests[3]);
    expect(risk.result.verdict).toBe('REJECT');
  });

  it('rejects a successful path when hard risk fails or an artifact is missing', async () => {
    const activities = new FakeInvestmentDecisionActivities();
    const requests = buildInvestmentDecisionRequests({ ...base, payload: { ...base.payload, scenario: 'HARD_REJECT' } });
    const hardRisk = await activities.runHardRiskEvaluation(requests[4]);
    expect(hardRisk.result.hardRiskPassed).toBe(false);
    const gate = await activities.validateDecisionGate(requests[0]);
    expect(() => validateInvestmentDecisionResult('READY_FOR_APPROVAL', [gate])).toThrow('requires 5');
  });
});
