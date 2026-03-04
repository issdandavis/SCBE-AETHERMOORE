/**
 * @file micro-ledger.unit.test.ts
 * @module tests/L2-unit/game
 * @layer Layer 12, Layer 13
 *
 * Tests for Spiral Forge RPG micro blockchain ledger.
 * Verifies: credit minting, Merkle integrity, chain verification,
 * ownership transfer, exchange protocol, denomination rates.
 */

import { describe, it, expect } from 'vitest';
import {
  DENOMINATION_WEIGHTS,
  SERVICE_BASE_COSTS,
  exchangeRate,
  energyCost,
  faceValue,
  creditHash,
  mintCredit,
  merkleRoot,
  blockHash,
  ContextLedger,
  ComputeExchange,
} from '../../../src/game/microLedger.js';

// ===========================================================================
//  Denomination System
// ===========================================================================

describe('Denomination System', () => {
  it('weights follow golden ratio scaling', () => {
    const phi = (1 + Math.sqrt(5)) / 2;
    expect(DENOMINATION_WEIGHTS.KO).toBeCloseTo(1.0, 5);
    expect(DENOMINATION_WEIGHTS.AV).toBeCloseTo(phi, 3);
    expect(DENOMINATION_WEIGHTS.DR).toBeCloseTo(phi ** 5, 2);
  });

  it('exchange rates obey φ-ratio symmetry', () => {
    // rate(A→B) × rate(B→A) = 1
    const ab = exchangeRate('KO', 'DR');
    const ba = exchangeRate('DR', 'KO');
    expect(ab * ba).toBeCloseTo(1.0, 8);
  });

  it('exchange rate KO→DR matches weight ratio', () => {
    const expected = DENOMINATION_WEIGHTS.KO / DENOMINATION_WEIGHTS.DR;
    expect(exchangeRate('KO', 'DR')).toBeCloseTo(expected, 8);
  });

  it('self-exchange rate is 1', () => {
    expect(exchangeRate('CA', 'CA')).toBeCloseTo(1.0, 10);
  });
});

// ===========================================================================
//  Service Costs
// ===========================================================================

describe('Service Base Costs', () => {
  it('all service types have a base cost', () => {
    const services = [
      'healing', 'formation_buff', 'scouting', 'transform_assist',
      'evolution_catalyst', 'drift_cleanse', 'codex_query', 'escort',
      'training', 'governance_vote',
    ] as const;
    for (const svc of services) {
      expect(SERVICE_BASE_COSTS[svc]).toBeGreaterThan(0);
    }
  });

  it('evolution_catalyst is the most expensive', () => {
    const max = Math.max(...Object.values(SERVICE_BASE_COSTS));
    expect(SERVICE_BASE_COSTS.evolution_catalyst).toBe(max);
  });

  it('codex_query is the cheapest', () => {
    const min = Math.min(...Object.values(SERVICE_BASE_COSTS));
    expect(SERVICE_BASE_COSTS.codex_query).toBe(min);
  });
});

// ===========================================================================
//  Credit Minting
// ===========================================================================

describe('Credit Minting', () => {
  it('mints a credit with valid fields', () => {
    const credit = mintCredit(
      'agent-1', 'crysling', 'CA', 'healing',
      [0.1, 0.1, 0.1, 0.6, 0.1, 0.1]
    );

    expect(credit.creditId).toMatch(/^cr_/);
    expect(credit.denomination).toBe('CA');
    expect(credit.serviceType).toBe('healing');
    expect(credit.dna.agentId).toBe('agent-1');
    expect(credit.legibility).toBe(1.0);
    expect(credit.nonce).toBeGreaterThanOrEqual(0);
  });

  it('face value = weight × energy × legibility', () => {
    const credit = mintCredit(
      'agent-1', 'crysling', 'KO', 'scouting',
      [0.5, 0.1, 0.1, 0.1, 0.1, 0.1],
      0, 0, 'ALLOW', [], 1.0
    );

    // KO weight=1, energy=1/(1+0+0)=1, legibility=1 → face value = 1
    expect(faceValue(credit)).toBeCloseTo(1.0, 5);
  });

  it('higher denomination = higher face value', () => {
    const ko = mintCredit('a', 's', 'KO', 'healing', [0.5, 0.1, 0.1, 0.1, 0.1, 0.1]);
    const dr = mintCredit('a', 's', 'DR', 'healing', [0.5, 0.1, 0.1, 0.1, 0.1, 0.1]);
    expect(faceValue(dr)).toBeGreaterThan(faceValue(ko));
  });

  it('higher Hamiltonian deviation = lower energy (higher cost)', () => {
    const credit = mintCredit(
      'a', 's', 'KO', 'healing', [0.5, 0.1, 0.1, 0.1, 0.1, 0.1],
      2.0, 1.0 // high d, high pd
    );
    // H(2,1) = 1/(1+2+2) = 0.2
    expect(energyCost(credit.dna)).toBeCloseTo(0.2, 5);
  });

  it('legibility affects face value', () => {
    const full = mintCredit('a', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0], 0, 0, 'ALLOW', [], 1.0);
    const half = mintCredit('a', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0], 0, 0, 'ALLOW', [], 0.5);
    expect(faceValue(full)).toBeGreaterThan(faceValue(half));
  });

  it('proof-of-context produces valid nonce (hash starts with 0)', () => {
    const credit = mintCredit(
      'a', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0],
      0, 0, 'ALLOW', [], 1.0, '', 1
    );
    const hash = creditHash(credit);
    expect(hash[0]).toBe('0');
  });
});

