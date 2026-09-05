export interface FeatureFlags {
  dashboard: boolean;
  realtime: boolean;
}

export function readFeatureFlags(env: Record<string, string | undefined>): FeatureFlags {
  return { dashboard: env.PLATFORM_FEATURE_DASHBOARD !== 'false', realtime: env.PLATFORM_FEATURE_REALTIME === 'true' };
}

export function compatibleVersion(clientVersion: string | undefined, supported = 'v1'): boolean {
  return !clientVersion || clientVersion === supported;
}

export function securityHeaders(): Record<string, string> {
  return { 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store' };
}
