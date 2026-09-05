import { proxyActivities } from '@temporalio/workflow';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';
import { type RebalanceExecutionActivities, type RebalanceExecutionRequest, validateRebalanceRequest, validateRebalanceResult } from './rebalance-execution.contract.js';

const activities = proxyActivities<RebalanceExecutionActivities>({ startToCloseTimeout: '15 minutes', retry: ACTIVITY_RETRY_POLICY });

export async function rebalanceExecutionWorkflow(input: RebalanceExecutionRequest) {
  const request = validateRebalanceRequest(input);
  const reservation = await activities.reserveBudget(request);
  if (reservation.result.reservationStatus !== 'RESERVED') return validateRebalanceResult('FAILED', [reservation]);
  try {
    const batch = await activities.createRebalanceBatch(request);
    if (batch.result.accepted !== true) {
      const released = await activities.releaseBudget(request);
      return validateRebalanceResult('RELEASED', [reservation, batch, released]);
    }
    const intents = await activities.createManualOrderIntents(request);
    const fills = await activities.recordFills(request);
    if (fills.result.fillStatus === 'UNKNOWN') return validateRebalanceResult('UNKNOWN', [reservation, batch, intents, fills]);
    return validateRebalanceResult(fills.result.fillStatus === 'PARTIAL' ? 'PARTIAL' : 'COMPLETED', [reservation, batch, intents, fills]);
  } catch {
    const released = await activities.releaseBudget(request);
    return validateRebalanceResult('RELEASED', [reservation, released]);
  }
}
