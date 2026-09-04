import { BadRequestException, Body, ConflictException, Controller, Get, Module, NotFoundException, Param, Post } from '@nestjs/common'; import { NestFactory } from '@nestjs/core'; import { FastifyAdapter } from '@nestjs/platform-fastify'; import { readServiceConfig } from '@stock/config'; import { log } from '@stock/observability';
import { GovernanceService } from '../application/governance-service.js'; import type { CreateProposalCommand } from '../domain/proposal.js';
const serviceName = 'decision-governance-service';
@Controller() class HealthController { @Get('/live') live() { return { status: 'UP' }; } @Get('/ready') ready() { return { status: 'UP', dependencies: {} }; } @Get('/metrics') metrics() { return ''; } @Get('/version') version() { return { service: serviceName, version: '0.1.0' }; } }
@Controller('/api/v1/proposals') export class ProposalController {
  public constructor(private readonly service = new GovernanceService()) {}
  @Post() create(@Body() body: CreateProposalCommand) { try { return this.service.createDraft(body); } catch (error) { if (error instanceof Error && error.message.includes('version conflict')) throw new ConflictException(error.message); throw new BadRequestException(error instanceof Error ? error.message : 'invalid proposal'); } }
  @Get(':proposalId') get(@Param('proposalId') proposalId: string) { const proposal = this.service.getProposal(proposalId); if (!proposal) throw new NotFoundException('proposal not found'); return proposal; }
}
@Module({ controllers: [HealthController, ProposalController] }) class AppModule {} async function bootstrap() { const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName }); const app = await NestFactory.create(AppModule, new FastifyAdapter()); await app.listen(config.PORT, '0.0.0.0'); log('service.started', { service: serviceName }); } if (process.env.NODE_ENV !== 'test') void bootstrap();
