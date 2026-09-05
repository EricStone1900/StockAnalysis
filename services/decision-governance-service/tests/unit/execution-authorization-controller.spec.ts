import { describe, expect, it, vi, afterEach } from 'vitest';
import { ExecutionAuthorizationController } from '../../src/bootstrap/execution-authorization-controller.js';

describe('ExecutionAuthorizationController', () => {
  afterEach(() => { delete process.env.GOVERNANCE_INTERNAL_TOKEN; });
  it('没有治理服务身份时拒绝签发', async () => {
    const controller = new ExecutionAuthorizationController({ issueExecutionAuthorization: vi.fn() } as never, { get: vi.fn() } as never);
    await expect(controller.issue({}, {} as never)).rejects.toThrow('invalid governance service identity');
  });
  it('只用资源读取器返回的资源申请授权', async () => {
    process.env.GOVERNANCE_INTERNAL_TOKEN = 'governance-token';
    const grant = { decisionId: 'd' };
    const issueExecutionAuthorization = vi.fn().mockResolvedValue(grant);
    const get = vi.fn().mockResolvedValue({ reservationId: 'resource-1', status: 'DISPATCHING' });
    const controller = new ExecutionAuthorizationController({ issueExecutionAuthorization } as never, { get } as never);
    await expect(controller.issue({ 'x-service-token': 'governance-token' }, { resourceReservationId: 'resource-1' } as never)).resolves.toEqual(grant);
    expect(get).toHaveBeenCalledWith('resource-1');
    expect(issueExecutionAuthorization).toHaveBeenCalledWith({ resourceReservationId: 'resource-1' }, { reservationId: 'resource-1', status: 'DISPATCHING' });
  });
});
