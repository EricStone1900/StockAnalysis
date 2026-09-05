import { describe, expect, it } from 'vitest';
import { compatibleVersion, readFeatureFlags, securityHeaders } from '../../src/application/compatibility.js';

describe('platform compatibility', () => {
  it('fails closed for unsupported client versions and exposes explicit flags', () => {
    expect(compatibleVersion('v2')).toBe(false);
    expect(compatibleVersion('v1')).toBe(true);
    expect(readFeatureFlags({ PLATFORM_FEATURE_REALTIME: 'true' })).toEqual({ dashboard: true, realtime: true });
  });

  it('provides no-store security defaults', () => {
    expect(securityHeaders()['x-frame-options']).toBe('DENY');
    expect(securityHeaders()['cache-control']).toBe('no-store');
  });
});