// ===========================================================================
//  Merkle Tree
// ===========================================================================

describe('Merkle Tree', () => {
  it('single hash returns itself', () => {
    expect(merkleRoot(['abc'])).toBe('abc');
  });

  it('empty list returns hash of "empty"', () => {
    const result = merkleRoot([]);
    expect(result).toBeTruthy();
    expect(result.length).toBe(64); // SHA-256 hex
  });

  it('is deterministic', () => {
    const hashes = ['aaa', 'bbb', 'ccc'];
    expect(merkleRoot(hashes)).toBe(merkleRoot(hashes));
  });

  it('odd-length list pads correctly', () => {
    const result = merkleRoot(['a', 'b', 'c']);
    expect(result.length).toBe(64);
  });
});

// ===========================================================================
//  Context Ledger (Blockchain)
// ===========================================================================

describe('Context Ledger', () => {
  it('starts with genesis block', () => {
    const ledger = new ContextLedger();
    expect(ledger.chainLength).toBe(1);
    expect(ledger.pendingCount).toBe(0);
  });

  it('adds credits to pending pool', () => {
    const ledger = new ContextLedger();
    const credit = mintCredit('a', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]);
    ledger.addCredit(credit);
    expect(ledger.pendingCount).toBe(1);
  });

  it('mines a block from pending credits', () => {
    const ledger = new ContextLedger();
    const credit = mintCredit('a', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]);
    ledger.addCredit(credit);
    const block = ledger.mineBlock('validator-1');
    expect(block).not.toBeNull();
    expect(block!.creditCount).toBe(1);
    expect(ledger.chainLength).toBe(2);
    expect(ledger.pendingCount).toBe(0);
  });

  it('returns null when mining with no pending credits', () => {
    const ledger = new ContextLedger();
    expect(ledger.mineBlock('v')).toBeNull();
  });

  it('tracks balance correctly', () => {
    const ledger = new ContextLedger();
    const c1 = mintCredit('alice', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]);
    const c2 = mintCredit('bob', 's', 'CA', 'scouting', [0, 0, 0, 0, 0, 0]);
    ledger.addCredit(c1);
    ledger.addCredit(c2);
    ledger.mineBlock('v');

    expect(ledger.balance('alice')).toBeGreaterThan(0);
    expect(ledger.balance('bob')).toBeGreaterThan(0);
    expect(ledger.balance('nobody')).toBe(0);
  });

  it('transfers credit ownership', () => {
    const ledger = new ContextLedger();
    const credit = mintCredit('alice', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]);
    ledger.addCredit(credit);
    ledger.mineBlock('v');

    const aliceBefore = ledger.balance('alice');
    expect(ledger.transfer(credit.creditId, 'alice', 'bob')).toBe(true);
    expect(ledger.balance('alice')).toBeLessThan(aliceBefore);
    expect(ledger.balance('bob')).toBeGreaterThan(0);
  });

  it('rejects transfer from wrong owner', () => {
    const ledger = new ContextLedger();
    const credit = mintCredit('alice', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]);
    ledger.addCredit(credit);
    ledger.mineBlock('v');

    expect(ledger.transfer(credit.creditId, 'bob', 'charlie')).toBe(false);
  });

  it('verifies chain integrity', () => {
    const ledger = new ContextLedger();
    for (let i = 0; i < 5; i++) {
      ledger.addCredit(mintCredit(`agent-${i}`, 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]));
      ledger.mineBlock(`validator-${i}`);
    }
    const result = ledger.verifyChain();
    expect(result.valid).toBe(true);
  });

  it('tracks total supply', () => {
    const ledger = new ContextLedger();
    const c1 = mintCredit('a', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]);
    const c2 = mintCredit('b', 's', 'KO', 'scouting', [0, 0, 0, 0, 0, 0]);
    ledger.addCredit(c1);
    ledger.addCredit(c2);
    ledger.mineBlock('v');
    expect(ledger.totalSupply()).toBeGreaterThan(0);
  });

  it('lists credits by agent', () => {
    const ledger = new ContextLedger();
    ledger.addCredit(mintCredit('alice', 's', 'KO', 'healing', [0, 0, 0, 0, 0, 0]));
    ledger.addCredit(mintCredit('alice', 's', 'CA', 'scouting', [0, 0, 0, 0, 0, 0]));
    ledger.addCredit(mintCredit('bob', 's', 'DR', 'training', [0, 0, 0, 0, 0, 0]));
    ledger.mineBlock('v');

    expect(ledger.creditsByAgent('alice')).toHaveLength(2);
    expect(ledger.creditsByAgent('bob')).toHaveLength(1);
    expect(ledger.creditsByAgent('nobody')).toHaveLength(0);
  });
});

