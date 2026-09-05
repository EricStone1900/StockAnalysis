import { describe, expect, it } from 'vitest';

import { createAudit, InMemoryAuditRepository, principalFromHeaders, requireRole, toProblemDetails } from '../../src/application/security.js';

describe('platform security primitives', () => {
  it('parses a principal without trusting blank roles', () => {
    expect(principalFromHeaders(' user-1 ', 'RESEARCH_READ, ,OPS')).toEqual({ actorId: 'user-1', roles: ['RESEARCH_READ', 'OPS'] });
    expect(principalFromHeaders(undefined, undefined).roles).toEqual([]);
  });

  it('enforces roles and creates traceable audit records', () => {
    const principal = principalFromHeaders('user-1', 'RESEARCH_READ');
    expect(() => requireRole(principal, 'RESEARCH_READ')).not.toThrow();
    expect(() => requireRole(principal, 'ADMIN')).toThrow('missing role');
    expect(createAudit({ requestId: 'req-1', correlationId: 'corr-1', actorId: 'user-1', action: 'dashboard.read', occurredAt: '2026-09-04T00:00:00Z' }).occurredAt).toBe('2026-09-04T00:00:00Z');
    const repository = new InMemoryAuditRepository();
    repository.append(createAudit({ requestId: 'req-1', correlationId: 'corr-1', actorId: 'user-1', action: 'dashboard.read', occurredAt: '2026-09-04T00:00:00Z' }));
    expect(repository.list()).toHaveLength(1);
    expect(toProblemDetails(new Error('missing role: ADMIN'), 'req-1').status).toBe(403);
  });
});
