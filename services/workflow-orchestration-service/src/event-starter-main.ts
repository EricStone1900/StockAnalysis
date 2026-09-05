import { Client, Connection } from '@temporalio/client';
import { connect } from 'nats';
import { RebalanceExecutionEventStarter } from './event-starter.js';

async function run(): Promise<void> {
  if (process.env.WORKFLOW_EVENT_STARTER_ENABLED !== 'true') throw new Error('WORKFLOW_EVENT_STARTER_ENABLED=true is required');
  const temporal = await Connection.connect({ address: process.env.TEMPORAL_ADDRESS ?? 'localhost:7233' });
  const nats = await connect({ servers: process.env.NATS_URL ?? 'nats://localhost:4222' });
  const starter = new RebalanceExecutionEventStarter(nats, await nats.jetstreamManager(), new Client({ connection: temporal }), process.env.REBALANCE_TASK_QUEUE ?? 'stock-rebalance-v1');
  await starter.start();
  const stop = async () => { await starter.stop(); await nats.drain(); await temporal.close(); };
  process.once('SIGTERM', () => void stop().finally(() => process.exit(0)));
  process.once('SIGINT', () => void stop().finally(() => process.exit(0)));
}

void run();
