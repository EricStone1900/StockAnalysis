import { Controller, Get, Headers, Module } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { GeneratedMarketDataClient } from '@stock/contracts';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';

import { DashboardFacade } from '../application/dashboard-facade.js';
import { createAudit, InMemoryAuditRepository, principalFromHeaders } from '../application/security.js';

const serviceName = 'platform-api-service';
const dashboardFacade = new DashboardFacade(new GeneratedMarketDataClient(process.env.MARKET_DATA_SERVICE_URL ?? 'http://localhost:3000'));
const auditRepository = new InMemoryAuditRepository();

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
    const principal = principalFromHeaders(actorId, roles);
    const result = await dashboardFacade.latest(principal);
    auditRepository.append(createAudit({ requestId, correlationId, actorId: principal.actorId, action: 'dashboard.read' }));
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
  await app.listen(config.PORT, '0.0.0.0');
  log('service.started', { service: serviceName });
}

if (process.env.NODE_ENV !== 'test') void bootstrap();
