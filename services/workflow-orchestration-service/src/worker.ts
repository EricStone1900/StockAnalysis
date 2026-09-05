import { NativeConnection, Worker } from '@temporalio/worker';
import { FakeDailyQuantActivities, FakeNewsAnalysisActivities, FakeWorkflowActivities } from './activities/fake-activities.js';
import { WORKFLOW_TASK_QUEUE } from './workflow-contract.js';

async function run(): Promise<void> {
  const connection = await NativeConnection.connect({ address: process.env.TEMPORAL_ADDRESS ?? 'localhost:7233' });
  const healthActivities = new FakeWorkflowActivities();
  const quantActivities = new FakeDailyQuantActivities();
  const newsActivities = new FakeNewsAnalysisActivities();
  const activities = { verifyDependency: healthActivities.verifyDependency.bind(healthActivities), waitForDataVersion: quantActivities.waitForDataVersion.bind(quantActivities), runDailyAnalysis: quantActivities.runDailyAnalysis.bind(quantActivities), runActiveStrategy: quantActivities.runActiveStrategy.bind(quantActivities), publishSnapshots: quantActivities.publishSnapshots.bind(quantActivities), collectNews: newsActivities.collectNews.bind(newsActivities), buildCandidate: newsActivities.buildCandidate.bind(newsActivities), analyzeNewsAgent: newsActivities.analyzeNewsAgent.bind(newsActivities), publishFinancialNewsEvent: newsActivities.publishFinancialNewsEvent.bind(newsActivities) };
  const worker = await Worker.create({ connection, taskQueue: process.env.WORKFLOW_TASK_QUEUE ?? WORKFLOW_TASK_QUEUE, workflowsPath: new URL('./workflows/health.workflow.ts', import.meta.url).pathname, activities });
  await worker.run();
}
void run();
