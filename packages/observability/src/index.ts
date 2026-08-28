export interface LogFields { correlationId?: string; [key: string]: unknown; }

export function log(event: string, fields: LogFields = {}): void {
  process.stdout.write(`${JSON.stringify({ level: 'info', event, ...fields })}\n`);
}
