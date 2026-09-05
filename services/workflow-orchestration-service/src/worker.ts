import { NativeConnection, Worker } from '@temporalio/worker';
import { FakeDailyQuantActivities, FakeHumanApprovalActivities, FakeInvestmentDecisionActivities, FakeMarketMonitorActivities, FakeMarketRegimeActivities, FakeNewsAnalysisActivities, FakeRebalanceExecutionActivities, FakeWorkflowActivities } from './activities/fake-activities.js';
import { WORKFLOW_TASK_QUEUE } from './workflow-contract.js';

async function run(): Promise<void> {
  const connection = await NativeConnection.connect({ address: process.env.TEMPORAL_ADDRESS ?? 'localhost:7233' });
  const healthActivities = new FakeWorkflowActivities();
  const quantActivities = new FakeDailyQuantActivities();
  const newsActivities = new FakeNewsAnalysisActivities();
  const monitorActivities = new FakeMarketMonitorActivities();
  const regimeActivities = new FakeMarketRegimeActivities();
  const decisionActivities = new FakeInvestmentDecisionActivities();
  const approvalActivities = new FakeHumanApprovalActivities();
  const rebalanceActivities = new FakeRebalanceExecutionActivities();
  const activities = { verifyDependency: healthActivities.verifyDependency.bind(healthActivities), waitForDataVersion: quantActivities.waitForDataVersion.bind(quantActivities), runDailyAnalysis: quantActivities.runDailyAnalysis.bind(quantActivities), runActiveStrategy: quantActivities.runActiveStrategy.bind(quantActivities), publishSnapshots: quantActivities.publishSnapshots.bind(quantActivities), collectNews: newsActivities.collectNews.bind(newsActivities), buildCandidate: newsActivities.buildCandidate.bind(newsActivities), analyzeNewsAgent: newsActivities.analyzeNewsAgent.bind(newsActivities), publishFinancialNewsEvent: newsActivities.publishFinancialNewsEvent.bind(newsActivities), checkMarketOpen: monitorActivities.checkMarketOpen.bind(monitorActivities), loadAnomalySnapshot: monitorActivities.loadAnomalySnapshot.bind(monitorActivities), assessAnomaly: monitorActivities.assessAnomaly.bind(monitorActivities), publishMonitorAssessment: monitorActivities.publishMonitorAssessment.bind(monitorActivities), generateRegimeSnapshot: regimeActivities.generateRegimeSnapshot.bind(regimeActivities), analyzeMarketState: regimeActivities.analyzeMarketState.bind(regimeActivities), publishRegimeAssessment: regimeActivities.publishRegimeAssessment.bind(regimeActivities), validateDecisionGate: decisionActivities.validateDecisionGate.bind(decisionActivities), collectSpecialistEvidence: decisionActivities.collectSpecialistEvidence.bind(decisionActivities), runMainDecision: decisionActivities.runMainDecision.bind(decisionActivities), runRiskReview: decisionActivities.runRiskReview.bind(decisionActivities), runHardRiskEvaluation: decisionActivities.runHardRiskEvaluation.bind(decisionActivities), loadApprovalBundle: approvalActivities.loadApprovalBundle.bind(approvalActivities), recordApproval: approvalActivities.recordApproval.bind(approvalActivities), refreshApprovalBundle: approvalActivities.refreshApprovalBundle.bind(approvalActivities), reserveBudget: rebalanceActivities.reserveBudget.bind(rebalanceActivities), createRebalanceBatch: rebalanceActivities.createRebalanceBatch.bind(rebalanceActivities), createManualOrderIntents: rebalanceActivities.createManualOrderIntents.bind(rebalanceActivities), recordFills: rebalanceActivities.recordFills.bind(rebalanceActivities), releaseBudget: rebalanceActivities.releaseBudget.bind(rebalanceActivities) };
  const worker = await Worker.create({ connection, taskQueue: process.env.WORKFLOW_TASK_QUEUE ?? WORKFLOW_TASK_QUEUE, workflowsPath: new URL('./workflows/health.workflow.ts', import.meta.url).pathname, activities });
  await worker.run();
}
void run();
