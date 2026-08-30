import { AsyncLocalStorage } from 'node:async_hooks';

export interface TraceContext { correlationId: string; causationId?: string; traceparent?: string; }
export interface LogFields { [key: string]: unknown; }
const contextStore = new AsyncLocalStorage<TraceContext>();
const sensitiveKey = /(token|password|secret|database_?url|broker|prompt|restricted.*body)/i;

export function withTraceContext<T>(context: TraceContext, work: () => T): T { return contextStore.run(context, work); }
export function currentTraceContext(): TraceContext | undefined { return contextStore.getStore(); }
export function redact(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, sensitiveKey.test(key) ? '[REDACTED]' : redact(item)]));
  return value;
}
export function log(event: string, fields: LogFields = {}): void {
  process.stdout.write(`${JSON.stringify(redact({ level: 'info', event, ...currentTraceContext(), ...fields }))}\n`);
}
export function readiness(dependencies: Record<string, boolean>): { status: 'UP' | 'DOWN'; dependencies: Record<string, boolean> } {
  return { status: Object.values(dependencies).every(Boolean) ? 'UP' : 'DOWN', dependencies };
}
export function prometheusMetrics(values: Record<string, number>): string { return Object.entries(values).map(([name, value]) => `${name} ${value}`).join('\n'); }
