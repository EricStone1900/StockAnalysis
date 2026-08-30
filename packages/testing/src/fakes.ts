export class FakeEventPublisher<T> {
  readonly events: T[] = [];
  async publish(event: T): Promise<void> { this.events.push(event); }
}

export class FakeHttpServer {
  readonly requests: Array<{ path: string; status: number }> = [];
  respond(path: string, status = 200): { status: number } { this.requests.push({ path, status }); return { status }; }
}
