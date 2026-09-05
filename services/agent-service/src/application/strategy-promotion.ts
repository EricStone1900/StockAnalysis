import { createHash } from 'node:crypto';

export type PromotionStatus = 'SELECTED' | 'VALIDATED' | 'SHADOW' | 'APPROVED' | 'ACTIVE' | 'REJECTED' | 'SUSPENDED';
export interface ValidationGates { pit: boolean; outOfSample: boolean; walkForward: boolean; cost: boolean; turnover: boolean; capacity: boolean; regime: boolean; correlation: boolean; }
export interface ResearchExperiment { experimentId: string; draftId: string; candidateStrategyVersion: string; status: PromotionStatus; validation?: ValidationGates; approvalId?: string; contentHash: string; }

export function createResearchExperiment(draftId: string, candidateStrategyVersion: string, humanSelectionId: string): ResearchExperiment {
  if (!draftId || !candidateStrategyVersion || !humanSelectionId) throw new Error('experiment requires explicit human selection');
  return update({ experimentId: `experiment:${draftId}:${candidateStrategyVersion}`, draftId, candidateStrategyVersion, status: 'SELECTED' }, humanSelectionId);
}

export function recordIndependentValidation(experiment: ResearchExperiment, validation: ValidationGates): ResearchExperiment {
  if (experiment.status !== 'SELECTED') throw new Error('only SELECTED experiments can be validated');
  const passed = Object.values(validation).every(Boolean);
  return update({ ...experiment, status: passed ? 'VALIDATED' : 'REJECTED', validation }, experiment.approvalId);
}

export function enterShadow(experiment: ResearchExperiment): ResearchExperiment {
  if (experiment.status !== 'VALIDATED') throw new Error('only VALIDATED experiments can enter shadow');
  return update({ ...experiment, status: 'SHADOW' }, experiment.approvalId);
}

export function approveShadow(experiment: ResearchExperiment, approvalId: string): ResearchExperiment {
  if (experiment.status !== 'SHADOW') throw new Error('only SHADOW experiments can be approved');
  if (!approvalId) throw new Error('human approval id is required');
  return update({ ...experiment, status: 'APPROVED', approvalId }, approvalId);
}

export function activateApproved(experiment: ResearchExperiment, approvalId: string): ResearchExperiment {
  if (experiment.status !== 'APPROVED') throw new Error('only APPROVED experiments can activate');
  if (!approvalId || approvalId !== experiment.approvalId) throw new Error('activation requires matching human approval');
  return update({ ...experiment, status: 'ACTIVE' }, approvalId);
}

export function suspendActive(experiment: ResearchExperiment, reason: string): ResearchExperiment {
  if (experiment.status !== 'ACTIVE' || !reason.trim()) throw new Error('only ACTIVE experiments can be suspended with a reason');
  return update({ ...experiment, status: 'SUSPENDED' }, reason);
}

function update(experiment: Omit<ResearchExperiment, 'contentHash'>, salt?: string): ResearchExperiment {
  const payload = JSON.stringify({ ...experiment, salt });
  return { ...experiment, contentHash: createHash('sha256').update(payload).digest('hex') };
}
