import { NatsJetStreamPublisher, OutboxPublisher, OutboxWorker, type JetStreamConnection } from './outbox-publisher.js';
import type { OutboxStore } from './outbox-publisher.js';

export interface OutboxRuntime { readonly worker: OutboxWorker; readonly publisher: OutboxPublisher; }

/** 生产组合根使用此工厂；NATS 连接由部署层建立并传入。 */
export function createOutboxRuntime(store: OutboxStore, connection: JetStreamConnection, intervalMs = 5_000): OutboxRuntime {
  const publisher = new OutboxPublisher(store, new NatsJetStreamPublisher(connection));
  return { publisher, worker: new OutboxWorker(publisher, intervalMs) };
}
