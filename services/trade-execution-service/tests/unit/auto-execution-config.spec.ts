import { describe, expect, it } from 'vitest';
import { readAutoExecutionConfig } from '../../src/application/auto-execution-config.js';

const approved = { AUTO_EXECUTION_ENABLED: 'true', AUTO_EXECUTION_APPROVAL_REFERENCE: 'approval-2026-09-05', AUTO_EXECUTION_ALLOWED_ACCOUNTS: 'small-live-001', AUTO_EXECUTION_ALLOWED_SECURITIES: 'SSE:600000,SSE:600001', AUTO_EXECUTION_ALLOWED_STRATEGY_VERSIONS: 'strategy-v1', AUTO_EXECUTION_MAX_BATCH_NOTIONAL: '10000', AUTO_EXECUTION_MAX_ORDER_NOTIONAL: '5000', AUTO_EXECUTION_SESSION_START_UTC: '01:30', AUTO_EXECUTION_SESSION_END_UTC: '07:00' };

describe('readAutoExecutionConfig', () => {
  it('默认关闭且没有隐式白名单', () => { const config = readAutoExecutionConfig({}); expect(config.policy.enabled).toBe(false); expect(config.policy.allowedAccountIds).toEqual([]); });
  it('启用时读取精确白名单和审批引用', () => { const config = readAutoExecutionConfig(approved); expect(config.approvalReference).toBe('approval-2026-09-05'); expect(config.policy.enabled).toBe(true); expect(config.policy.allowedSecurityIds).toEqual(['SSE:600000', 'SSE:600001']); });
  it('拒绝缺失审批、白名单和非法时段/额度的启用配置', () => { expect(() => readAutoExecutionConfig({ ...approved, AUTO_EXECUTION_APPROVAL_REFERENCE: '' })).toThrow('APPROVAL_REFERENCE'); expect(() => readAutoExecutionConfig({ ...approved, AUTO_EXECUTION_ALLOWED_ACCOUNTS: '' })).toThrow('ALLOWED_ACCOUNTS'); expect(() => readAutoExecutionConfig({ ...approved, AUTO_EXECUTION_MAX_BATCH_NOTIONAL: '0' })).toThrow('MAX_BATCH_NOTIONAL'); expect(() => readAutoExecutionConfig({ ...approved, AUTO_EXECUTION_SESSION_START_UTC: '18:00', AUTO_EXECUTION_SESSION_END_UTC: '07:00' })).toThrow('invalid auto execution session'); });
});
