import { describe, expect, it } from 'vitest';
import { HealthController } from '../../src/bootstrap/main.js';

describe('HealthController', () => {
  it('reports local memory mode explicitly when database is not configured', async () => {
    const health = new HealthController();
    expect(await health.ready()).toEqual({ status: 'UP', dependencies: { postgres: 'NOT_CONFIGURED' } });
  });
});
