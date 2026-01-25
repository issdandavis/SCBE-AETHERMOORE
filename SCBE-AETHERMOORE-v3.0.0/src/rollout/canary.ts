type Level = 5 | 25 | 50 | 100;
type ProviderId = string;

export class CanaryManager {
  private levels = new Map<ProviderId, Level>();
  private lastChange = new Map<ProviderId, number>();
  private soakMs: [number, number]; // min,max

  constructor(soakWindow: [number, number] = [30*60_000, 60*60_000]) {
    this.soakMs = soakWindow;
  }

  getLevel(id: ProviderId): Level {
    return this.levels.get(id) ?? 5;
  }

  canAdvance(id: ProviderId): boolean {
    const last = this.lastChange.get(id) ?? 0;
    const elapsed = Date.now() - last;
    return elapsed >= this.soakMs[0];
  }

  advance(id: ProviderId) {
    const order: Level[] = [5,25,50,100];
    const cur = this.getLevel(id);
    const idx = order.indexOf(cur);
    if (idx < order.length - 1) {
      this.levels.set(id, order[idx+1]);
      this.lastChange.set(id, Date.now());
    }
  }

  rollback(id: ProviderId) {
    this.levels.set(id, 5);
    this.lastChange.set(id, Date.now());
  }
}
