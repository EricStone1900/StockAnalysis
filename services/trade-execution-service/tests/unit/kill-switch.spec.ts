import { describe, expect, it } from 'vitest';
import { KillSwitchGuard, KillSwitchRegistry, type KillSwitchReader } from '../../src/application/kill-switch.js';

const key = { accountId: 'paper-001', strategyVersion: 'strategy-v1', securityIds: ['SSE:600000'] } as const;
describe('KillSwitchGuard', () => {
  it('支持全局、账户、策略和标的级暂停并可审计恢复', () => {
    const registry = new KillSwitchRegistry(); const guard = new KillSwitchGuard(registry);
    expect(guard.canSubmit(key)).toBe(true); registry.set('ACCOUNT', 'paper-001', 'manual-pause', '2026-09-05T02:00:00Z'); expect(guard.canSubmit(key)).toBe(false); registry.clear('ACCOUNT', 'paper-001', '2026-09-05T02:01:00Z'); expect(guard.canSubmit(key)).toBe(true);
    registry.set('STRATEGY', 'strategy-v1', 'strategy-pause', '2026-09-05T02:02:00Z'); expect(guard.canSubmit(key)).toBe(false); registry.clear('STRATEGY', 'strategy-v1', '2026-09-05T02:03:00Z'); registry.set('SECURITY', 'SSE:600000', 'halt', '2026-09-05T02:04:00Z'); expect(() => guard.assertCanSubmit(key)).toThrow('KILL_SWITCH');
    expect(registry.read()).toHaveLength(3); expect(registry.read().filter((item) => item.enabled)).toHaveLength(1);
  });
  it('读取控制面异常时 fail-closed', () => { const unavailable: KillSwitchReader = { read: () => { throw new Error('control plane unavailable'); } }; expect(new KillSwitchGuard(unavailable).canSubmit(key)).toBe(false); });
  it('全局暂停优先于具体账户', () => { const registry = new KillSwitchRegistry(); const guard = new KillSwitchGuard(registry); registry.set('GLOBAL', 'all', 'incident', '2026-09-05T02:00:00Z'); expect(guard.canSubmit({ ...key, accountId: 'paper-002' })).toBe(false); });
});
