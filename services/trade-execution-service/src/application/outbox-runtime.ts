import type { ExecutionOutboxRecord } from './outbox-worker.js';
export interface ExecutionJetStreamConnection { jetstream(): { publish(subject: string, payload: Uint8Array): Promise<unknown> } }
export class ExecutionNatsPublisher { public constructor(private readonly connection: ExecutionJetStreamConnection) {} public async publish(event: ExecutionOutboxRecord): Promise<void> { const envelope = event.payload && typeof event.payload === 'object' && 'eventId' in event.payload && 'subject' in event.payload ? event.payload : event; await this.connection.jetstream().publish(event.subject, new TextEncoder().encode(JSON.stringify(envelope))); } }
export class ExecutionWorkerLifecycle { public constructor(private readonly worker?: { start(): void; stop(): void }) {} public onApplicationBootstrap(): void { this.worker?.start(); } public onApplicationShutdown(): void { this.worker?.stop(); } }
export class ExecutionOutboxScheduler {
  private timer?: ReturnType<typeof setInterval>;
  constructor(private readonly worker: { publishBatch(limit?: number): Promise<unknown> }, private readonly intervalMs = 1000) {}
  start(): void { if (this.timer) return; void this.worker.publishBatch(); this.timer = setInterval(() => void this.worker.publishBatch(), this.intervalMs); }
  stop(): void { if (this.timer) clearInterval(this.timer); this.timer = undefined; }
}