// ===========================================================================
//  Compute Exchange
// ===========================================================================

describe('Compute Exchange', () => {
  function setupExchange() {
    const ledger = new ContextLedger();
    // Give alice some credits
    for (let i = 0; i < 10; i++) {
      ledger.addCredit(mintCredit('alice', 's', 'KO', 'training', [0, 0, 0, 0, 0, 0]));
    }
    ledger.mineBlock('v');
    return { ledger, exchange: new ComputeExchange(ledger) };
  }

  it('posts an offer', () => {
    const { exchange } = setupExchange();
    const offer = exchange.postOffer(
      'bob', 'healing', 'KO', 'Heal your companion', 5.0
    );
    expect(offer.state).toBe('POSTED');
    expect(offer.offererId).toBe('bob');
  });

  it('lists active offers', () => {
    const { exchange } = setupExchange();
    exchange.postOffer('bob', 'healing', 'KO', 'Heal 1', 5.0);
    exchange.postOffer('carol', 'scouting', 'CA', 'Scout dungeon', 3.0);

    expect(exchange.listOffers()).toHaveLength(2);
    expect(exchange.listOffers('healing')).toHaveLength(1);
    expect(exchange.listOffers(undefined, 'CA')).toHaveLength(1);
  });

  it('accepts an offer and creates transaction', () => {
    const { exchange } = setupExchange();
    const offer = exchange.postOffer('bob', 'healing', 'KO', 'Heal', 3.0, 2.0);
    const tx = exchange.acceptOffer(offer.offerId, 'alice', 3.0);

    expect(tx).not.toBeNull();
    expect(tx!.sellerId).toBe('bob');
    expect(tx!.buyerId).toBe('alice');
    expect(tx!.state).toBe('MATCHED');
  });

  it('rejects offers below min price', () => {
    const { exchange } = setupExchange();
    const offer = exchange.postOffer('bob', 'healing', 'KO', 'Heal', 5.0, 4.0);
    const tx = exchange.acceptOffer(offer.offerId, 'alice', 2.0);
    expect(tx).toBeNull();
  });

  it('settles a transaction', () => {
    const { exchange } = setupExchange();
    const offer = exchange.postOffer('bob', 'healing', 'KO', 'Heal', 3.0, 2.0);
    const tx = exchange.acceptOffer(offer.offerId, 'alice', 3.0);
    expect(tx).not.toBeNull();

    const settled = exchange.settleTransaction(tx!.transactionId, 'delivery-hash-123');
    expect(settled).toBe(true);
  });

  it('produces exchange summary', () => {
    const { exchange } = setupExchange();
    exchange.postOffer('bob', 'healing', 'KO', 'Heal', 3.0);
    const summary = exchange.summary();
    expect(summary.totalOffers).toBe(1);
    expect(summary.activeOffers).toBe(1);
  });

  it('tracks transactions by agent', () => {
    const { exchange } = setupExchange();
    const offer = exchange.postOffer('bob', 'healing', 'KO', 'Heal', 3.0, 2.0);
    exchange.acceptOffer(offer.offerId, 'alice', 3.0);

    expect(exchange.transactionsByAgent('alice')).toHaveLength(1);
    expect(exchange.transactionsByAgent('bob')).toHaveLength(1);
    expect(exchange.transactionsByAgent('nobody')).toHaveLength(0);
  });
});
