import { expect, it } from 'vitest';
import { blocksWorkflow, isRetryable } from '../../src/activity-errors.js';

it('retries only explicitly retryable activity failures', () => {
  expect(isRetryable('RETRYABLE')).toBe(true);
  expect(isRetryable('NON_RETRYABLE')).toBe(false);
  expect(blocksWorkflow('BLOCKED')).toBe(true);
  expect(blocksWorkflow('CANCELLED')).toBe(true);
});
