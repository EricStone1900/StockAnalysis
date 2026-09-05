import { NativeConnection, Worker } from '@temporalio/worker';
import { FakeWorkflowActivities } from './activities/fake-activities.js';
import { WORKFLOW_TASK_QUEUE } from './workflow-contract.js';

async function run(): Promise<void> {
  const connection = await NativeConnection.connect({ address: process.env.TEMPORAL_ADDRESS ?? 'localhost:7233' });
  const activities = new FakeWorkflowActivities();
  const worker = await Worker.create({ connection, taskQueue: process.env.WORKFLOW_TASK_QUEUE ?? WORKFLOW_TASK_QUEUE, workflowsPath: new URL('./workflows/health.workflow.ts', import.meta.url).pathname, activities });
  await worker.run();
}
void run();
