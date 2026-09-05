import { createHash } from 'node:crypto';
import type { ExecutionAuthorizationGrant, ResourceReservation } from '@stock/contracts';
import type { Reservation } from '../domain/decision-budget.js';
import type { TradeProposal } from '../domain/proposal.js';

export interface ExecutionAuthorizationInput {
  readonly decisionId: string;
  readonly proposalId: string;
  readonly proposalVersion: number;
  readonly budgetReservationId: string;
  readonly resourceReservationId: string;
  readonly executionContentHash: string;
  readonly validUntil: string;
}

/**
 * 生成执行服务可校验的只读授权视图。调用方必须提供已从各所有者读取到的
 * 最新快照；任何一个快照不匹配都拒绝发放，而不是事后补偿。
 */
export class ExecutionAuthorizationService {
  issue(input: ExecutionAuthorizationInput, proposal: TradeProposal | undefined, budget: Reservation | undefined, resource: ResourceReservation | undefined, now = new Date()): ExecutionAuthorizationGrant {
    if (!proposal || proposal.proposalId !== input.proposalId || proposal.proposalVersion !== input.proposalVersion || proposal.state !== 'APPROVED' || proposal.approval?.decision !== 'APPROVED') throw new Error('proposal approval is not valid');
    if (!budget || budget.reservationId !== input.budgetReservationId || budget.proposalId !== proposal.proposalId || budget.status !== 'DISPATCHING') throw new Error('budget reservation is not dispatching');
    if (!resource || resource.reservationId !== input.resourceReservationId || resource.status !== 'DISPATCHING') throw new Error('resource reservation is not dispatching');
    if (resource.decisionId !== input.decisionId || resource.proposalVersion !== proposal.proposalVersion || resource.ledgerVersion !== proposal.targetPortfolioVersion || resource.riskEvaluationId !== proposal.riskReview?.evaluationId || resource.riskPolicyVersion !== proposal.riskReview?.policyVersion || resource.executionContentHash !== input.executionContentHash) throw new Error('execution authority references do not match');
    if (!/^[a-f0-9]{64}$/.test(input.executionContentHash) || !Date.parse(input.validUntil) || new Date(input.validUntil) <= now) throw new Error('invalid execution authorization expiry');
    const approval = proposal.approval;
    const approvalId = createHash('sha256').update(JSON.stringify({ proposalId: proposal.proposalId, proposalVersion: proposal.proposalVersion, approval: { actorId: approval.actorId, decision: approval.decision, reason: approval.reason, decidedAt: approval.decidedAt } })).digest('hex');
    return { decisionId: input.decisionId, proposalVersion: proposal.proposalVersion, approvalId, riskEvaluationId: resource.riskEvaluationId, budgetReservationId: budget.reservationId, resourceReservationId: resource.reservationId, targetPortfolioVersion: proposal.targetPortfolioVersion, executionContentHash: input.executionContentHash, validUntil: input.validUntil };
  }
}
