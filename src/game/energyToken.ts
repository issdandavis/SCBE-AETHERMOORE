/**
 * @file energyToken.ts
 * @module game/energyToken
 * @layer Layer 12, Layer 13
 * @component Energy Token System — Human Currency → Compute Bridge
 *
 * Three-tier currency architecture:
 *   1. AI Coins (MMCCL Credits) — internal AI-to-AI barter, zero real value
 *   2. Energy Tokens (this file) — purchased with real money, spent on compute
 *   3. Human Currency (Stripe) — real money, standard refund policy
 *
 * Energy Tokens are NOT cryptocurrency. They are:
 *   - Non-tradeable (cannot be sent to another player)
 *   - Non-withdrawable (cannot be converted back to cash)
 *   - Non-transferable (bound to the purchasing account)
 *   - Consumed on use (like arcade tokens or prepaid server time)
 *
 * Legal model: prepaid compute credits, like AWS credits or game time cards.
 *
 * A3: Causality — all purchases and consumption are time-ordered.
 * A5: Composition — audit trail links Stripe payment → token mint → consumption.
 */

// Energy Tokens are independent from AI Coin system (microLedger).
// They exist in a separate namespace with no cross-trading.

// ---------------------------------------------------------------------------
//  Energy Token Constants
// ---------------------------------------------------------------------------

/** How many seconds of GPU compute one token buys */
export const SECONDS_PER_TOKEN = 60; // 1 token = 1 minute of compute

/** Token packages available for purchase */
export interface TokenPackage {
  readonly packageId: string;
  readonly name: string;
  readonly tokens: number;
  readonly priceUsd: number;
  readonly bonusTokens: number;
  readonly description: string;
}

export const TOKEN_PACKAGES: readonly TokenPackage[] = [
  {
    packageId: 'starter',
    name: 'Starter Pack',
    tokens: 100,
    priceUsd: 4.99,
    bonusTokens: 0,
    description: '100 Energy Tokens — ~5 dungeon runs',
  },
  {
    packageId: 'adventurer',
    name: 'Adventurer Pack',
    tokens: 500,
    priceUsd: 19.99,
    bonusTokens: 50,
    description: '550 Energy Tokens — ~25 dungeon runs + bonus',
  },
  {
    packageId: 'guild',
    name: 'Guild Pack',
    tokens: 2000,
    priceUsd: 49.99,
    bonusTokens: 400,
    description: '2400 Energy Tokens — ~100 dungeon runs + bonus',
  },
  {
    packageId: 'academy',
    name: 'Academy Semester',
    tokens: 10000,
    priceUsd: 199.99,
    bonusTokens: 3000,
    description: '13000 Energy Tokens — full semester of training + bonus',
  },
];

/** Compute costs for game activities (in tokens) */
export interface ActivityCost {
  readonly activityType: string;
  readonly baseCost: number;
  readonly description: string;
}

export const ACTIVITY_COSTS: Record<string, ActivityCost> = {
  dungeon_run: {
    activityType: 'dungeon_run',
    baseCost: 20,
    description: 'Run a dungeon floor (5 encounters + boss)',
  },
  tower_floor: {
    activityType: 'tower_floor',
    baseCost: 15,
    description: 'Attempt one tower floor',
  },
  companion_training: {
    activityType: 'companion_training',
    baseCost: 30,
    description: 'AI fine-tune session for one companion',
  },
  fleet_battle: {
    activityType: 'fleet_battle',
    baseCost: 10,
    description: 'Fleet formation battle',
  },
  codex_deep_query: {
    activityType: 'codex_deep_query',
    baseCost: 5,
    description: 'Extended codex research session',
  },
  evolution_ceremony: {
    activityType: 'evolution_ceremony',
    baseCost: 50,
    description: 'Evolution ceremony with model checkpoint',
  },
  world_simulation: {
    activityType: 'world_simulation',
    baseCost: 100,
    description: '24h autonomous world simulation tick',
  },
};

// ---------------------------------------------------------------------------
//  Purchase Record (audit trail)
// ---------------------------------------------------------------------------

export interface PurchaseRecord {
  readonly purchaseId: string;
  readonly playerId: string;
  readonly packageId: string;
  readonly tokensMinted: number;
  readonly priceUsd: number;
  readonly stripePaymentId: string;
  readonly timestamp: number;
  readonly status: 'completed' | 'refunded' | 'disputed';
}

// ---------------------------------------------------------------------------
//  Consumption Record (audit trail)
// ---------------------------------------------------------------------------

export interface ConsumptionRecord {
  readonly consumptionId: string;
  readonly playerId: string;
  readonly activityType: string;
  readonly tokensSpent: number;
  readonly companionId: string | null;
  readonly timestamp: number;
  readonly sessionId: string;
  /** Whether this consumption generated training data */
  readonly generatedTrainingData: boolean;
  /** HuggingFace dataset ID if training data was pushed */
  readonly hfDatasetId: string | null;
}

// ---------------------------------------------------------------------------
//  Energy Wallet
// ---------------------------------------------------------------------------

export class EnergyWallet {
  private _playerId: string;
  private _balance: number = 0;
  private _totalPurchased: number = 0;
  private _totalConsumed: number = 0;
  private _purchases: PurchaseRecord[] = [];
  private _consumptions: ConsumptionRecord[] = [];

  constructor(playerId: string) {
    this._playerId = playerId;
  }

