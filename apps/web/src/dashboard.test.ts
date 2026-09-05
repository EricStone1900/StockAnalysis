import { describe, expect, it } from 'vitest';
import { statusLabel } from './dashboard.js';

describe('dashboard status presentation', () => {
  it('keeps degraded states explicit for users', () => {
    expect(statusLabel('OK')).toBe('正常');
    expect(statusLabel('STALE')).toBe('已过期');
    expect(statusLabel('UNAVAILABLE')).toBe('不可用');
    expect(statusLabel('FORBIDDEN')).toBe('无权限');
  });
});
