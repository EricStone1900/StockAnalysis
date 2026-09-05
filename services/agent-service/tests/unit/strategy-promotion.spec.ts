import { describe, expect, it } from 'vitest';
import { activateApproved, approveShadow, createResearchExperiment, enterShadow, recordIndependentValidation, suspendActive } from '../../src/application/strategy-promotion.js';

const passed = { pit: true, outOfSample: true, walkForward: true, cost: true, turnover: true, capacity: true, regime: true, correlation: true };

describe('strategy promotion state machine', () => {
  it('requires independent validation, shadow, and human approval before activation', () => {
    let experiment = createResearchExperiment('draft-1', 'candidate-v2', 'selection-1');
    experiment = recordIndependentValidation(experiment, passed);
    experiment = enterShadow(experiment);
    experiment = approveShadow(experiment, 'approval-1');
    experiment = activateApproved(experiment, 'approval-1');
    expect(experiment.status).toBe('ACTIVE');
    expect(experiment.contentHash).toHaveLength(64);
  });

  it('rejects validation failures and never auto-promotes them', () => {
    const experiment = createResearchExperiment('draft-2', 'candidate-v3', 'selection-2');
    const rejected = recordIndependentValidation(experiment, { ...passed, capacity: false });
    expect(rejected.status).toBe('REJECTED');
    expect(() => enterShadow(rejected)).toThrow('VALIDATED');
  });

  it('requires a matching approval and supports explicit suspension', () => {
    let experiment = enterShadow(recordIndependentValidation(createResearchExperiment('draft-3', 'candidate-v4', 'selection-3'), passed));
    experiment = approveShadow(experiment, 'approval-3');
    expect(() => activateApproved(experiment, 'other-approval')).toThrow('matching');
    experiment = activateApproved(experiment, 'approval-3');
    expect(suspendActive(experiment, 'drift threshold breached').status).toBe('SUSPENDED');
  });
});
