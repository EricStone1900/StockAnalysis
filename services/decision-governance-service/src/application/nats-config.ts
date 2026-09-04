export interface NatsRuntimeConfig { readonly enabled: boolean; readonly url?: string; }

export function readNatsRuntimeConfig(env: NodeJS.ProcessEnv): NatsRuntimeConfig {
  const url = env.NATS_URL?.trim();
  if (!url) return { enabled: false };
  if (!/^\w+:\/\/[^\s]+$/.test(url)) throw new Error('NATS_URL must be a valid URL');
  return { enabled: true, url };
}
