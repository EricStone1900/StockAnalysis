import type { AutoExecutionPolicy } from './broker-auto-execution.js';

export interface AutoExecutionConfig { readonly approvalReference?: string; readonly policy: AutoExecutionPolicy; }

const disabledPolicy: AutoExecutionPolicy = { enabled: false, allowedAccountIds: [], allowedSecurityIds: [], allowedStrategyVersions: [], maxBatchNotional: 0, maxOrderNotional: 0, sessionStartUtc: '00:00', sessionEndUtc: '00:00', killSwitchOpen: true };

/** 默认关闭；启用时必须提供人工签署的审批引用和精确白名单。 */
export function readAutoExecutionConfig(environment: NodeJS.ProcessEnv): AutoExecutionConfig {
  if (environment.AUTO_EXECUTION_ENABLED !== 'true') return { policy: disabledPolicy };
  const approvalReference = required(environment, 'AUTO_EXECUTION_APPROVAL_REFERENCE');
  const sessionStartUtc = required(environment, 'AUTO_EXECUTION_SESSION_START_UTC');
  const sessionEndUtc = required(environment, 'AUTO_EXECUTION_SESSION_END_UTC');
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(sessionStartUtc) || !/^([01]\d|2[0-3]):[0-5]\d$/.test(sessionEndUtc) || sessionStartUtc > sessionEndUtc) throw new Error('invalid auto execution session');
  return { approvalReference, policy: { enabled: true, allowedAccountIds: list(environment, 'AUTO_EXECUTION_ALLOWED_ACCOUNTS'), allowedSecurityIds: list(environment, 'AUTO_EXECUTION_ALLOWED_SECURITIES'), allowedStrategyVersions: list(environment, 'AUTO_EXECUTION_ALLOWED_STRATEGY_VERSIONS'), maxBatchNotional: positive(environment, 'AUTO_EXECUTION_MAX_BATCH_NOTIONAL'), maxOrderNotional: positive(environment, 'AUTO_EXECUTION_MAX_ORDER_NOTIONAL'), sessionStartUtc, sessionEndUtc, killSwitchOpen: true } };
}

function required(environment: NodeJS.ProcessEnv, name: string): string { const value = environment[name]?.trim(); if (!value) throw new Error(`${name} is required when auto execution is enabled`); return value; }
function list(environment: NodeJS.ProcessEnv, name: string): readonly string[] { const values = required(environment, name).split(',').map((value) => value.trim()).filter(Boolean); if (values.length === 0) throw new Error(`${name} must not be empty`); return values; }
function positive(environment: NodeJS.ProcessEnv, name: string): number { const value = Number(required(environment, name)); if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be positive`); return value; }
