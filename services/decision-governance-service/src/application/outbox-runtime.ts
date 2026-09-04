import type { GovernanceOutboxRecord } from '../infrastructure/governance-outbox-repository.js';
import { GovernanceOutboxWorker } from './outbox-worker.js';

export interface GovernanceJetStreamConnection { jetstream(): { publish(subject: string, payload: Uint8Array): Promise<unknown> } }
export class GovernanceNatsPublisher { public constructor(private readonly connection: GovernanceJetStreamConnection) {} public async publish(event: GovernanceOutboxRecord): Promise<void> { await this.connection.jetstream().publish(event.subject, new TextEncoder().encode(JSON.stringify(event.payload))); } }
export class GovernanceOutboxRuntime { public readonly worker: GovernanceOutboxWorker; public constructor(store: ConstructorParameters<typeof GovernanceOutboxWorker>[0], connection: GovernanceJetStreamConnection) { this.worker = new GovernanceOutboxWorker(store, new GovernanceNatsPublisher(connection)); } }
export class GovernanceWorkerLifecycle { public constructor(private readonly worker?: { start(): void; stop(): void }) {} public onApplicationBootstrap(): void { this.worker?.start(); } public onApplicationShutdown(): void { this.worker?.stop(); } }
