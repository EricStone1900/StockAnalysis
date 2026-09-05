import { Controller, ForbiddenException, Get, Headers, Module, NotFoundException, Param } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { GeneratedMarketDataClient } from '@stock/contracts';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';

import { DashboardFacade } from '../application/dashboard-facade.js';
import { createAudit, InMemoryAuditRepository, principalFromHeaders } from '../application/security.js';
import { compatibleVersion, readFeatureFlags, securityHeaders } from '../application/compatibility.js';
import { ProblemDetailsFilter } from '../application/problem-details.filter.js';

const serviceName = 'platform-api-service';
const dashboardFacade = new DashboardFacade(
  new GeneratedMarketDataClient(process.env.MARKET_DATA_SERVICE_URL ?? 'http://localhost:3000'),
  process.env.AGENT_SERVICE_URL ?? 'http://localhost:3010',
);
const auditRepository = new InMemoryAuditRepository();
const featureFlags = readFeatureFlags(process.env);

@Controller()
class HealthController {
  @Get('/live') live() { return { status: 'UP' }; }
  @Get('/ready') ready() { return { status: 'UP', dependencies: {} }; }
  @Get('/metrics') metrics() { return ''; }
  @Get('/version') version() { return { service: serviceName, version: '0.1.0' }; }
}

@Controller('/api/v1')
class DashboardController {
  @Get('/dashboard')
  async dashboard(@Headers('x-actor-id') actorId: string | undefined, @Headers('x-roles') roles: string | undefined, @Headers('x-request-id') requestId = 'generated-request-id', @Headers('x-correlation-id') correlationId = requestId) {
    if (!featureFlags.dashboard) return { status: 'UNAVAILABLE', errorCode: 'FEATURE_DISABLED' };
    const principal = principalFromHeaders(actorId, roles);
    const result = await dashboardFacade.latest(principal);
    auditRepository.append(createAudit({ requestId, correlationId, actorId: principal.actorId, action: 'dashboard.read' }));
    return result;
  }

  @Get('/compatibility')
  compatibility(@Headers('x-client-version') clientVersion: string | undefined) {
    return { compatible: compatibleVersion(clientVersion), apiVersion: 'v1', featureFlags };
  }

  @Get('/agent-runs/:correlationId')
  async agentRun(@Param('correlationId') correlationId: string, @Headers('x-actor-id') actorId: string | undefined, @Headers('x-roles') roles: string | undefined) {
    const principal = principalFromHeaders(actorId, roles);
    if (!principal.roles.includes('RESEARCH_READ')) throw new ForbiddenException('missing role: RESEARCH_READ');
    const result = await dashboardFacade.agentRun(correlationId, principal);
    if (!result) throw new NotFoundException('AGENT_RUN_NOT_FOUND');
    return result;
  }

  @Get('/audit/events')
  audit(@Headers('x-roles') roles: string | undefined) {
    return roles?.split(',').map((role) => role.trim()).includes('ADMIN') ? { events: auditRepository.list() } : { events: [] };
  }
}

@Module({ controllers: [HealthController, DashboardController] })
class AppModule {}

async function bootstrap() {
  const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName });
  const app = await NestFactory.create(AppModule, new FastifyAdapter());
  app.useGlobalFilters(new ProblemDetailsFilter());
  app.getHttpAdapter().getInstance().addHook('onSend', async (_request: unknown, reply: { header: (name: string, value: string) => void }) => {
    for (const [name, value] of Object.entries(securityHeaders())) reply.header(name, value);
  });
  await app.listen(config.PORT, '0.0.0.0');
  log('service.started', { service: serviceName });
}

if (process.env.NODE_ENV !== 'test') void bootstrap();
