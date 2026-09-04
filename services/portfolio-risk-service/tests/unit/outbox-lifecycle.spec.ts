import { describe, expect, it, vi } from 'vitest';
import { OutboxWorkerLifecycle } from '../../src/application/outbox-publisher.js';

describe('OutboxWorkerLifecycle', () => {
  it('在应用启动和关闭时转发 Worker 生命周期', () => {
    const worker = { start: vi.fn(), stop: vi.fn() };
    const lifecycle = new OutboxWorkerLifecycle(worker);
    lifecycle.onApplicationBootstrap();
    lifecycle.onApplicationShutdown();
    expect(worker.start).toHaveBeenCalledOnce();
    expect(worker.stop).toHaveBeenCalledOnce();
  });

  it('未配置 Worker 时安全空操作', () => {
    expect(() => { new OutboxWorkerLifecycle().onApplicationBootstrap(); new OutboxWorkerLifecycle().onApplicationShutdown(); }).not.toThrow();
  });
});
