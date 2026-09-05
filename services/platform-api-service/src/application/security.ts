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

export const ROLES = ['VIEWER', 'RESEARCHER', 'RISK_REVIEWER', 'APPROVER', 'EXECUTION_OPERATOR', 'ADMIN'] as const;
export type Role = typeof ROLES[number];

export class InMemoryAuditRepository {
  private readonly records: RequestAudit[] = [];

  public append(record: RequestAudit): void { this.records.push(record); }
  public list(): readonly RequestAudit[] { return this.records; }
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

export function toProblemDetails(error: unknown, requestId: string, fallbackStatus = 500): ProblemDetails {
  const detail = error instanceof Error ? error.message : 'unexpected platform api error';
  const status = detail.startsWith('missing role:') ? 403 : fallbackStatus;
  return { type: 'https://stock-analysis.dev/problems/platform-api', title: status === 403 ? 'Forbidden' : 'Internal Server Error', status, detail, requestId };
}
