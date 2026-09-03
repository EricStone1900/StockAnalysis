import { BadRequestException, Body, ConflictException, Controller, Get, Module, NotFoundException, Param, Post } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';
import { OpeningSnapshotCommand, PortfolioLedger } from '../domain/portfolio.js';
import { PortfolioService } from '../application/portfolio-service.js';

const serviceName = 'portfolio-risk-service';
@Controller()
class HealthController {
  @Get('/live') live() { return { status: 'UP' }; }
  @Get('/ready') ready() { return { status: 'UP', dependencies: {} }; }
  @Get('/metrics') metrics() { return ''; }
  @Get('/version') version() { return { service: serviceName, version: '0.1.0' }; }
}
@Controller('/api/v1/portfolios')
class PortfolioController {
  private readonly service = new PortfolioService(new PortfolioLedger());

  @Post(':portfolioId/manual-snapshots')
  importOpening(@Param('portfolioId') portfolioId: string, @Body() body: Omit<OpeningSnapshotCommand, 'portfolioId'>) {
    try {
      return this.service.importOpening({ ...body, portfolioId });
    } catch (error) {
      if (error instanceof Error && error.message === 'ledger version conflict') throw new ConflictException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid opening snapshot');
    }
  }

  @Get(':portfolioId/snapshots/latest')
  latest(@Param('portfolioId') portfolioId: string) {
    const snapshot = this.service.latest(portfolioId);
    if (!snapshot) throw new NotFoundException('snapshot not found');
    return snapshot;
  }
}
@Module({ controllers: [HealthController, PortfolioController] }) class AppModule {}
async function bootstrap() { const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName }); const app = await NestFactory.create(AppModule, new FastifyAdapter()); await app.listen(config.PORT, '0.0.0.0'); log('service.started', { service: serviceName }); }
void bootstrap();
