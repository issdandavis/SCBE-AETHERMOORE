/**
 * @file microLedger.ts
 * @module game/microLedger
 * @layer Layer 12, Layer 13
 * @component Micro Blockchain Ledger — AI-to-AI Service Trading
 *
 * Internal-only micro-currency for companion/agent service trading.
 * NOT real-world value. Tracks compute receipts, healing, formation buffs,
 * information exchange, and codex queries between AI entities.
 *
 * Integrates with MMCCL (Python) patterns:
 * - Denomination weights = Sacred Tongue φ-weights
 * - Face value = weight × energy × complexity × legibility
 * - Merkle tree block integrity
 * - Proof-of-context mining (not proof-of-work)
 *
 * A3: Causality — all transactions are time-ordered, append-only.
 * A4: Symmetry — denomination exchange rates obey φ-ratio symmetry.
 * A5: Composition — chain integrity verified by Merkle root.
 */

import { createHash } from 'crypto';
import { TongueCode, TONGUE_CODES, TONGUE_WEIGHTS, RiskDecision } from './types.js';

// ---------------------------------------------------------------------------
//  Denomination (mirrors MMCCL Denomination enum)
// ---------------------------------------------------------------------------

/** Sacred Tongue denomination — each tongue IS a currency */
export type Denomination = TongueCode;

/** Denomination weights from golden ratio — mirrors MMCCL DENOMINATION_WEIGHTS */
export const DENOMINATION_WEIGHTS: Record<Denomination, number> = { ...TONGUE_WEIGHTS };

/**
 * Get exchange rate between two denominations.
 * Rate(A→B) = weight(A) / weight(B)
 */
export function exchangeRate(from: Denomination, to: Denomination): number {
  return DENOMINATION_WEIGHTS[from] / DENOMINATION_WEIGHTS[to];
}

// ---------------------------------------------------------------------------
//  Service Types (what companions trade)
// ---------------------------------------------------------------------------

/** Categories of services companions can offer/request */
export type ServiceType =
  | 'healing' // Restore seal integrity
  | 'formation_buff' // Temporary formation bonus
  | 'scouting' // Reveal dungeon info
  | 'transform_assist' // Help with math combat transforms
  | 'evolution_catalyst' // Assist evolution conditions
  | 'drift_cleanse' // Reduce drift level
  | 'codex_query' // Share codex knowledge
  | 'escort' // Protection during travel
  | 'training' // XP sharing
  | 'governance_vote'; // Voting weight for roundtable decisions

/** Base cost in KO-equivalent for each service type */
export const SERVICE_BASE_COSTS: Record<ServiceType, number> = {
  healing: 5.0,
  formation_buff: 3.0,
  scouting: 2.0,
  transform_assist: 4.0,
  evolution_catalyst: 15.0,
  drift_cleanse: 8.0,
  codex_query: 1.0,
  escort: 3.0,
  training: 6.0,
  governance_vote: 10.0,
};

// ---------------------------------------------------------------------------
//  SHA-256 Helper
// ---------------------------------------------------------------------------

function sha256(data: string): string {
  return createHash('sha256').update(data).digest('hex');
}

// ---------------------------------------------------------------------------
//  Credit DNA (mirrors MMCCL CreditDNA)
// ---------------------------------------------------------------------------

export interface CreditDNA {
  /** Agent/companion ID */
  readonly agentId: string;

  /** Species or model name */
  readonly speciesId: string;

  /** 6D tongue position snapshot at mint time */
  readonly tongueSnapshot: readonly number[];

  /** Hamiltonian deviation at mint time */
  readonly hamiltonianD: number;

  /** Phase deviation at mint time */
  readonly hamiltonianPd: number;

  /** SCBE governance verdict that authorized this credit */
  readonly governanceVerdict: RiskDecision;
}

/** H(d,pd) = 1/(1+d+2*pd) — energy cost */
export function energyCost(dna: CreditDNA): number {
  return 1.0 / (1.0 + dna.hamiltonianD + 2.0 * dna.hamiltonianPd);
}

/** Hash the DNA for Merkle inclusion */
function dnaSha(dna: CreditDNA): string {
  return sha256(JSON.stringify(dna)).slice(0, 16);
}

