import type { ExecutionContext } from '@nestjs/common';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ExecutionWriteGuard } from '../../src/application/execution-write-guard.js';
const context = (authorization?: string) => ({ switchToHttp: () => ({ getRequest: () => ({ headers: { authorization } }) }) }) as ExecutionContext;
describe('执行写入口服务身份', () => {
  afterEach(() => vi.unstubAllEnvs());
  it('未配置、缺失身份或错误身份拒绝', () => {
    const guard = new ExecutionWriteGuard();
    vi.stubEnv('EXECUTION_SERVICE_TOKEN', '');
    expect(() => guard.canActivate(context())).toThrow();
    vi.stubEnv('EXECUTION_SERVICE_TOKEN', 'test-only-identity'.repeat(3));
    expect(() => guard.canActivate(context('Bearer wrong'))).toThrow();
  });
  it('匹配身份才通过传输层检查', () => {
    const token = 'test-only-identity'.repeat(3);
    vi.stubEnv('EXECUTION_SERVICE_TOKEN', token);
    expect(new ExecutionWriteGuard().canActivate(context(`Bearer ${token}`))).toBe(true);
  });
});
