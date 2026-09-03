import { BadRequestException, Body, ConflictException, Controller, Get, Headers, Module, NotFoundException, Param, Post } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';
import { Pool } from 'pg';
import { readFile } from 'node:fs/promises';
import { OpeningSnapshotCommand, PortfolioLedger } from '../domain/portfolio.js';
import { PortfolioService } from '../application/portfolio-service.js';
import { PostgresPortfolioRepository } from '../infrastructure/postgres-portfolio-repository.js';

const serviceName = 'portfolio-risk-service';
@Controller()
class HealthController {
  @Get('/live') live() { return { status: 'UP' }; }
  @Get('/ready') ready() { return { status: 'UP', dependencies: {} }; }
  @Get('/metrics') metrics() { return ''; }
  @Get('/version') version() { return { service: serviceName, version: '0.1.0' }; }
}
@Controller('/api/v1/portfolios')
export class PortfolioController {
  constructor(private readonly service: Pick<PortfolioService, 'importOpening' | 'latest'> = createPortfolioService()) {}

  @Post(':portfolioId/manual-snapshots')
  async importOpening(@Param('portfolioId') portfolioId: string, @Headers('Idempotency-Key') idempotencyKey: string | undefined, @Body() body: Omit<OpeningSnapshotCommand, 'portfolioId'>) {
    try {
      if (!idempotencyKey || idempotencyKey !== body.idempotencyKey) throw new BadRequestException('Idempotency-Key must match body.idempotencyKey');
      return await this.service.importOpening({ ...body, portfolioId });
    } catch (error) {
      if (error instanceof Error && error.message === 'ledger version conflict') throw new ConflictException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid opening snapshot');
    }
  }

  @Get(':portfolioId/snapshots/latest')
  async latest(@Param('portfolioId') portfolioId: string) {
    const snapshot = await this.service.latest(portfolioId);
    if (!snapshot) throw new NotFoundException('snapshot not found');
    return snapshot;
  }
}
function createPortfolioService(): PortfolioService {
  const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
  if (!databaseUrl) return new PortfolioService(new PortfolioLedger());
  const pool = new Pool({ connectionString: databaseUrl, max: 5 });
  return new PortfolioService(new PortfolioLedger(), new PostgresPortfolioRepository(pool));
}
@Module({ controllers: [HealthController, PortfolioController] }) class AppModule {}
async function bootstrap() {
  const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName });
  await migratePortfolioDatabase();
  const app = await NestFactory.create(AppModule, new FastifyAdapter());
  await app.listen(config.PORT, '0.0.0.0');
  log('service.started', { service: serviceName });
}
async function migratePortfolioDatabase(): Promise<void> {
  const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
  if (!databaseUrl) return;
  const pool = new Pool({ connectionString: databaseUrl, max: 1 });
  try {
    await pool.query(await readFile(new URL('../../migrations/001_portfolio_ledger.sql', import.meta.url), 'utf8'));
  } finally {
    await pool.end();
  }
}
if (process.env.NODE_ENV !== 'test') void bootstrap();
