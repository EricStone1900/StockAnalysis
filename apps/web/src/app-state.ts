export type Route = 'dashboard' | 'unknown';
export type AuthStatus = 'AUTHENTICATED' | 'ANONYMOUS';

export function routeFor(pathname: string): Route {
  return pathname === '/' || pathname === '/dashboard' ? 'dashboard' : 'unknown';
}

export function authStatus(actorId: string | null): AuthStatus {
  return actorId?.trim() ? 'AUTHENTICATED' : 'ANONYMOUS';
}
