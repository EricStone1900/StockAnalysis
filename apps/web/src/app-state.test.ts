import { describe, expect, it } from 'vitest';
import { authStatus, routeFor } from './app-state.js';

describe('web app state', () => {
  it('resolves dashboard routes and authentication state', () => {
    expect(routeFor('/')).toBe('dashboard');
    expect(routeFor('/dashboard')).toBe('dashboard');
    expect(routeFor('/settings')).toBe('unknown');
    expect(authStatus('user-1')).toBe('AUTHENTICATED');
    expect(authStatus('')).toBe('ANONYMOUS');
  });
});
