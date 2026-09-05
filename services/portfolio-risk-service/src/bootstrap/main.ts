import { BadRequestException, Body, ConflictException, Controller, ForbiddenException, Get, Headers, Injectable, Module, NotFoundException, OnApplicationShutdown, Param, Post, UnauthorizedException } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';
import { Pool } from 'pg';
import { readFile } from 'node:fs/promises';
import { CashDividendCommand, ConfirmedFillCommand, OpeningSnapshotCommand, PortfolioLedger, ReversalCommand, StockSplitCommand } from '../domain/portfolio.js';
import { PortfolioService } from '../application/portfolio-service.js';
import type { RiskEvaluationInput } from '../domain/risk-policy.js';
import { PostgresPortfolioRepository } from '../infrastructure/postgres-portfolio-repository.js';
import { OutboxWorkerLifecycle } from '../application/outbox-publisher.js';
import { ResourceReservationService } from '../application/resource-reservation-service.js';
import { PostgresResourceReservationRepository } from '../infrastructure/postgres-resource-reservation-repository.js';
import type { ResourceReservationRequest, ResourceReservationStatus } from '@stock/contracts';
import { connect, type NatsConnection } from 'nats';
import { ExecutionEventHandler } from '../application/execution-event-handler.js';
import { ExecutionEventRuntime, JetStreamExecutionSubscription } from '../application/execution-event-runtime.js';
import { PostgresExecutionInboxRepository } from '../infrastructure/postgres-execution-inbox-repository.js';

const serviceName = 'portfolio-risk-service';
const databasePool = process.env.PORTFOLIO_DATABASE_URL ? new Pool({ connectionString: process.env.PORTFOLIO_DATABASE_URL, max: 5 }) : undefined;
let natsConnection: NatsConnection | undefined;
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
  async onApplicationShutdown(): Promise<void> { if (process.env.NODE_ENV !== 'test' && natsConnection) await natsConnection.drain(); if (process.env.NODE_ENV !== 'test' && databasePool) await databasePool.end(); }
}
@Controller('/api/v1/portfolios')
export class PortfolioController {
  constructor(private readonly service: Pick<PortfolioService, 'importOpening' | 'latest'> & Partial<Pick<PortfolioService, 'reverse' | 'evaluateRisk'>> = portfolioService) {}

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