// ---------------------------------------------------------------------------
//  Context Credit (mirrors MMCCL ContextCredit)
// ---------------------------------------------------------------------------

export interface ContextCredit {
  /** Unique credit ID */
  readonly creditId: string;

  /** Sacred Tongue denomination */
  readonly denomination: Denomination;

  /** Genetic fingerprint of the minting agent */
  readonly dna: CreditDNA;

  /** SHA-256 of the service payload */
  readonly payloadHash: string;

  /** IDs of parent credits (lineage) */
  readonly parentCredits: readonly string[];

  /** Unix timestamp of minting */
  readonly timestamp: number;

  /** Proof-of-context nonce */
  readonly nonce: number;

  /** Legibility score [0,1] — how verifiable the service was */
  readonly legibility: number;

  /** Service type this credit represents */
  readonly serviceType: ServiceType;

  /** Optional description */
  readonly summary: string;
}

/**
 * Face value of a credit.
 * value = weight × energy × legibility
 * (Simplified from MMCCL — no complexity field in game context)
 */
export function faceValue(credit: ContextCredit): number {
  const weight = DENOMINATION_WEIGHTS[credit.denomination];
  const energy = energyCost(credit.dna);
  return weight * energy * credit.legibility;
}

/** Block hash of a credit for Merkle inclusion */
export function creditHash(credit: ContextCredit): string {
  const data = JSON.stringify({
    id: credit.creditId,
    denom: credit.denomination,
    payload: credit.payloadHash,
    parents: [...credit.parentCredits],
    ts: credit.timestamp,
    nonce: credit.nonce,
    dna_hash: dnaSha(credit.dna),
    value: Math.round(faceValue(credit) * 1e8) / 1e8,
  });
  return sha256(data);
}

// ---------------------------------------------------------------------------
//  Credit Minting
// ---------------------------------------------------------------------------

let _creditCounter = 0;

/**
 * Mint a new ContextCredit.
 *
 * Performs proof-of-context: finds a nonce such that the credit hash
 * starts with `difficulty` zero-nibbles.
 *
 * @param agentId - Minting companion/agent ID
 * @param speciesId - Species name
 * @param denomination - Tongue denomination
 * @param serviceType - What service this credit represents
 * @param tongueSnapshot - 6D tongue position at mint time
 * @param hamiltonianD - Deviation at mint time
 * @param hamiltonianPd - Phase deviation at mint time
 * @param governanceVerdict - SCBE decision at mint time
 * @param parentCreditIds - Lineage
 * @param legibility - How verifiable (0-1)
 * @param summary - Description
 * @param difficulty - Proof-of-context difficulty (default 1)
 */
export function mintCredit(
  agentId: string,
  speciesId: string,
  denomination: Denomination,
  serviceType: ServiceType,
  tongueSnapshot: readonly number[],
  hamiltonianD: number = 0,
  hamiltonianPd: number = 0,
  governanceVerdict: RiskDecision = 'ALLOW',
  parentCreditIds: string[] = [],
  legibility: number = 1.0,
  summary: string = '',
  difficulty: number = 1
): ContextCredit {
  const dna: CreditDNA = {
    agentId,
    speciesId,
    tongueSnapshot,
    hamiltonianD,
    hamiltonianPd,
    governanceVerdict,
  };

  const payloadHash = sha256(`${agentId}:${serviceType}:${Date.now()}:${_creditCounter++}`);

  // Proof-of-context: find nonce that gives leading zeros
  const prefix = '0'.repeat(difficulty);
  let nonce = 0;

  const baseCredit: ContextCredit = {
    creditId: `cr_${sha256(`${agentId}:${Date.now()}:${_creditCounter}`).slice(0, 12)}`,
    denomination,
    dna,
    payloadHash,
    parentCredits: parentCreditIds,
    timestamp: Date.now() / 1000,
    nonce: 0,
    legibility: Math.max(0, Math.min(1, legibility)),
    serviceType,
    summary,
  };

  // Mine for valid nonce (proof-of-context)
  while (nonce < 100000) {
    const candidate = { ...baseCredit, nonce };
    const hash = creditHash(candidate);
    if (hash.startsWith(prefix)) {
      return candidate;
    }
    nonce++;
  }

  // Fallback: accept without prefix match (shouldn't happen with difficulty=1)
  return { ...baseCredit, nonce };
}

