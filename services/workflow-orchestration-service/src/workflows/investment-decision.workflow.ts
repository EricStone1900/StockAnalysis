import { proxyActivities } from '@temporalio/workflow';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';
import { buildInvestmentDecisionRequests, type InvestmentDecisionActivities, type InvestmentDecisionRequest, validateInvestmentDecisionResult } from './investment-decision.contract.js';

const activities = proxyActivities<InvestmentDecisionActivities>({ startToCloseTimeout: '15 minutes', retry: ACTIVITY_RETRY_POLICY });

export async function investmentDecisionWorkflow(request: InvestmentDecisionRequest) {
  const requests = buildInvestmentDecisionRequests(request);
  const gate = await activities.validateDecisionGate(requests[0]);
  if (gate.result.allowed !== true) return validateInvestmentDecisionResult('BLOCKED', [gate]);
  const specialists = await activities.collectSpecialistEvidence(requests[1]);
  const main = await activities.runMainDecision(requests[2]);
  if (main.result.proposalAction === 'HOLD') return validateInvestmentDecisionResult('HOLD', [gate, specialists, main]);
  const risk = await activities.runRiskReview(requests[3]);
  if (risk.result.verdict !== 'PASS' && risk.result.verdict !== 'PASS_WITH_CONDITIONS') return validateInvestmentDecisionResult('REJECTED', [gate, specialists, main, risk]);
  const hardRisk = await activities.runHardRiskEvaluation(requests[4]);
  return validateInvestmentDecisionResult(hardRisk.result.hardRiskPassed === true ? 'READY_FOR_APPROVAL' : 'REJECTED', [gate, specialists, main, risk, hardRisk]);
}
