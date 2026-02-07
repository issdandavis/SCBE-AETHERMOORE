"use strict";
/**
 * SCBE-AETHERMOORE API
 *
 * Complete TypeScript API for the Spiralverse Protocol, exposing:
 * - Risk evaluation with hyperbolic geometry
 * - RWP v2.1 multi-signature envelopes
 * - Agent management with 6D positioning and trust
 * - SecurityGate with adaptive dwell time
 * - Roundtable consensus (multi-signature requirements)
 * - Harmonic complexity pricing
 *
 * Usage:
 *   import { SCBE, Agent, SecurityGate, Roundtable } from './api';
 *
 *   // Create agents in 6D space
 *   const alice = new Agent('Alice', [1, 2, 3, 0.5, 1.5, 2.5]);
 *
 *   // Evaluate risk
 *   const risk = scbe.evaluateRisk({ action: 'transfer', amount: 10000 });
 *
 *   // Security gate check with adaptive dwell time
 *   const gate = new SecurityGate();
 *   const result = await gate.check(alice, 'delete', { source: 'external' });
 *
 *   // Sign with Roundtable consensus
 *   const tongues = Roundtable.requiredTongues('deploy');
 *   const envelope = scbe.sign(payload, tongues);
 *
 * @module api
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultGate = exports.scbe = exports.SCBE = exports.Roundtable = exports.SecurityGate = exports.Agent = void 0;
exports.harmonicComplexity = harmonicComplexity;
exports.getPricingTier = getPricingTier;
exports.evaluateRisk = evaluateRisk;
exports.sign = sign;
exports.signForAction = signForAction;
exports.verify = verify;
exports.verifyForAction = verifyForAction;
exports.breathe = breathe;
exports.checkAccess = checkAccess;
exports.requiredTongues = requiredTongues;
const crypto_1 = require("crypto");
const index_js_1 = require("../harmonic/index.js");
const index_js_2 = require("../spiralverse/index.js");
// ============================================================
// Configuration
// ============================================================
const DEFAULT_KEYRING = {
    ko: (0, crypto_1.randomBytes)(32),
    av: (0, crypto_1.randomBytes)(32),
    ru: (0, crypto_1.randomBytes)(32),
    ca: (0, crypto_1.randomBytes)(32),
    um: (0, crypto_1.randomBytes)(32),
    dr: (0, crypto_1.randomBytes)(32),
};
const SAFE_CENTER = [0, 0, 0, 0, 0, 0];
const RISK_THRESHOLDS = {
    ALLOW: 0.3,
    REVIEW: 0.7,
};
const MAX_COMPLEXITY = 1e10; // Cap to prevent overflow
// ============================================================
// Agent - 6D Vector Navigation
// ============================================================
/**
 * An AI agent with a position in 6D space and trust tracking.
 *
 * Agents exist in a 6-dimensional space where:
 * - Close agents = simple security (they trust each other)
 * - Far agents = complex security (strangers need more checks)
 */
class Agent {
    name;
    position;
    trustScore;
    lastSeen;
    /**
     * Create a new agent in 6D space.
     * @param name - Agent identifier
     * @param position - 6D position vector
     * @param initialTrust - Starting trust score (0-1, default 1.0)
     */
    constructor(name, position, initialTrust = 1.0) {
        if (!Array.isArray(position) || position.length !== 6) {
            throw new Error('Position must be a 6-element array');
        }
        if (!position.every((n) => typeof n === 'number' && isFinite(n))) {
            throw new Error('Position elements must be finite numbers');
        }
        this.name = name;
        this.position = [...position];
        this.trustScore = Math.max(0, Math.min(1, initialTrust));
        this.lastSeen = Date.now();
    }
    /**
     * Calculate Euclidean distance to another agent.
     * Close agents = simple communication, far agents = complex security.
     */
    distanceTo(other) {
        let sum = 0;
        for (let i = 0; i < 6; i++) {
            const diff = this.position[i] - other.position[i];
            sum += diff * diff;
        }
        return Math.sqrt(sum);
    }
    /**
     * Agent checks in - refreshes trust and timestamp.
     */
    checkIn() {
        this.lastSeen = Date.now();
        this.trustScore = Math.min(1.0, this.trustScore + 0.1);
    }
    /**
     * Apply trust decay based on time since last check-in.
     * @param decayRate - Rate of decay (default 0.01)
     * @returns Current trust score after decay
     */
    decayTrust(decayRate = 0.01) {
        const elapsed = (Date.now() - this.lastSeen) / 1000; // seconds
        this.trustScore *= Math.exp(-decayRate * elapsed);
        return this.trustScore;
    }
}
exports.Agent = Agent;
// ============================================================
// SecurityGate - Adaptive Dwell Time
// ============================================================
/**
 * Security gate with adaptive dwell time based on risk.
 *
 * Like a nightclub bouncer that:
 * - Checks your ID (authentication)
 * - Looks at your reputation (trust score)
 * - Makes you wait longer if you're risky (adaptive dwell time)
 */
