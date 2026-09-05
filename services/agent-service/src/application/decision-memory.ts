import { createHash } from 'node:crypto';

export type DecisionMemoryStatus = 'ACTIVE' | 'SUPERSEDED' | 'INVALIDATED' | 'QUARANTINED';
export type OutcomeClass = 'SUCCESS' | 'COUNTEREXAMPLE';

export interface DecisionMemorySource {
  memoryId: string;
  portfolioId: string;
  strategyId: string;
  symbol: string;
  decisionAsOf: string;
  availableAt: string;
  outcomeRefs: readonly string[];
  evidenceIds: readonly string[];
  outcomeClass: OutcomeClass;
  status: DecisionMemoryStatus;
  memoryPolicyVersion: string;
}

export interface DecisionMemorySummary extends DecisionMemorySource { contentHash: string; }
export interface MemoryQuery { portfolioId: string; strategyId: string; symbol: string; availableAt: string; limit: number; successQuota: number; counterexampleQuota: number; }
export interface MemoryQueryResult { selected: readonly DecisionMemorySummary[]; excluded: Readonly<Record<string, string>>; }

export function projectDecisionMemory(source: DecisionMemorySource): DecisionMemorySummary {
  validateSource(source);
  return { ...source, contentHash: memoryHash(source) };
}

export class InMemoryDecisionMemoryProjection {
  private readonly values = new Map<string, DecisionMemorySummary>();

  public project(source: DecisionMemorySource): DecisionMemorySummary {
    const summary = projectDecisionMemory(source);
    this.values.set(summary.memoryId, structuredClone(summary));
    return summary;
  }

  public delete(memoryId: string): void { this.values.delete(memoryId); }

  public query(query: MemoryQuery): MemoryQueryResult {
    const excluded: Record<string, string> = {};
    const candidates = [...this.values.values()].filter((memory) => {
      const reason = exclusionReason(memory, query);
      if (reason) { excluded[memory.memoryId] = reason; return false; }
      return true;
    }).sort((left, right) => left.decisionAsOf.localeCompare(right.decisionAsOf) || left.memoryId.localeCompare(right.memoryId));
    const successes = candidates.filter((memory) => memory.outcomeClass === 'SUCCESS').slice(0, query.successQuota);
    const counterexamples = candidates.filter((memory) => memory.outcomeClass === 'COUNTEREXAMPLE').slice(0, query.counterexampleQuota);
    const selected = [...successes, ...counterexamples].slice(0, query.limit);
    for (const memory of candidates) if (!selected.some((item) => item.memoryId === memory.memoryId)) excluded[memory.memoryId] = 'QUOTA_OR_LIMIT';
    return { selected, excluded };
  }
}

function exclusionReason(memory: DecisionMemorySummary, query: MemoryQuery): string | undefined {
  if (memory.portfolioId !== query.portfolioId) return 'PORTFOLIO_SCOPE';
  if (memory.strategyId !== query.strategyId || memory.symbol !== query.symbol) return 'STRUCTURED_FILTER';
  if (memory.availableAt > query.availableAt) return 'FUTURE';
  if (memory.status !== 'ACTIVE') return 'STATUS';
  if (memory.contentHash !== memoryHash(memory)) return 'HASH_MISMATCH';
  return undefined;
}

function validateSource(source: DecisionMemorySource): void {
  if (!source.memoryId || !source.portfolioId || !source.strategyId || !source.symbol || !source.memoryPolicyVersion) throw new Error('decision memory requires identifiers and policy version');
  if (!source.outcomeRefs.length || !source.evidenceIds.length) throw new Error('decision memory requires outcome and evidence references');
  if (source.availableAt < source.decisionAsOf) throw new Error('memory availableAt cannot precede decisionAsOf');
}

function memoryHash(source: Omit<DecisionMemorySummary, 'contentHash'> | DecisionMemorySummary): string {
  const canonical = JSON.stringify(source, (key, value: unknown) => key === 'contentHash' ? undefined : value);
  return createHash('sha256').update(canonical).digest('hex');
}