  @Post(':portfolioId/risk-evaluations')
  async evaluateRisk(@Param('portfolioId') portfolioId: string, @Body() body: Omit<RiskEvaluationInput, 'portfolio' | 'portfolioId'>) {
    try {
      if (!this.service.evaluateRisk) throw new BadRequestException('risk evaluation is not configured');
      return await this.service.evaluateRisk({ ...body, portfolioId });
    } catch (error) {
      if (error instanceof BadRequestException) throw error;
      if (error instanceof Error && error.message === 'portfolio snapshot not found') throw new NotFoundException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid risk evaluation');
    }
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
@Controller('/internal/v1/reconciliation')
export class ReconciliationController {
  constructor(private readonly service: Pick<PortfolioService, 'recordConfirmedFill' | 'recordCashDividend' | 'recordStockSplit'> = portfolioService) {}

  @Post('apply-confirmed-fill')
  async applyConfirmedFill(@Headers('Idempotency-Key') idempotencyKey: string | undefined, @Headers('X-Actor-Id') actorId: string | undefined, @Headers('X-Correlation-Id') correlationId: string | undefined, @Body() body: ConfirmedFillCommand) {
    try {
      if (!idempotencyKey || idempotencyKey !== body.idempotencyKey) throw new BadRequestException('Idempotency-Key must match body.idempotencyKey');
      if (!actorId || actorId !== body.actorId) throw new ForbiddenException('X-Actor-Id must match body.actorId');
      if (!correlationId) throw new BadRequestException('X-Correlation-Id is required');
      return await this.service.recordConfirmedFill({ ...body, correlationId });
    } catch (error) {
      if (error instanceof ForbiddenException || error instanceof ConflictException || error instanceof BadRequestException) throw error;
      if (error instanceof Error && error.message === 'ledger version conflict') throw new ConflictException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid confirmed fill');
    }
  }

  @Post('apply-cash-dividend')
  async applyCashDividend(@Headers('Idempotency-Key') idempotencyKey: string | undefined, @Headers('X-Actor-Id') actorId: string | undefined, @Headers('X-Correlation-Id') correlationId: string | undefined, @Body() body: CashDividendCommand) {
    try {
      if (!idempotencyKey || idempotencyKey !== body.idempotencyKey) throw new BadRequestException('Idempotency-Key must match body.idempotencyKey');
      if (!actorId || actorId !== body.actorId) throw new ForbiddenException('X-Actor-Id must match body.actorId');
      if (!correlationId) throw new BadRequestException('X-Correlation-Id is required');
      return await this.service.recordCashDividend({ ...body, correlationId });
    } catch (error) {
      if (error instanceof ForbiddenException || error instanceof ConflictException || error instanceof BadRequestException) throw error;
      if (error instanceof Error && error.message === 'ledger version conflict') throw new ConflictException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid cash dividend');
    }
  }

  @Post('apply-stock-split')
  async applyStockSplit(@Headers('Idempotency-Key') idempotencyKey: string | undefined, @Headers('X-Actor-Id') actorId: string | undefined, @Headers('X-Correlation-Id') correlationId: string | undefined, @Body() body: StockSplitCommand) {
    try {
      if (!idempotencyKey || idempotencyKey !== body.idempotencyKey) throw new BadRequestException('Idempotency-Key must match body.idempotencyKey');
      if (!actorId || actorId !== body.actorId) throw new ForbiddenException('X-Actor-Id must match body.actorId');
      if (!correlationId) throw new BadRequestException('X-Correlation-Id is required');
      return await this.service.recordStockSplit({ ...body, correlationId });
    } catch (error) {
      if (error instanceof ForbiddenException || error instanceof ConflictException || error instanceof BadRequestException) throw error;
      if (error instanceof Error && error.message === 'ledger version conflict') throw new ConflictException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid stock split');
    }
  }
}
function createPortfolioService(): PortfolioService {
  const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
  if (!databaseUrl) return new PortfolioService(new PortfolioLedger());
  return new PortfolioService(new PortfolioLedger(), new PostgresPortfolioRepository(databasePool ?? new Pool({ connectionString: databaseUrl, max: 5 })));
}
const portfolioService = createPortfolioService();
const resourceReservationService = new ResourceReservationService({ latest: (portfolioId) => portfolioService.latest(portfolioId) }, databasePool ? new PostgresResourceReservationRepository(databasePool) : undefined);
const executionEventHandler = new ExecutionEventHandler(portfolioService, resourceReservationService, databasePool ? new PostgresExecutionInboxRepository(databasePool) : undefined);
@Injectable() class PortfolioInternalTokenGuard { check(token: string | undefined): void { const expected = process.env.PORTFOLIO_INTERNAL_TOKEN; if (!expected || token !== expected) throw new UnauthorizedException('invalid portfolio service identity'); } }
@Controller('/internal/v1/portfolio-reservations')
export class ResourceReservationController {
  constructor(private readonly guard = new PortfolioInternalTokenGuard()) {}
  @Post()
  async reserve(@Headers('Idempotency-Key') idempotencyKey: string | undefined, @Headers('x-service-token') serviceToken: string | undefined, @Body() body: ResourceReservationRequest) {
    this.guard.check(serviceToken);
    try { if (!idempotencyKey || idempotencyKey !== body.idempotencyKey) throw new BadRequestException('Idempotency-Key must match body.idempotencyKey'); return await resourceReservationService.reserve(body); }
    catch (error) { if (error instanceof Error && /conflict|active|insufficient/.test(error.message)) throw new ConflictException(error.message); throw new BadRequestException(error instanceof Error ? error.message : 'invalid resource reservation'); }
  }
  @Post(':reservationId/status')
  async transition(@Param('reservationId') reservationId: string, @Headers('x-service-token') serviceToken: string | undefined, @Body() body: { status: ResourceReservationStatus }) {
    this.guard.check(serviceToken);
    try { return await resourceReservationService.transition(reservationId, body.status); }
    catch (error) { throw new BadRequestException(error instanceof Error ? error.message : 'invalid resource reservation transition'); }
  }
  @Get(':reservationId')
  async get(@Param('reservationId') reservationId: string, @Headers('x-service-token') serviceToken: string | undefined) { this.guard.check(serviceToken); const reservation = await resourceReservationService.get(reservationId); if (!reservation) throw new NotFoundException('resource reservation not found'); return reservation; }
}
export class AppModule {}
Module({ controllers: [HealthController, PortfolioController, ReconciliationController, ResourceReservationController], providers: [DatabaseLifecycle, OutboxWorkerLifecycle] })(AppModule);
async function bootstrap() {
  const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName });
  await migratePortfolioDatabase();
  const app = await NestFactory.create(AppModule, new FastifyAdapter());
  app.enableShutdownHooks();
  if (process.env.NATS_URL) { natsConnection = await connect({ servers: process.env.NATS_URL }); const manager = await natsConnection.jetstreamManager(); try { await manager.streams.add({ name: 'STOCK_EXECUTION', subjects: ['stock.trade-execution.>'] }); } catch { /* 已存在时复用 */ } await new ExecutionEventRuntime(new JetStreamExecutionSubscription(natsConnection), executionEventHandler).start(); }
  await app.listen(config.PORT, '0.0.0.0');
  log('service.started', { service: serviceName });
}
async function migratePortfolioDatabase(): Promise<void> {
  const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
  if (!databaseUrl) return;
  const pool = new Pool({ connectionString: databaseUrl, max: 1 });
  try {
    for (const migration of ['001_portfolio_ledger.sql', '002_resource_reservations.sql', '003_execution_inbox.sql']) await pool.query(await readFile(new URL(`../../migrations/${migration}`, import.meta.url), 'utf8'));
  } finally {
    await pool.end();
  }
}
if (process.env.NODE_ENV !== 'test') void bootstrap();