class SecurityGate {
    minWaitMs;
    maxWaitMs;
    alpha;
    constructor(config = {}) {
        this.minWaitMs = config.minWaitMs ?? 100;
        this.maxWaitMs = config.maxWaitMs ?? 5000;
        this.alpha = config.alpha ?? 1.5;
    }
    /**
     * Calculate risk score for an agent performing an action.
     * @returns Risk score (0 = safe, higher = riskier)
     */
    assessRisk(agent, action, context) {
        let risk = 0;
        // Low trust = high risk
        risk += (1.0 - agent.trustScore) * 2.0;
        // Dangerous actions = high risk
        const dangerousActions = ['delete', 'deploy', 'rotate_keys', 'grant_access'];
        if (dangerousActions.includes(action)) {
            risk += 3.0;
        }
        // External context = higher risk
        if (context.source === 'external') {
            risk += 1.5;
        }
        return risk;
    }
    /**
     * Perform security gate check with adaptive dwell time.
     *
     * Higher risk = longer wait time (slows attackers).
     * Returns allow/review/deny decision.
     */
    async check(agent, action, context) {
        const risk = this.assessRisk(agent, action, context);
        // Adaptive dwell time (higher risk = longer wait)
        const dwellMs = Math.min(this.maxWaitMs, this.minWaitMs * Math.pow(this.alpha, risk));
        // Wait (non-blocking)
        await new Promise((resolve) => setTimeout(resolve, dwellMs));
        // Calculate composite score (0-1, higher = safer)
        const trustComponent = agent.trustScore * 0.4;
        const actionComponent = (dangerousActions.includes(action) ? 0.3 : 1.0) * 0.3;
        const contextComponent = (context.source === 'internal' ? 0.8 : 0.4) * 0.3;
        const score = trustComponent + actionComponent + contextComponent;
        if (score > 0.8) {
            return { status: 'allow', score, dwellMs };
        }
        else if (score > 0.5) {
            return { status: 'review', score, dwellMs, reason: 'Manual approval required' };
        }
        else {
            return { status: 'deny', score, dwellMs, reason: 'Security threshold not met' };
        }
    }
}
exports.SecurityGate = SecurityGate;
const dangerousActions = ['delete', 'deploy', 'rotate_keys', 'grant_access'];
// ============================================================
// Roundtable - Multi-Signature Consensus
// ============================================================
/**
 * Roundtable multi-signature consensus system.
 *
 * Different actions require different numbers of "departments" to agree:
 * - Low security: 1 signature (just control)
 * - Medium security: 2 signatures (control + policy)
 * - High security: 3 signatures (control + policy + security)
 * - Critical: 4+ signatures (all departments)
 */