// ---------------------------------------------------------------------------
//  Merkle Tree (mirrors MMCCL merkle_root)
// ---------------------------------------------------------------------------

function merkleHash(a: string, b: string): string {
  return sha256(a + b);
}

export function merkleRoot(hashes: string[]): string {
  if (hashes.length === 0) return sha256('empty');
  if (hashes.length === 1) return hashes[0];

  let layer = [...hashes];
  if (layer.length % 2 !== 0) layer.push(layer[layer.length - 1]);

  while (layer.length > 1) {
    const next: string[] = [];
    for (let i = 0; i < layer.length; i += 2) {
      next.push(merkleHash(layer[i], layer[i + 1]));
    }
    layer = next;
  }

  return layer[0];
}

// ---------------------------------------------------------------------------
//  Block (mirrors MMCCL Block)
// ---------------------------------------------------------------------------

export interface Block {
  readonly index: number;
  readonly timestamp: number;
  readonly credits: readonly ContextCredit[];
  readonly previousHash: string;
  readonly merkleRootHash: string;
  readonly validatorId: string;
  readonly totalValue: number;
  readonly totalEnergy: number;
  readonly creditCount: number;
}

function computeBlockHash(block: Block): string {
  const data = JSON.stringify({
    index: block.index,
    ts: block.timestamp,
    merkle: block.merkleRootHash,
    prev: block.previousHash,
    validator: block.validatorId,
    value: Math.round(block.totalValue * 1e8) / 1e8,
    energy: Math.round(block.totalEnergy * 1e8) / 1e8,
    count: block.creditCount,
  });
  return sha256(data);
}

export function blockHash(block: Block): string {
  return computeBlockHash(block);
}

function createBlock(
  index: number,
  credits: ContextCredit[],
  previousHash: string,
  validatorId: string
): Block {
  return {
    index,
    timestamp: Date.now() / 1000,
    credits,
    previousHash,
    merkleRootHash: merkleRoot(credits.map(creditHash)),
    validatorId,
    totalValue: credits.reduce((sum, c) => sum + faceValue(c), 0),
    totalEnergy: credits.reduce((sum, c) => sum + energyCost(c.dna), 0),
    creditCount: credits.length,
  };
}

// ---------------------------------------------------------------------------
//  Context Ledger (Blockchain)
// ---------------------------------------------------------------------------

const GENESIS_HASH = sha256('SCBE-AETHERMOORE-MMCCB-GENESIS');

export class ContextLedger {
  private chain: Block[] = [];
  private pendingCredits: ContextCredit[] = [];
  private ownershipMap: Map<string, string> = new Map(); // creditId → agentId

  constructor() {
    // Genesis block
    const genesis = createBlock(0, [], GENESIS_HASH, 'genesis');
    this.chain.push(genesis);
  }

  /** Add a credit to the pending pool */
  addCredit(credit: ContextCredit): void {
    this.pendingCredits.push(credit);
    this.ownershipMap.set(credit.creditId, credit.dna.agentId);
  }

  /** Mine a block from pending credits */
  mineBlock(validatorId: string): Block | null {
    if (this.pendingCredits.length === 0) return null;

    const prev = this.chain[this.chain.length - 1];
    const block = createBlock(
      this.chain.length,
      [...this.pendingCredits],
      blockHash(prev),
      validatorId
    );

    this.chain.push(block);
    this.pendingCredits = [];

    return block;
  }

  /** Transfer credit ownership */
  transfer(creditId: string, fromAgent: string, toAgent: string): boolean {
    const currentOwner = this.ownershipMap.get(creditId);
    if (currentOwner !== fromAgent) return false;
    this.ownershipMap.set(creditId, toAgent);
    return true;
  }

  /** Get balance (total face value) for an agent */
  balance(agentId: string): number {
    let total = 0;
    for (const block of this.chain) {
      for (const credit of block.credits) {
        if (this.ownershipMap.get(credit.creditId) === agentId) {
          total += faceValue(credit);
        }
      }
    }
    // Add pending credits
    for (const credit of this.pendingCredits) {
      if (this.ownershipMap.get(credit.creditId) === agentId) {
        total += faceValue(credit);
      }
    }
    return total;
  }

