export type KillSwitchScope = 'GLOBAL' | 'ACCOUNT' | 'STRATEGY' | 'SECURITY';
export interface KillSwitchKey { readonly accountId: string; readonly strategyVersion: string; readonly securityIds: readonly string[]; }
export interface KillSwitchState { readonly scope: KillSwitchScope; readonly key: string; readonly enabled: boolean; readonly reason: string; readonly updatedAt: string; }
export interface KillSwitchReader { read(): readonly KillSwitchState[]; }

/** 独立于 Agent、NATS 和 Temporal 的内存实现；生产环境可由独立控制面替换。 */
export class KillSwitchRegistry implements KillSwitchReader {
  private readonly states = new Map<string, KillSwitchState>();
  public set(scope: KillSwitchScope, key: string, reason: string, updatedAt: string): KillSwitchState { const state = { scope, key, enabled: true, reason, updatedAt }; this.states.set(`${scope}:${key}`, state); return state; }
  public clear(scope: KillSwitchScope, key: string, updatedAt: string): void { const existing = this.states.get(`${scope}:${key}`); if (existing) this.states.set(`${scope}:${key}`, { ...existing, enabled: false, updatedAt }); }
  public read(): readonly KillSwitchState[] { return [...this.states.values()]; }
}

export class KillSwitchGuard {
  public constructor(private readonly reader: KillSwitchReader) {}
  public canSubmit(key: KillSwitchKey): boolean {
    try {
      const active = this.reader.read().filter((state) => state.enabled);
      return !active.some((state) => state.scope === 'GLOBAL' || (state.scope === 'ACCOUNT' && state.key === key.accountId) || (state.scope === 'STRATEGY' && state.key === key.strategyVersion) || (state.scope === 'SECURITY' && key.securityIds.includes(state.key)));
    } catch { return false; }
  }
  public assertCanSubmit(key: KillSwitchKey): void { if (!this.canSubmit(key)) throw new Error('KILL_SWITCH_ACTIVE_OR_UNAVAILABLE'); }
}