exports.Roundtable = {
    /** Tier definitions for multi-signature requirements */
    TIERS: {
        low: ['ko'],
        medium: ['ko', 'ru'],
        high: ['ko', 'ru', 'um'],
        critical: ['ko', 'ru', 'um', 'dr'],
    },
    /**
     * Get required tongues for an action.
     */
    requiredTongues(action) {
        switch (action) {
            case 'read':
            case 'query':
                return this.TIERS.low;
            case 'write':
            case 'update':
                return this.TIERS.medium;
            case 'delete':
            case 'grant':
                return this.TIERS.high;
            case 'deploy':
            case 'rotate_keys':
            default:
                return this.TIERS.critical;
        }
    },
    /**
     * Check if we have all required signatures.
     */
    hasQuorum(signatures, required) {
        return required.every((t) => signatures.includes(t));
    },
    /**
     * Get suggested policy level for an action (from spiralverse).
     */
    suggestPolicy: index_js_2.suggestPolicy,
    /**
     * Get required tongues for a policy level (from spiralverse).
     */
    getRequiredTongues: index_js_2.getRequiredTongues,
    /**
     * Check if tongues satisfy a policy (from spiralverse).
     */
    checkPolicy: index_js_2.checkPolicy,
};
// ============================================================
// Harmonic Complexity Pricing
// ============================================================
/**
 * Calculate harmonic complexity for a task depth.
 *
 * Uses the "perfect fifth" ratio (1.5) from music theory:
 * - depth=1: H = 1.5^1 = 1.5 (simple, like a single note)
 * - depth=2: H = 1.5^4 = 5.06 (medium, like a chord)
 * - depth=3: H = 1.5^9 = 38.4 (complex, like a symphony)
 *
 * @param depth - Task nesting depth (1-based)
 * @param ratio - Harmonic ratio (default 1.5 = perfect fifth)
 */
function harmonicComplexity(depth, ratio = 1.5) {
    const result = Math.pow(ratio, depth * depth);
    return Math.min(result, MAX_COMPLEXITY);
}
/**
 * Get pricing tier based on task complexity.
 */
