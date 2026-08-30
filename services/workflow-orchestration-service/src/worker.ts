import { NativeConnection, Worker } from '@temporalio/worker';

async function run(): Promise<void> {
  const connection = await NativeConnection.connect({ address: process.env.TEMPORAL_ADDRESS ?? 'localhost:7233' });
  const worker = await Worker.create({ connection, taskQueue: 'stock-platform', workflowsPath: new URL('./workflows/health.workflow.ts', import.meta.url).pathname, activities: { verify: async () => 'UP' } });
  await worker.run();
}
void run();
