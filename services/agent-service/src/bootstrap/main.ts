import { Body, Controller, Get, Module, Post } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { readServiceConfig } from '@stock/config';
import { log } from '@stock/observability';
import { Pool } from 'pg';
import { readFile } from 'node:fs/promises';
import { FakeAnalysisEntrypoints, type FakeAnalysisCommand } from '../application/agent-entrypoints.js';
import { readAgentDeployment } from '../application/deployment-config.js';
import { PostgresAgentRunRepository } from '../infrastructure/postgres-agent-run-repository.js';

const serviceName = 'agent-service';
const databasePool = process.env.AGENT_DATABASE_URL ? new Pool({ connectionString: process.env.AGENT_DATABASE_URL, max: 5 }) : undefined;
const entrypoints = new FakeAnalysisEntrypoints(databasePool ? new PostgresAgentRunRepository(databasePool) : undefined);

@Controller()
class HealthController {
  @Get('/live') live() { return { status: 'UP' }; }
  @Get('/ready') ready() { return { status: 'UP', dependencies: {} }; }
  @Get('/metrics') metrics() { return ''; }
  @Get('/version') version() { return { service: serviceName, version: '0.1.0' }; }
}

@Controller('/internal/v1/agent-runs')
class AgentRunController {
  @Post('/fake-analysis')
  async runFake(@Body() command: FakeAnalysisCommand) { return await entrypoints.execute(command); }
}

@Module({ controllers: [HealthController, AgentRunController] }) class AppModule {}
async function bootstrap() { const config = readServiceConfig({ ...process.env, SERVICE_NAME: serviceName }); const deployment = readAgentDeployment(process.env); if (databasePool) await databasePool.query(await readFile(new URL('../../migrations/001_agent_runs.sql', import.meta.url), 'utf8')); const app = await NestFactory.create(AppModule, new FastifyAdapter()); await app.listen(config.PORT, '0.0.0.0'); log('service.started', { service: serviceName, agentId: deployment.agentId, taskQueue: deployment.taskQueue }); }
if (process.env.NODE_ENV !== 'test') void bootstrap();