function getPricingTier(depth) {
    const complexity = harmonicComplexity(depth);
    if (complexity < 2) {
        return { tier: 'FREE', complexity, description: 'Simple single-step tasks' };
    }
    else if (complexity < 10) {
        return { tier: 'STARTER', complexity, description: 'Basic workflows' };
    }
    else if (complexity < 100) {
        return { tier: 'PRO', complexity, description: 'Advanced multi-step' };
    }
    else {
        return { tier: 'ENTERPRISE', complexity, description: 'Complex orchestration' };
    }
}
// ============================================================
// Core API
// ============================================================
class SCBE {
    keyring;
    metric;
    constructor(keyring) {
        this.keyring = keyring || DEFAULT_KEYRING;
        this.metric = new index_js_1.LanguesMetric();
    }
    /**
     * Evaluate the risk of a context/action.
     * Returns a risk score and decision.
     */
    evaluateRisk(context) {
        // Convert context to 6D point
        const point = this.contextToPoint(context);
        // Project to Poincaré ball (ensures point is valid)
        const projected = (0, index_js_1.projectToBall)(point);
        // Compute hyperbolic distance from safe center
        const distance = (0, index_js_1.hyperbolicDistance)(projected, SAFE_CENTER);
        // Apply harmonic scaling (exponential cost)
        const d = Math.max(1, Math.ceil(distance));
        const scaledCost = (0, index_js_1.harmonicScale)(d, 1.5);
        // Normalize to 0-1 risk score
        const score = Math.min(1, distance / 5);
        // Make decision
        let decision;
        let reason;
        if (score < RISK_THRESHOLDS.ALLOW) {
            decision = 'ALLOW';
            reason = 'Context within safe zone';
        }
        else if (score < RISK_THRESHOLDS.REVIEW) {
            decision = 'REVIEW';
            reason = 'Context requires review - moderate deviation';
        }
        else {
            decision = 'DENY';
            reason = 'Context exceeds safe threshold - high risk';
        }
        return {
            score,
            distance,
            scaledCost,
            decision,
            reason,
        };
    }
    /**
     * Sign a payload using RWP multi-signature envelope.
     *
     * @param payload - Data to sign
     * @param tongues - Tongues to sign with (default: ['ko'])
     * @returns Signed envelope and tongues used
     */
    sign(payload, tongues = ['ko']) {
        const envelope = (0, index_js_2.signRoundtable)(payload, tongues[0], 'scbe-api', this.keyring, tongues);
        return { envelope, tongues };
    }
    /**
     * Verify an envelope signature.
     *
     * @param envelope - RWP envelope to verify
     * @param options - Verification options (policy, maxAge, etc.)
     * @returns Verification result with valid tongues and payload
     */
    verify(envelope, options) {
        (0, index_js_2.clearNonceCache)(); // Clear for fresh verification
        const result = (0, index_js_2.verifyRoundtable)(envelope, this.keyring, options);
        return {
            valid: result.valid,
            validTongues: result.validTongues,
            payload: result.payload,
            reason: result.error ??
                (result.valid ? 'Signature valid - all tongues verified' : 'Signature invalid or tampered'),
        };
    }
    /**
     * Sign and verify with policy enforcement.
     *
     * Automatically determines required tongues based on action.
     *
     * @param payload - Data to sign
     * @param action - Action type (determines required tongues)
     * @returns Signed envelope
     */
    signForAction(payload, action) {
        const tongues = exports.Roundtable.requiredTongues(action);
        return this.sign(payload, tongues);
    }
    /**
     * Verify an envelope with policy enforcement.
     *
     * @param envelope - RWP envelope to verify
     * @param action - Expected action (determines required policy)
     * @returns Verification result
     */
    verifyForAction(envelope, action) {
        const policy = exports.Roundtable.suggestPolicy(action);
        return this.verify(envelope, { policy });
    }
    /**
     * Apply breathing transform to a context point.
     * Used for dynamic security adaptation.
     */
    breathe(context, intensity = 1.0) {
        const point = this.contextToPoint(context);
        const projected = (0, index_js_1.projectToBall)(point);
        const config = { amplitude: 0.1 * intensity, omega: 1.0 };
        return (0, index_js_1.breathTransform)(projected, Date.now() / 1000, config);
    }
    /**
     * Get the keyring (for advanced usage).
     */
    getKeyring() {
        return this.keyring;
    }
    /**
     * Set a custom keyring.
     */
    setKeyring(keyring) {
        this.keyring = keyring;
    }
    // ============================================================
    // Private Methods
    // ============================================================
    contextToPoint(context) {
        // Convert arbitrary context to 6D point using hash-based mapping
        const str = JSON.stringify(context);
        const hash = this.simpleHash(str);
        // Map hash to 6 dimensions, scaled to reasonable range
        const point = [];
        for (let i = 0; i < 6; i++) {
            // Extract 4 characters at a time, convert to number, scale to [-2, 2]
            const slice = hash.slice(i * 4, i * 4 + 4);
            const num = parseInt(slice, 16) / 65535; // 0 to 1
            point.push((num - 0.5) * 4); // -2 to 2
        }
        return point;
    }
    simpleHash(str) {
        // Simple hash for context-to-point mapping
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = (hash << 5) - hash + char;
            hash = hash & hash;
        }
        // Pad to 24 hex chars (6 dimensions * 4 chars each)
        const hex = Math.abs(hash).toString(16).padStart(8, '0');
        return (hex + hex + hex).slice(0, 24);
    }
}
exports.SCBE = SCBE;
// ============================================================
// Singleton Export for Simple Usage
// ============================================================
/** Default SCBE instance for simple usage */
exports.scbe = new SCBE();
/** Default security gate instance */
exports.defaultGate = new SecurityGate();
// ============================================================
// Convenience Functions
// ============================================================
/**
 * Evaluate risk of a context using the default SCBE instance.
 */
function evaluateRisk(context) {
    return exports.scbe.evaluateRisk(context);
}
/**
 * Sign a payload using the default SCBE instance.
 */
function sign(payload, tongues) {
    return exports.scbe.sign(payload, tongues);
}
/**
 * Sign a payload for a specific action (determines required tongues).
 */
function signForAction(payload, action) {
    return exports.scbe.signForAction(payload, action);
}
/**
 * Verify an envelope using the default SCBE instance.
 */
function verify(envelope, options) {
    return exports.scbe.verify(envelope, options);
}
/**
 * Verify an envelope for a specific action (enforces policy).
 */
function verifyForAction(envelope, action) {
    return exports.scbe.verifyForAction(envelope, action);
}
/**
 * Apply breathing transform to a context using the default SCBE instance.
 */
function breathe(context, intensity) {
    return exports.scbe.breathe(context, intensity);
}
/**
 * Check if an agent can perform an action (using default gate).
 */
async function checkAccess(agent, action, context) {
    return exports.defaultGate.check(agent, action, context);
}
/**
 * Get required tongues for an action.
 */
function requiredTongues(action) {
    return exports.Roundtable.requiredTongues(action);
}
//# sourceMappingURL=index.js.map