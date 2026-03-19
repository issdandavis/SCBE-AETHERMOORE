/**
 * @file energy-token.unit.test.ts
 * @module tests/L2-unit/game
 * @layer Layer 12, Layer 13
 *
 * Tests for Energy Token system (Human Currency → Compute Bridge).
 * Verifies: token packages, purchases, consumption, refunds, wallet queries.
 */

import { describe, it, expect } from 'vitest';
import {
  SECONDS_PER_TOKEN,
  TOKEN_PACKAGES,
  ACTIVITY_COSTS,
  EnergyWallet,
} from '../../../src/game/energyToken.js';

// ===========================================================================
//  Token Packages
// ===========================================================================

describe('Token Packages', () => {
  it('has 4 packages', () => {
    expect(TOKEN_PACKAGES).toHaveLength(4);
  });

  it('packages have increasing token counts', () => {
    for (let i = 1; i < TOKEN_PACKAGES.length; i++) {
      expect(TOKEN_PACKAGES[i].tokens).toBeGreaterThan(TOKEN_PACKAGES[i - 1].tokens);
    }
  });

  it('packages have increasing prices', () => {
    for (let i = 1; i < TOKEN_PACKAGES.length; i++) {
      expect(TOKEN_PACKAGES[i].priceUsd).toBeGreaterThan(TOKEN_PACKAGES[i - 1].priceUsd);
    }
  });

  it('larger packages have better per-token rates', () => {
    const rates = TOKEN_PACKAGES.map((p) => p.priceUsd / (p.tokens + p.bonusTokens));
    for (let i = 1; i < rates.length; i++) {
      expect(rates[i]).toBeLessThan(rates[i - 1]);
    }
  });

  it('each package has a unique ID', () => {
    const ids = TOKEN_PACKAGES.map((p) => p.packageId);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

// ===========================================================================
//  Activity Costs
// ===========================================================================

describe('Activity Costs', () => {
  it('all activities have positive base costs', () => {
    for (const [key, cost] of Object.entries(ACTIVITY_COSTS)) {
      expect(cost.baseCost).toBeGreaterThan(0);
      expect(cost.activityType).toBe(key);
    }
  });

  it('world_simulation is the most expensive', () => {
    const max = Math.max(...Object.values(ACTIVITY_COSTS).map((c) => c.baseCost));
    expect(ACTIVITY_COSTS.world_simulation.baseCost).toBe(max);
  });

  it('codex_deep_query is the cheapest', () => {
    const min = Math.min(...Object.values(ACTIVITY_COSTS).map((c) => c.baseCost));
    expect(ACTIVITY_COSTS.codex_deep_query.baseCost).toBe(min);
  });
});

// ===========================================================================
//  Energy Wallet — Purchases
// ===========================================================================

describe('EnergyWallet — Purchases', () => {
  it('starts with zero balance', () => {
    const wallet = new EnergyWallet('player-1');
    expect(wallet.balance).toBe(0);
    expect(wallet.totalPurchased).toBe(0);
    expect(wallet.totalConsumed).toBe(0);
  });

  it('records a purchase and mints tokens', () => {
    const wallet = new EnergyWallet('player-1');
    const record = wallet.recordPurchase('starter', 'pi_stripe_123');

    expect(record).not.toBeNull();
    expect(record!.tokensMinted).toBe(100); // starter = 100 + 0 bonus
    expect(record!.priceUsd).toBe(4.99);
    expect(record!.status).toBe('completed');
    expect(wallet.balance).toBe(100);
    expect(wallet.totalPurchased).toBe(100);
  });

  it('includes bonus tokens', () => {
    const wallet = new EnergyWallet('player-1');
    const record = wallet.recordPurchase('adventurer', 'pi_stripe_456');

    expect(record).not.toBeNull();
    expect(record!.tokensMinted).toBe(550); // 500 + 50 bonus
    expect(wallet.balance).toBe(550);
  });

  it('rejects invalid package ID', () => {
    const wallet = new EnergyWallet('player-1');
    const record = wallet.recordPurchase('nonexistent', 'pi_stripe_789');
    expect(record).toBeNull();
    expect(wallet.balance).toBe(0);
  });

  it('accumulates multiple purchases', () => {
    const wallet = new EnergyWallet('player-1');
    wallet.recordPurchase('starter', 'pi_1');
    wallet.recordPurchase('adventurer', 'pi_2');

    expect(wallet.balance).toBe(650); // 100 + 550
    expect(wallet.totalPurchased).toBe(650);
    expect(wallet.getPurchases()).toHaveLength(2);
  });

  it('purchase IDs are unique', () => {
    const wallet = new EnergyWallet('player-1');
    const r1 = wallet.recordPurchase('starter', 'pi_1');
    const r2 = wallet.recordPurchase('starter', 'pi_2');
    expect(r1!.purchaseId).not.toBe(r2!.purchaseId);
  });
});

// ===========================================================================
//  Energy Wallet — Consumption
// ===========================================================================

describe('EnergyWallet — Consumption', () => {
  function fundedWallet(): EnergyWallet {
    const wallet = new EnergyWallet('player-1');
    wallet.recordPurchase('adventurer', 'pi_1'); // 550 tokens
    return wallet;
  }

  it('checks affordability', () => {
    const wallet = fundedWallet();
    expect(wallet.canAfford('dungeon_run')).toBe(true); // 20 tokens
    expect(wallet.canAfford('world_simulation')).toBe(true); // 100 tokens
    expect(wallet.canAfford('nonexistent_activity')).toBe(false);
  });

  it('consumes tokens for an activity', () => {
    const wallet = fundedWallet();
    const record = wallet.consume('dungeon_run', 'comp-1', 'session-1');

    expect(record).not.toBeNull();
    expect(record!.tokensSpent).toBe(20);
    expect(wallet.balance).toBe(530); // 550 - 20
    expect(wallet.totalConsumed).toBe(20);
  });

  it('rejects consumption with insufficient balance', () => {
    const wallet = new EnergyWallet('player-1');
    wallet.recordPurchase('starter', 'pi_1'); // 100 tokens

    const record = wallet.consume('world_simulation', null, 'session-1'); // costs 100
    expect(record).not.toBeNull();
    expect(wallet.balance).toBe(0);

    // Now try again with 0 balance
    const record2 = wallet.consume('codex_deep_query', null, 'session-2');
    expect(record2).toBeNull();
  });

  it('rejects unknown activity type', () => {
    const wallet = fundedWallet();
    const record = wallet.consume('nonexistent', null, 'session-1');
    expect(record).toBeNull();
  });

  it('tracks training data generation', () => {
    const wallet = fundedWallet();
    wallet.consume('dungeon_run', 'comp-1', 'session-1', true, 'hf-dataset-1');
    wallet.consume('tower_floor', 'comp-1', 'session-1', false);

    const training = wallet.getTrainingConsumptions();
    expect(training).toHaveLength(1);
    expect(training[0].hfDatasetId).toBe('hf-dataset-1');
  });

  it('multiple consumptions drain balance correctly', () => {
    const wallet = fundedWallet(); // 550
    wallet.consume('dungeon_run', 'comp-1', 's1'); // -20 → 530
    wallet.consume('tower_floor', 'comp-1', 's1'); // -15 → 515
    wallet.consume('companion_training', 'comp-1', 's1'); // -30 → 485
    expect(wallet.balance).toBe(485);
    expect(wallet.totalConsumed).toBe(65);
    expect(wallet.getConsumptions()).toHaveLength(3);
  });
});

// ===========================================================================
//  Energy Wallet — Refunds
// ===========================================================================

describe('EnergyWallet — Refunds', () => {
  it('refunds unspent tokens', () => {
    const wallet = new EnergyWallet('player-1');
    const purchase = wallet.recordPurchase('starter', 'pi_1')!;

    const result = wallet.processRefund(purchase.purchaseId);
    expect(result.refunded).toBe(true);
    expect(result.tokensReclaimed).toBe(100);
    expect(wallet.balance).toBe(0);
  });

  it('partial refund when some tokens spent', () => {
    const wallet = new EnergyWallet('player-1');
    const purchase = wallet.recordPurchase('starter', 'pi_1')!; // 100 tokens
    wallet.consume('dungeon_run', null, 's1'); // spend 20

    const result = wallet.processRefund(purchase.purchaseId);
    expect(result.refunded).toBe(true);
    expect(result.tokensReclaimed).toBe(80); // min(100, 80) = 80
    expect(wallet.balance).toBe(0);
  });

  it('rejects refund for unknown purchase', () => {
    const wallet = new EnergyWallet('player-1');
    const result = wallet.processRefund('nonexistent');
    expect(result.refunded).toBe(false);
  });

  it('rejects double refund', () => {
    const wallet = new EnergyWallet('player-1');
    const purchase = wallet.recordPurchase('starter', 'pi_1')!;
    wallet.processRefund(purchase.purchaseId);

    const result = wallet.processRefund(purchase.purchaseId);
    expect(result.refunded).toBe(false);
  });
});

// ===========================================================================
//  Energy Wallet — Compute Hours
// ===========================================================================

describe('EnergyWallet — Compute Hours', () => {
  it('calculates purchased compute hours', () => {
    const wallet = new EnergyWallet('player-1');
    wallet.recordPurchase('starter', 'pi_1'); // 100 tokens

    // 100 tokens × 60 seconds / 3600 = 1.667 hours
    expect(wallet.computeHoursPurchased()).toBeCloseTo((100 * 60) / 3600, 5);
  });

  it('calculates consumed compute hours', () => {
    const wallet = new EnergyWallet('player-1');
    wallet.recordPurchase('starter', 'pi_1');
    wallet.consume('dungeon_run', null, 's1'); // 20 tokens

    expect(wallet.computeHoursConsumed()).toBeCloseTo((20 * 60) / 3600, 5);
  });

  it('summary includes all fields', () => {
    const wallet = new EnergyWallet('player-1');
    wallet.recordPurchase('starter', 'pi_1');
    wallet.consume('dungeon_run', 'comp-1', 's1', true);

    const s = wallet.summary();
    expect(s.balance).toBe(80);
    expect(s.totalPurchased).toBe(100);
    expect(s.totalConsumed).toBe(20);
    expect(s.purchaseCount).toBe(1);
    expect(s.activityCount).toBe(1);
    expect(s.trainingDataGenerated).toBe(1);
    expect(s.computeHoursRemaining).toBeGreaterThan(0);
  });
});
