export interface Principal {
  actorId: string;
  roles: readonly string[];
}

export interface RequestAudit {
  requestId: string;
  correlationId: string;
  actorId: string;
  action: string;
  occurredAt: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  requestId: string;
}

export function principalFromHeaders(actorId: string | undefined, roles: string | undefined): Principal {
  if (!actorId?.trim()) return { actorId: 'anonymous', roles: [] };
  return { actorId: actorId.trim(), roles: (roles ?? '').split(',').map((role) => role.trim()).filter(Boolean) };
}

export function requireRole(principal: Principal, role: string): void {
  if (!principal.roles.includes(role)) throw new Error(`missing role: ${role}`);
}

export function createAudit(input: Omit<RequestAudit, 'occurredAt'> & { occurredAt?: string }): RequestAudit {
  return { ...input, occurredAt: input.occurredAt ?? new Date().toISOString() };
}
