import { describe, expect, it } from 'vitest';
import { checkCompatibility, fetchAgentRun, fetchConfiguredDashboard, fetchDashboard } from './dashboard-client.js';

const response = (status: number, body: unknown): Response => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

describe('dashboard query', () => {
  it('maps downstream failures to explicit UI states', async () => {
    expect((await fetchDashboard(async () => response(403, {}), 1)).status).toBe('FORBIDDEN');
    expect((await fetchDashboard(async () => response(503, {}), 1)).status).toBe('UNAVAILABLE');
    expect((await fetchDashboard(async () => { throw new Error('offline'); }, 1)).status).toBe('UNAVAILABLE');
  });

  it('marks stale data without replacing it with an empty object', async () => {
    const result = await fetchDashboard(async () => response(200, { dataVersion: { status: 'STALE' }, dailyAnalysisSnapshot: { status: 'UNAVAILABLE' }, services: {} }), 1);
    expect(result.status).toBe('STALE');
    expect(result.data?.dataVersion.status).toBe('STALE');
  });

  it('sends the explicit local read-only identity to the BFF', async () => {
    let headers: HeadersInit | undefined;
    await fetchDashboard(async (input, init) => {
      headers = init?.headers;
      return response(200, { dataVersion: { status: 'OK' }, dailyAnalysisSnapshot: { status: 'UNAVAILABLE' }, services: {} });
    }, 1);
    const normalized = new Headers(headers);
    expect(normalized.get('x-actor-id')).toBe('web-user');
    expect(normalized.get('x-roles')).toBe('RESEARCH_READ');
  });

  it('keeps the default path on the real BFF', async () => {
    const result = await fetchConfiguredDashboard(async () => response(503, {}));
    expect(result.status).toBe('UNAVAILABLE');
  });

  it('detects incompatible API versions', async () => {
    expect(await checkCompatibility(async () => response(200, { compatible: false }))).toBe(false);
    expect(await checkCompatibility(async () => response(200, { compatible: true }))).toBe(true);
  });

  it('reads an AgentRun through the BFF with the local read-only identity', async () => {
    let requestedUrl = '';
    const result = await fetchAgentRun('agent-run-1', async (input, init) => {
      requestedUrl = String(input);
      expect(new Headers(init?.headers).get('x-roles')).toBe('RESEARCH_READ');
      return response(200, { runId: 'agent-run-1', definitionId: 'stock-analysis:v1', correlationId: 'agent-run-1', modelRun: { provider: 'fake', modelId: 'fake', promptVersion: 'v1' }, toolCalls: [], output: {} });
    });
    expect(requestedUrl).toContain('/api/v1/agent-runs/agent-run-1');
    expect(result?.correlationId).toBe('agent-run-1');
    expect(await fetchAgentRun('missing', async () => response(404, {}))).toBeUndefined();
  });
});
