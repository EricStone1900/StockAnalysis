import { describe, expect, it } from 'vitest';
import { buildGoldenFixtureCatalog, evaluateGoldenRuns, mergeReviewerVerdicts, type GoldenRunResult } from '../../src/application/golden-evaluation.js';

describe('golden evaluation', () => {
  it('builds ten versioned safety fixtures for each of six agents', () => {
    const fixtures = buildGoldenFixtureCatalog();
    expect(fixtures).toHaveLength(60);
    for (const agentId of ['stock-analysis', 'financial-news', 'market-monitor', 'market-state', 'main-decision', 'risk-review']) {
      expect(fixtures.filter((fixture) => fixture.agentId === agentId)).toHaveLength(10);
    }
    expect(fixtures.every((fixture) => fixture.fixtureVersion === 'v1' && fixture.allowedEvidenceIds.length > 0)).toBe(true);
  });

  it('blocks release on schema, evidence, safety, or reason-code regression', () => {
    const fixtures = buildGoldenFixtureCatalog().slice(0, 2);
    const runs: GoldenRunResult[] = fixtures.map((fixture) => ({ fixtureId: fixture.fixtureId, schemaValid: true, evidenceIds: fixture.allowedEvidenceIds, safetyAssertionsPassed: true, reasonCodes: fixture.keyReasonCodes }));
    const pass = evaluateGoldenRuns(fixtures, runs, { agentVersion: 'v1', promptVersion: 'v1', modelProfile: 'deepseek', fixtureVersion: 'v1' });
    expect(pass.releaseBlocked).toBe(false);
    const failed = evaluateGoldenRuns(fixtures, [{ ...runs[0], evidenceIds: ['evidence:not-provided'] }, runs[1]], { agentVersion: 'v1', promptVersion: 'v1', modelProfile: 'deepseek', fixtureVersion: 'v1' });
    expect(failed.releaseBlocked).toBe(true);
    expect(failed.failedFixtureIds).toContain(fixtures[0].fixtureId);
  });

  it('merges cross-model review conservatively', () => {
    expect(mergeReviewerVerdicts(['PASS', 'PASS_WITH_CONDITIONS'])).toBe('PASS_WITH_CONDITIONS');
    expect(mergeReviewerVerdicts(['PASS', 'REJECT'])).toBe('REJECT');
    expect(mergeReviewerVerdicts([])).toBe('INSUFFICIENT_EVIDENCE');
  });
});
