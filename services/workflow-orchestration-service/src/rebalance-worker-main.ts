import { NativeConnection, Worker } from '@temporalio/worker';
import { HttpRebalanceExecutionActivities } from './activities/real-rebalance-activities.js';

function required(name: string): string { const value = process.env[name]; if (!value) throw new Error(`${name} is required for real rebalance worker`); return value; }
async function run(): Promise<void> {
  const connection = await NativeConnection.connect({ address: process.env.TEMPORAL_ADDRESS ?? 'localhost:7233' });
  const activities = new HttpRebalanceExecutionActivities({ governanceBaseUrl: required('GOVERNANCE_BASE_URL'), portfolioBaseUrl: required('PORTFOLIO_BASE_URL'), executionBaseUrl: required('EXECUTION_BASE_URL'), governanceToken: required('GOVERNANCE_INTERNAL_TOKEN'), portfolioToken: required('PORTFOLIO_INTERNAL_TOKEN'), executionToken: required('EXECUTION_SERVICE_TOKEN') });
  const worker = await Worker.create({ connection, taskQueue: process.env.REBALANCE_TASK_QUEUE ?? 'stock-rebalance-v1', workflowsPath: new URL('./workflows/index.ts', import.meta.url).pathname, activities: { reserveBudget: activities.reserveBudget.bind(activities), createRebalanceBatch: activities.createRebalanceBatch.bind(activities), createManualOrderIntents: activities.createManualOrderIntents.bind(activities), recordFills: activities.recordFills.bind(activities), releaseBudget: activities.releaseBudget.bind(activities) } });
  await worker.run();
}
void run();