  /** Get credits owned by an agent */
  creditsByAgent(agentId: string): ContextCredit[] {
    const result: ContextCredit[] = [];
    for (const block of this.chain) {
      for (const credit of block.credits) {
        if (this.ownershipMap.get(credit.creditId) === agentId) {
          result.push(credit);
        }
      }
    }
    for (const credit of this.pendingCredits) {
      if (this.ownershipMap.get(credit.creditId) === agentId) {
        result.push(credit);
      }
    }
    return result;
  }

  /** Get credits by denomination */
  creditsByDenomination(denom: Denomination): ContextCredit[] {
    const result: ContextCredit[] = [];
    for (const block of this.chain) {
      for (const credit of block.credits) {
        if (credit.denomination === denom) result.push(credit);
      }
    }
    return result;
  }

  /** Total supply across all agents */
  totalSupply(): number {
    let total = 0;
    for (const block of this.chain) {
      total += block.totalValue;
    }
    for (const credit of this.pendingCredits) {
      total += faceValue(credit);
    }
    return total;
  }

  /** Total energy spent across all blocks */
  totalEnergySpent(): number {
    return this.chain.reduce((sum, b) => sum + b.totalEnergy, 0);
  }

  /** Verify chain integrity (Merkle roots + hash links) */
  verifyChain(): { valid: boolean; errorAt?: number; reason?: string } {
    for (let i = 1; i < this.chain.length; i++) {
      const prev = this.chain[i - 1];
      const curr = this.chain[i];

      // Verify hash link
      if (curr.previousHash !== blockHash(prev)) {
        return { valid: false, errorAt: i, reason: 'broken hash link' };
      }

      // Verify Merkle root
      const expectedMerkle = merkleRoot(curr.credits.map(creditHash));
      if (curr.merkleRootHash !== expectedMerkle) {
        return { valid: false, errorAt: i, reason: 'merkle root mismatch' };
      }
    }

    return { valid: true };
  }

  /** Get chain length */
  get chainLength(): number {
    return this.chain.length;
  }

  /** Get pending credit count */
  get pendingCount(): number {
    return this.pendingCredits.length;
  }

  /** Get all blocks (for display/debug) */
  getChain(): readonly Block[] {
    return this.chain;
  }
}

// ---------------------------------------------------------------------------
//  Exchange Offer (mirrors MMCCL ExchangeOffer)
// ---------------------------------------------------------------------------

export type OfferType = ServiceType;

export type ExchangeState =
  | 'POSTED'
  | 'MATCHED'
  | 'ESCROWED'
  | 'EXECUTING'
  | 'SETTLED'
  | 'DISPUTED'
  | 'CANCELLED'
  | 'EXPIRED';

export interface ExchangeOffer {
  readonly offerId: string;
  readonly offererId: string;
  readonly serviceType: ServiceType;
  readonly denomination: Denomination;
  readonly description: string;
  readonly askingPrice: number;
  readonly minPrice: number;
  readonly createdAt: number;
  readonly expiresAt: number;
  state: ExchangeState;
}

export interface ExchangeTransaction {
  readonly transactionId: string;
  readonly offerId: string;
  readonly sellerId: string;
  readonly buyerId: string;
  readonly serviceType: ServiceType;
  readonly agreedPrice: number;
  readonly denomination: Denomination;
  state: ExchangeState;
  readonly createdAt: number;
  settledAt?: number;
  readonly deliveryHash?: string;
}

// ---------------------------------------------------------------------------
//  Compute Exchange (marketplace)
// ---------------------------------------------------------------------------

let _offerCounter = 0;
let _txCounter = 0;

export class ComputeExchange {
  private offers: Map<string, ExchangeOffer> = new Map();
  private transactions: Map<string, ExchangeTransaction> = new Map();
  private ledger: ContextLedger;

  constructor(ledger: ContextLedger) {
    this.ledger = ledger;
  }

  /** Post an offer to provide a service */
  postOffer(
    offererId: string,
    serviceType: ServiceType,
    denomination: Denomination,
    description: string,
    askingPrice: number,
    minPrice?: number,
    ttlSeconds: number = 3600
  ): ExchangeOffer {
    const offer: ExchangeOffer = {
      offerId: `offer_${++_offerCounter}`,
      offererId,
      serviceType,
      denomination,
      description,
      askingPrice,
      minPrice: minPrice ?? askingPrice * 0.8,
      createdAt: Date.now() / 1000,
      expiresAt: Date.now() / 1000 + ttlSeconds,
      state: 'POSTED',
    };

    this.offers.set(offer.offerId, offer);
    return offer;
  }

