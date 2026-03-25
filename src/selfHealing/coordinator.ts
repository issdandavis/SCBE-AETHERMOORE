import { QuickFixBot } from './quickFixBot.js';
import { DeepHealing } from './deepHealing.js';
import { Failure } from './types.js';

export class HealingCoordinator {
  private quick = new QuickFixBot();
  private deep = new DeepHealing();

  async handleFailure(failure: Failure) {
    const quick = await this.quick.attemptFix(failure);
    const deep = await this.deep.diagnose(failure);
    // Coordination policy: prefer deep when available; cherry-pick quick successes
    return { quick, deep, decision: 'prefer_deep_if_ready' as const };
  }
}
