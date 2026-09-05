import { describe, expect, it } from 'vitest';
import { InMemoryDecisionMemoryProjection, projectDecisionMemory, type DecisionMemorySource } from '../../src/application/decision-memory.js';

const source = (memoryId: string, outcomeClass: 'SUCCESS' | 'COUNTEREXAMPLE', overrides: Partial<DecisionMemorySource> = {}): DecisionMemorySource => ({
  memoryId, portfolioId: 'portfolio-1', strategyId: 'strategy-1', symbol: 'SSE:600000', decisionAsOf: '2026-09-01T08:00:00Z', availableAt: '2026-09-03T08:00:00Z',
  outcomeRefs: [`outcome:${memoryId}`], evidenceIds: [`evidence:${memoryId}`], outcomeClass, status: 'ACTIVE', memoryPolicyVersion: 'memory-v1', ...overrides,
});
const query = { portfolioId: 'portfolio-1', strategyId: 'strategy-1', symbol: 'SSE:600000', availableAt: '2026-09-05T08:00:00Z', limit: 3, successQuota: 1, counterexampleQuota: 1 };

describe('Decision Memory projection', () => {
  it('excludes future, cross-portfolio, invalid-status, and tampered memories', () => {
    const projection = new InMemoryDecisionMemoryProjection();
    projection.project(source('active', 'SUCCESS'));
    projection.project(source('future', 'SUCCESS', { availableAt: '2026-09-06T08:00:00Z' }));
    projection.project(source('other-portfolio', 'SUCCESS', { portfolioId: 'portfolio-2' }));
    projection.project(source('invalid', 'SUCCESS', { status: 'INVALIDATED' }));
    projection.project(source('tampered', 'SUCCESS'));
    const values = (projection as unknown as { values: Map<string, { contentHash: string }> }).values;
    values.get('tampered')!.contentHash = '0'.repeat(64);
    const result = projection.query(query);
    expect(result.selected.map((memory) => memory.memoryId)).toEqual(['active']);
    expect(result.excluded).toMatchObject({ future: 'FUTURE', 'other-portfolio': 'PORTFOLIO_SCOPE', invalid: 'STATUS', tampered: 'HASH_MISMATCH' });
  });

  it('returns both successful and counterexample samples within quotas', () => {
    const projection = new InMemoryDecisionMemoryProjection();
    projection.project(source('success-1', 'SUCCESS'));
    projection.project(source('success-2', 'SUCCESS', { decisionAsOf: '2026-09-02T08:00:00Z' }));
    projection.project(source('counter-1', 'COUNTEREXAMPLE'));
    const result = projection.query(query);
    expect(result.selected.map((memory) => memory.outcomeClass).sort()).toEqual(['COUNTEREXAMPLE', 'SUCCESS']);
    expect(result.excluded['success-2']).toBe('QUOTA_OR_LIMIT');
  });

  it('can delete and rebuild the same deterministic projection hash', () => {
    const projection = new InMemoryDecisionMemoryProjection();
    const original = projection.project(source('rebuild', 'SUCCESS'));
    projection.delete('rebuild');
    const rebuilt = projection.project(source('rebuild', 'SUCCESS'));
    expect(rebuilt.contentHash).toBe(original.contentHash);
    expect(projectDecisionMemory(source('rebuild', 'SUCCESS')).contentHash).toBe(original.contentHash);
  });
});