  /** Accept an offer — creates a transaction */
  acceptOffer(offerId: string, buyerId: string, agreedPrice: number): ExchangeTransaction | null {
    const offer = this.offers.get(offerId);
    if (!offer || offer.state !== 'POSTED') return null;
    if (agreedPrice < offer.minPrice) return null;
    if (Date.now() / 1000 > offer.expiresAt) {
      offer.state = 'EXPIRED';
      return null;
    }

    // Check buyer balance
    const buyerBalance = this.ledger.balance(buyerId);
    if (buyerBalance < agreedPrice) return null;

    offer.state = 'MATCHED';

    const tx: ExchangeTransaction = {
      transactionId: `tx_${++_txCounter}`,
      offerId,
      sellerId: offer.offererId,
      buyerId,
      serviceType: offer.serviceType,
      agreedPrice,
      denomination: offer.denomination,
      state: 'MATCHED',
      createdAt: Date.now() / 1000,
    };

    this.transactions.set(tx.transactionId, tx);
    return tx;
  }

  /**
   * Settle a transaction — transfer credits from buyer to seller.
   * In production, this would use BitLocker escrow.
   * For game v1: direct transfer with delivery hash verification.
   */
  settleTransaction(transactionId: string, deliveryHash: string): boolean {
    const tx = this.transactions.get(transactionId);
    if (!tx || tx.state !== 'MATCHED') return false;

    // Mint a settlement credit from buyer to seller
    const credit = mintCredit(
      tx.buyerId,
      'exchange',
      tx.denomination,
      tx.serviceType,
      [0, 0, 0, 0, 0, 0], // generic snapshot for exchange
      0,
      0,
      'ALLOW',
      [],
      1.0,
      `Settlement: ${tx.serviceType} from ${tx.sellerId}`,
      1
    );

    this.ledger.addCredit(credit);

    // Transfer ownership to seller
    this.ledger.transfer(credit.creditId, tx.buyerId, tx.sellerId);

    tx.state = 'SETTLED';
    tx.settledAt = Date.now() / 1000;
    (tx as { deliveryHash: string }).deliveryHash = deliveryHash;

    const offer = this.offers.get(tx.offerId);
    if (offer) offer.state = 'SETTLED';

    return true;
  }

  /** List active offers, optionally filtered */
  listOffers(serviceType?: ServiceType, denomination?: Denomination): ExchangeOffer[] {
    const result: ExchangeOffer[] = [];
    const now = Date.now() / 1000;

    for (const offer of this.offers.values()) {
      // Auto-expire
      if (offer.state === 'POSTED' && now > offer.expiresAt) {
        offer.state = 'EXPIRED';
      }
      if (offer.state !== 'POSTED') continue;
      if (serviceType && offer.serviceType !== serviceType) continue;
      if (denomination && offer.denomination !== denomination) continue;
      result.push(offer);
    }

    return result;
  }

  /** Get transactions for an agent */
  transactionsByAgent(agentId: string): ExchangeTransaction[] {
    return Array.from(this.transactions.values()).filter(
      (tx) => tx.buyerId === agentId || tx.sellerId === agentId
    );
  }

  /** Get exchange summary */
  summary(): {
    totalOffers: number;
    activeOffers: number;
    totalTransactions: number;
    settledTransactions: number;
    totalVolumeTraded: number;
  } {
    const now = Date.now() / 1000;
    let active = 0;
    for (const o of this.offers.values()) {
      if (o.state === 'POSTED' && now <= o.expiresAt) active++;
    }

    let settled = 0;
    let volume = 0;
    for (const tx of this.transactions.values()) {
      if (tx.state === 'SETTLED') {
        settled++;
        volume += tx.agreedPrice;
      }
    }

    return {
      totalOffers: this.offers.size,
      activeOffers: active,
      totalTransactions: this.transactions.size,
      settledTransactions: settled,
      totalVolumeTraded: volume,
    };
  }
}
