import 'reflect-metadata';
import { Module } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ExecutionController } from '../../src/bootstrap/main.js';
import { ExecutionService } from '../../src/application/execution-service.js';
import { ExecutionWriteGuard } from '../../src/application/execution-write-guard.js';

@Module({ controllers: [ExecutionController], providers: [ExecutionWriteGuard, { provide: ExecutionService, useFactory: () => new ExecutionService() }] })
class TestModule {}

describe('HTTP执行边界', () => {
  afterEach(() => vi.unstubAllEnvs());
  it('实际路由拒绝无身份写入，匹配服务身份仍不能绕过业务授权', async () => {
    const token = 'test-only-http-identity'.repeat(3);
    vi.stubEnv('EXECUTION_SERVICE_TOKEN', token);
    const adapter = new FastifyAdapter();
    const app = await NestFactory.create(TestModule, adapter, { logger: false });
    try {
      await app.init();
      const unauthenticated = await adapter.getInstance().inject({ method: 'POST', url: '/api/v1/execution/batches', payload: {} });
      expect(unauthenticated.statusCode).toBe(401);
      const authenticated = await adapter.getInstance().inject({ method: 'POST', url: '/api/v1/execution/batches', headers: { authorization: `Bearer ${token}` }, payload: {} });
      expect(authenticated.statusCode).toBe(503);
      expect(authenticated.json().message).toContain('authorization adapter');
    } finally { await app.close(); }
  });
});
