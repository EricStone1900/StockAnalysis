import { expect, it } from 'vitest';
import { isRetryable } from '../../src/activity-errors.js';
it('retries only dependency and timeout activity failures', () => { expect(isRetryable('DEPENDENCY')).toBe(true); expect(isRetryable('VALIDATION')).toBe(false); });
