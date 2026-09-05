import type { ApprovedExecutionCommand } from '../domain/execution.js';
import type { ExecutionAuthorizationGrant } from '@stock/contracts';

/** 实现必须读取权威服务，不能信任命令内的ID或布尔声明。 */
export interface ExecutionAuthorization {
  assertAuthorized(command: ApprovedExecutionCommand): Promise<void>;
}

export class ExecutionAuthorizationUnavailable extends Error {
  constructor() { super('execution authorization adapter is not configured; execution is disabled'); }
}

export const denyExecution: ExecutionAuthorization = {
  async assertAuthorized(): Promise<void> { throw new ExecutionAuthorizationUnavailable(); },
};

/** HTTP/NATS适配器只需实现此读取端口；验证规则集中在执行边界。 */
export interface ExecutionAuthorizationGrantReader { getGrant(command: ApprovedExecutionCommand): Promise<ExecutionAuthorizationGrant | undefined>; }
export class GrantExecutionAuthorization implements ExecutionAuthorization {
  constructor(private readonly reader: ExecutionAuthorizationGrantReader, private readonly now: () => number = Date.now) {}
  async assertAuthorized(command: ApprovedExecutionCommand): Promise<void> {
    if (!command.resourceReservationId) throw new Error('resource reservation is required for execution');
    const grant = await this.reader.getGrant(command);
    if (!grant || Date.parse(grant.validUntil) <= this.now()) throw new Error('execution authorization is absent or expired');
    const same = grant.decisionId === command.decisionId && grant.proposalVersion === command.proposalVersion && grant.approvalId === command.approvalId && grant.riskEvaluationId === command.riskEvaluationId && grant.budgetReservationId === command.budgetReservationId && grant.resourceReservationId === command.resourceReservationId && grant.targetPortfolioVersion === command.targetPortfolioVersion && grant.executionContentHash === command.contentHash && grant.validUntil === command.validUntil;
    if (!same) throw new Error('execution authorization does not match command');
  }
}
