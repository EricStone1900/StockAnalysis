export type ActivityFailureCategory = 'VALIDATION' | 'DEPENDENCY' | 'TIMEOUT' | 'INTERNAL';
export function isRetryable(category: ActivityFailureCategory): boolean { return category === 'DEPENDENCY' || category === 'TIMEOUT'; }
