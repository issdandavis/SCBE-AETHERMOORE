type State = 'closed' | 'open' | 'half-open';

export class CircuitBreaker {
  private state: State = 'closed';
  private openedAt = 0;
  constructor(
    private failRateThreshold = 0.005,
    private windowMs = 300_000
  ) {}

  getState() {
    return this.state;
  }

  evaluate(failureRate: number) {
    if (this.state === 'open') return;
    if (failureRate > this.failRateThreshold) {
      this.state = 'open';
      this.openedAt = Date.now();
    }
  }

  halfOpenIfReady() {
    if (this.state === 'open' && Date.now() - this.openedAt > this.windowMs) {
      this.state = 'half-open';
    }
  }

  close() {
    this.state = 'closed';
    this.openedAt = 0;
  }
}
