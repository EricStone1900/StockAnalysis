import { BadRequestException, Body, ConflictException, Controller, Get, Injectable, Module, NotFoundException, Optional, Param, Post } from '@nestjs/common'; import { NestFactory } from '@nestjs/core'; import { FastifyAdapter } from '@nestjs/platform-fastify'; import { readServiceConfig } from '@stock/config'; import { log } from '@stock/observability'; import { Pool } from 'pg'; import { readFile } from 'node:fs/promises';
import { GovernanceService } from '../application/governance-service.js'; import type { CreateProposalCommand } from '../domain/proposal.js';
import { PostgresProposalRepository } from '../infrastructure/postgres-proposal-repository.js';
const serviceName = 'decision-governance-service';
const databasePool = process.env.DECISION_GOVERNANCE_DATABASE_URL ? new Pool({ connectionString: process.env.DECISION_GOVERNANCE_DATABASE_URL, max: 5 }) : undefined;
@Controller() class HealthController { @Get('/live') live() { return { status: 'UP' }; } @Get('/ready') ready() { return { status: 'UP', dependencies: {} }; } @Get('/metrics') metrics() { return ''; } @Get('/version') version() { return { service: serviceName, version: '0.1.0' }; } }
@Controller('/api/v1/proposals') export class ProposalController {
  public constructor(@Optional() private readonly service: GovernanceService = governanceService) {}
  @Post() async create(@Body() body: CreateProposalCommand) { try { return await this.service.createDraft(body); } catch (error) { if (error instanceof Error && error.message.includes('version conflict')) throw new ConflictException(error.message); throw new BadRequestException(error instanceof Error ? error.message : 'invalid proposal'); } }
  @Get(':proposalId') async get(@Param('proposalId') proposalId: string) { const proposal = await this.service.getProposal(proposalId); if (!proposal) throw new NotFoundException('proposal not found'); return proposal; }
}
const governanceService = databasePool ? new GovernanceService(undefined, new PostgresProposalRepository(databasePool)) : new GovernanceService();
@Injectable() class DatabaseLifecycle { async onApplicationShutdown(): Promise<void> { if (process.env.NODE_ENV !== 'test' && databasePool) await databasePool.end(); } }
@Module({ controllers: [HealthController, ProposalController], providers: [{ provide: GovernanceService, useFactory: () => governanceService }, DatabaseLifecycle] }) class AppModule {}
async function bootstrap() { const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName }); if (databasePool) await databasePool.query(await readFile(new URL('../../migrations/001_proposals.sql', import.meta.url), 'utf8')); const app = await NestFactory.create(AppModule, new FastifyAdapter()); app.enableShutdownHooks(); await app.listen(config.PORT, '0.0.0.0'); log('service.started', { service: serviceName }); }
if (process.env.NODE_ENV !== 'test') void bootstrap();