  get playerId(): string {
    return this._playerId;
  }

  get balance(): number {
    return this._balance;
  }

  get totalPurchased(): number {
    return this._totalPurchased;
  }

  get totalConsumed(): number {
    return this._totalConsumed;
  }

  // -------------------------------------------------------------------------
  //  Purchase (Stripe → Tokens)
  // -------------------------------------------------------------------------

  /**
   * Record a purchase. Called AFTER Stripe payment confirmation.
   * Mints tokens into the wallet.
   *
   * @param packageId - Which package was purchased
   * @param stripePaymentId - Stripe payment intent ID (for audit)
   * @returns The purchase record
   */
  recordPurchase(packageId: string, stripePaymentId: string): PurchaseRecord | null {
    const pkg = TOKEN_PACKAGES.find((p) => p.packageId === packageId);
    if (!pkg) return null;

    const totalTokens = pkg.tokens + pkg.bonusTokens;

    const record: PurchaseRecord = {
      purchaseId: `pur_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      playerId: this._playerId,
      packageId,
      tokensMinted: totalTokens,
      priceUsd: pkg.priceUsd,
      stripePaymentId,
      timestamp: Date.now() / 1000,
      status: 'completed',
    };

    this._balance += totalTokens;
    this._totalPurchased += totalTokens;
    this._purchases.push(record);

    return record;
  }

  // -------------------------------------------------------------------------
  //  Consumption (Tokens → Compute)
  // -------------------------------------------------------------------------

  /**
   * Check if player can afford an activity.
   */
  canAfford(activityType: string): boolean {
    const cost = ACTIVITY_COSTS[activityType];
    if (!cost) return false;
    return this._balance >= cost.baseCost;
  }

  /**
   * Consume tokens for a game activity.
   * Returns the consumption record, or null if insufficient balance.
   *
   * @param activityType - What activity is being run
   * @param companionId - Which companion is involved (if any)
   * @param sessionId - Current game session ID
   * @param generatedTrainingData - Whether this activity generated SFT data
   * @param hfDatasetId - HuggingFace dataset ID if data was pushed
   */
  consume(
    activityType: string,
    companionId: string | null,
    sessionId: string,
    generatedTrainingData: boolean = false,
    hfDatasetId: string | null = null
  ): ConsumptionRecord | null {
    const cost = ACTIVITY_COSTS[activityType];
    if (!cost) return null;
    if (this._balance < cost.baseCost) return null;

    const record: ConsumptionRecord = {
      consumptionId: `con_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      playerId: this._playerId,
      activityType,
      tokensSpent: cost.baseCost,
      companionId,
      timestamp: Date.now() / 1000,
      sessionId,
      generatedTrainingData,
      hfDatasetId,
    };

    this._balance -= cost.baseCost;
    this._totalConsumed += cost.baseCost;
    this._consumptions.push(record);

    return record;
  }

  // -------------------------------------------------------------------------
  //  Refund (reverse a purchase)
  // -------------------------------------------------------------------------

  /**
   * Process a refund. Only works if tokens haven't been spent.
   * Returns remaining tokens to refund amount.
   */
  processRefund(purchaseId: string): { refunded: boolean; tokensReclaimed: number } {
    const purchase = this._purchases.find((p) => p.purchaseId === purchaseId);
    if (!purchase || purchase.status !== 'completed') {
      return { refunded: false, tokensReclaimed: 0 };
    }

    // Can only refund tokens that haven't been spent
    const reclaimable = Math.min(purchase.tokensMinted, this._balance);
    if (reclaimable <= 0) {
      return { refunded: false, tokensReclaimed: 0 };
    }

    this._balance -= reclaimable;
    // Mark as refunded (in production, also refund via Stripe API)
    (purchase as { status: string }).status = 'refunded';

    return { refunded: true, tokensReclaimed: reclaimable };
  }

  // -------------------------------------------------------------------------
  //  Queries
  // -------------------------------------------------------------------------

  /** Get purchase history */
  getPurchases(): readonly PurchaseRecord[] {
    return this._purchases;
  }

  /** Get consumption history */
  getConsumptions(): readonly ConsumptionRecord[] {
    return this._consumptions;
  }

  /** Get consumptions that generated training data */
  getTrainingConsumptions(): ConsumptionRecord[] {
    return this._consumptions.filter((c) => c.generatedTrainingData);
  }

  /** Compute hours of GPU time purchased */
  computeHoursPurchased(): number {
    return (this._totalPurchased * SECONDS_PER_TOKEN) / 3600;
  }

  /** Compute hours of GPU time consumed */
  computeHoursConsumed(): number {
    return (this._totalConsumed * SECONDS_PER_TOKEN) / 3600;
  }

  /** Summary for UI display */
  summary(): {
    balance: number;
    totalPurchased: number;
    totalConsumed: number;
    purchaseCount: number;
    activityCount: number;
    trainingDataGenerated: number;
    computeHoursRemaining: number;
  } {
    return {
      balance: this._balance,
      totalPurchased: this._totalPurchased,
      totalConsumed: this._totalConsumed,
      purchaseCount: this._purchases.length,
      activityCount: this._consumptions.length,
      trainingDataGenerated: this._consumptions.filter((c) => c.generatedTrainingData).length,
      computeHoursRemaining: (this._balance * SECONDS_PER_TOKEN) / 3600,
    };
  }
}
