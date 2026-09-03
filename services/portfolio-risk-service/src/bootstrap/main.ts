import { BadRequestException, Body, ConflictException, Controller, ForbiddenException, Get, Headers, Injectable, Module, NotFoundException, OnApplicationShutdown, Param, Post } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';
import { Pool } from 'pg';
import { readFile } from 'node:fs/promises';
import { OpeningSnapshotCommand, PortfolioLedger, ReversalCommand } from '../domain/portfolio.js';
import { PortfolioService } from '../application/portfolio-service.js';
import { PostgresPortfolioRepository } from '../infrastructure/postgres-portfolio-repository.js';

const serviceName = 'portfolio-risk-service';
const databasePool = process.env.PORTFOLIO_DATABASE_URL ? new Pool({ connectionString: process.env.PORTFOLIO_DATABASE_URL, max: 5 }) : undefined;
@Controller()
export class HealthController {
  @Get('/live') live() { return { status: 'UP' }; }
  @Get('/ready') async ready() {
    if (!databasePool) return { status: 'UP', dependencies: { postgres: 'NOT_CONFIGURED' } };
    try { await databasePool.query('SELECT 1'); return { status: 'UP', dependencies: { postgres: 'UP' } }; }
    catch { return { status: 'DOWN', dependencies: { postgres: 'DOWN' } }; }
  }
  @Get('/metrics') metrics() { return ''; }
  @Get('/version') version() { return { service: serviceName, version: '0.1.0' }; }
}
@Injectable()
class DatabaseLifecycle implements OnApplicationShutdown {
  async onApplicationShutdown(): Promise<void> { if (process.env.NODE_ENV !== 'test' && databasePool) await databasePool.end(); }
}
@Controller('/api/v1/portfolios')
export class PortfolioController {
  constructor(private readonly service: Pick<PortfolioService, 'importOpening' | 'latest'> & Partial<Pick<PortfolioService, 'reverse'>> = createPortfolioService()) {}

  @Post(':portfolioId/manual-snapshots')
  async importOpening(@Param('portfolioId') portfolioId: string, @Headers('Idempotency-Key') idempotencyKey: string | undefined, @Headers('X-Actor-Id') actorId: string | undefined, @Headers('X-Correlation-Id') correlationId: string | undefined, @Body() body: Omit<OpeningSnapshotCommand, 'portfolioId'>) {
    try {
      if (!idempotencyKey || idempotencyKey !== body.idempotencyKey) throw new BadRequestException('Idempotency-Key must match body.idempotencyKey');
      if (!actorId || actorId !== body.actorId) throw new ForbiddenException('X-Actor-Id must match body.actorId');
      if (!correlationId) throw new BadRequestException('X-Correlation-Id is required');
      return await this.service.importOpening({ ...body, portfolioId, correlationId });
    } catch (error) {
      if (error instanceof ForbiddenException || error instanceof ConflictException || error instanceof BadRequestException) throw error;
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

  @Post(':portfolioId/ledger-entries/:entryId/reversals')
  async reverse(@Param('portfolioId') portfolioId: string, @Param('entryId') entryId: string, @Headers('Idempotency-Key') idempotencyKey: string | undefined, @Headers('X-Actor-Id') actorId: string | undefined, @Headers('X-Correlation-Id') correlationId: string | undefined, @Body() body: Omit<ReversalCommand, 'portfolioId' | 'originalEntryId'>) {
    try {
      if (!idempotencyKey || idempotencyKey !== body.idempotencyKey) throw new BadRequestException('Idempotency-Key must match body.idempotencyKey');
      if (!actorId || actorId !== body.actorId) throw new ForbiddenException('X-Actor-Id must match body.actorId');
      if (!correlationId) throw new BadRequestException('X-Correlation-Id is required');
      if (!this.service.reverse) throw new BadRequestException('reversal is not configured');
      return await this.service.reverse({ ...body, portfolioId, originalEntryId: entryId, correlationId });
    } catch (error) {
      if (error instanceof ForbiddenException || error instanceof ConflictException || error instanceof BadRequestException) throw error;
      if (error instanceof Error && error.message === 'ledger version conflict') throw new ConflictException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid reversal');
    }
  }
}
function createPortfolioService(): PortfolioService {
  const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
  if (!databaseUrl) return new PortfolioService(new PortfolioLedger());
  return new PortfolioService(new PortfolioLedger(), new PostgresPortfolioRepository(databasePool ?? new Pool({ connectionString: databaseUrl, max: 5 })));
}
export class AppModule {}
Module({ controllers: [HealthController, PortfolioController], providers: [DatabaseLifecycle] })(AppModule);
async function bootstrap() {
  const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName });
  await migratePortfolioDatabase();
  const app = await NestFactory.create(AppModule, new FastifyAdapter());
  app.enableShutdownHooks();
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
