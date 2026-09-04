import { Controller, Get, Headers, Module } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { GeneratedMarketDataClient } from '@stock/contracts';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';

import { DashboardFacade } from '../application/dashboard-facade.js';

const serviceName = 'platform-api-service';
const dashboardFacade = new DashboardFacade(new GeneratedMarketDataClient(process.env.MARKET_DATA_SERVICE_URL ?? 'http://localhost:3000'));

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
  async dashboard(@Headers('x-actor-id') actorId = 'anonymous', @Headers('x-roles') roles = '') {
    return await dashboardFacade.latest({ actorId, roles: roles.split(',').filter(Boolean) });
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
