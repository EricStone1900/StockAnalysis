import { describe, expect, it } from 'vitest';
import { FakeRebalanceExecutionActivities } from '../../src/activities/fake-activities.js';
import { validateRebalanceRequest, validateRebalanceResult, type RebalanceExecutionRequest } from '../../src/workflows/rebalance-execution.contract.js';

const base: RebalanceExecutionRequest = { workflowId: 'rebalance-1', runId: 'run-1', correlationId: 'corr-rebalance-1', idempotencyKey: 'rebalance-1', payload: { portfolioId: 'portfolio-1', decisionId: 'decision-1', proposalVersion: 1, tradingDate: '2026-09-05', batchSequence: 1, reason: 'DAILY_TARGET', scenario: 'PASS', legCount: 2 } };

describe('RebalanceExecutionWorkflow contract', () => {
  it('rejects an invalid second daily target batch', () => {
    expect(() => validateRebalanceRequest({ ...base, payload: { ...base.payload, batchSequence: 2 } })).toThrow('second batch reason');
  });

  it('completes a multi-leg batch only after fills are recorded', async () => {
    const activities = new FakeRebalanceExecutionActivities();
    const reservation = await activities.reserveBudget(base);
    const batch = await activities.createRebalanceBatch(base);
    const intents = await activities.createManualOrderIntents(base);
    const fills = await activities.recordFills(base);
    expect(reservation.result.reservationStatus).toBe('RESERVED');
    expect(validateRebalanceResult('COMPLETED', [reservation, batch, intents, fills]).artifactRefs).toHaveLength(4);
  });

  it('releases the reservation when batch creation fails and preserves UNKNOWN acceptance', async () => {
    const activities = new FakeRebalanceExecutionActivities();
    const failedRequest = { ...base, idempotencyKey: 'rebalance-batch-fail', payload: { ...base.payload, scenario: 'BATCH_FAIL' as const } };
    const reservation = await activities.reserveBudget(failedRequest);
    await expect(activities.createRebalanceBatch(failedRequest)).rejects.toThrow('batch creation failed');
    const released = await activities.releaseBudget(failedRequest);
    expect(released.result.reservationStatus).toBe('RELEASED');
    const unknownRequest = { ...base, idempotencyKey: 'rebalance-unknown', payload: { ...base.payload, scenario: 'UNKNOWN_ACCEPTANCE' as const } };
    const unknownFill = await activities.recordFills(unknownRequest);
    expect(unknownFill.result.fillStatus).toBe('UNKNOWN');
    expect(validateRebalanceResult('UNKNOWN', [reservation, released, unknownFill]).status).toBe('UNKNOWN');
  });
});
