import { describe, expect, it } from 'vitest';
import { readNatsRuntimeConfig } from '../../src/application/nats-config.js';

describe('NATS runtime config', () => {
  it('未配置时默认禁用，配置合法 URL 时启用', () => {
    expect(readNatsRuntimeConfig({})).toEqual({ enabled: false });
    expect(readNatsRuntimeConfig({ NATS_URL: 'nats://nats:4222' })).toEqual({ enabled: true, url: 'nats://nats:4222' });
  });
  it('拒绝空白或非法 URL', () => { expect(readNatsRuntimeConfig({ NATS_URL: '  ' })).toEqual({ enabled: false }); expect(() => readNatsRuntimeConfig({ NATS_URL: 'nats host' })).toThrow('valid URL'); });
});
