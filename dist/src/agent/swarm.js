"use strict";
/**
 * Swarm Coordination in Poincaré Ball
 *
 * Implements agent swarm coordination using hyperbolic geometry:
 * - Formation control (dispersed, convergent, ring)
 * - Centroid calculation in hyperbolic space
 * - Byzantine fault tolerant consensus
 * - Rogue agent detection via PHDM coherence
 *
 * @module agent/swarm
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SwarmCoordinator = exports.ROGUE_QUARANTINE_THRESHOLD = exports.MAX_HYPERBOLIC_DISTANCE = exports.MIN_COHERENCE_THRESHOLD = void 0;
exports.mobiusAdd = mobiusAdd;
exports.mobiusScale = mobiusScale;
exports.hyperbolicCentroid = hyperbolicCentroid;
exports.generateRingFormation = generateRingFormation;
exports.generateDispersedFormation = generateDispersedFormation;
exports.generateConvergentFormation = generateConvergentFormation;
exports.createFormationTarget = createFormationTarget;
exports.collectVotes = collectVotes;
exports.weightedVoteCount = weightedVoteCount;
exports.runWeightedConsensus = runWeightedConsensus;
exports.detectRogueAgent = detectRogueAgent;
exports.quarantineAgent = quarantineAgent;
const ss1_js_1 = require("../tokenizer/ss1.js");
const types_js_1 = require("./types.js");
// ============================================================================
// Constants
// ============================================================================
/** Minimum coherence for healthy agent */
exports.MIN_COHERENCE_THRESHOLD = 0.3;
/** Maximum hyperbolic distance before rogue suspicion */
exports.MAX_HYPERBOLIC_DISTANCE = 2.0;
/** Rogue confidence threshold for quarantine */
exports.ROGUE_QUARANTINE_THRESHOLD = 0.8;
// ============================================================================
// Hyperbolic Operations
// ============================================================================
/**
 * Möbius addition in Poincaré ball
 *
 * Computes u ⊕ v (hyperbolic addition)
 */
function mobiusAdd(u, v) {
    const uNormSq = u.x * u.x + u.y * u.y + u.z * u.z;
    const vNormSq = v.x * v.x + v.y * v.y + v.z * v.z;
    const uDotV = u.x * v.x + u.y * v.y + u.z * v.z;
    const denominator = 1 + 2 * uDotV + uNormSq * vNormSq;
    if (denominator < 1e-10) {
        return { x: 0, y: 0, z: 0 };
    }
    const factor1 = 1 + 2 * uDotV + vNormSq;
    const factor2 = 1 - uNormSq;
    return {
        x: (factor1 * u.x + factor2 * v.x) / denominator,
        y: (factor1 * u.y + factor2 * v.y) / denominator,
        z: (factor1 * u.z + factor2 * v.z) / denominator,
    };
}
/**
 * Scalar multiplication in Poincaré ball
 *
 * Computes t ⊗ v (hyperbolic scaling)
 */
function mobiusScale(t, v) {
    const norm = (0, types_js_1.poincareNorm)(v);
    if (norm < 1e-10) {
        return { x: 0, y: 0, z: 0 };
    }
    const targetNorm = Math.tanh(t * Math.atanh(norm));
    const scale = targetNorm / norm;
    return {
        x: v.x * scale,
        y: v.y * scale,
        z: v.z * scale,
    };
}
/**
 * Compute weighted centroid in hyperbolic space
 *
 * Uses Einstein midpoint formula generalized to Poincaré ball
 */
function hyperbolicCentroid(points, weights) {
    if (points.length === 0) {
        return { x: 0, y: 0, z: 0 };
    }
    if (points.length === 1) {
        return { ...points[0] };
    }
    // Normalize weights
    const w = weights || points.map(() => 1);
    const totalWeight = w.reduce((a, b) => a + b, 0);
    if (totalWeight < 1e-10) {
        return { x: 0, y: 0, z: 0 };
    }
    // Compute weighted sum using Möbius operations
    let centroid = { x: 0, y: 0, z: 0 };
    for (let i = 0; i < points.length; i++) {
        const scaledPoint = mobiusScale(w[i] / totalWeight, points[i]);
        centroid = mobiusAdd(centroid, scaledPoint);
    }
    return centroid;
}
// ============================================================================
// Swarm Formation
// ============================================================================
/**
 * Generate ring formation positions for all tongues
 */
function generateRingFormation(radius = 0.5) {
    const positions = new Map();
    for (const tongue of ss1_js_1.TONGUE_CODES) {
        const phase = (0, types_js_1.phaseToRadians)(tongue);
        positions.set(tongue, {
            x: radius * Math.cos(phase),
            y: radius * Math.sin(phase),
            z: 0,
        });
    }
    return positions;
}
/**
 * Generate dispersed formation (spread across ball)
 */
function generateDispersedFormation() {
    const positions = new Map();
    let index = 0;
    for (const tongue of ss1_js_1.TONGUE_CODES) {
        const phi = Math.acos(1 - (2 * (index + 0.5)) / ss1_js_1.TONGUE_CODES.length);
        const theta = Math.PI * (1 + Math.sqrt(5)) * index;
        const radius = 0.4 + 0.3 * (index / (ss1_js_1.TONGUE_CODES.length - 1));
        positions.set(tongue, {
            x: radius * Math.sin(phi) * Math.cos(theta),
            y: radius * Math.sin(phi) * Math.sin(theta),
            z: radius * Math.cos(phi),
        });
        index++;
    }
    return positions;
}
/**
 * Generate convergent formation (clustered near center)
 */
function generateConvergentFormation() {
    const positions = new Map();
    for (const tongue of ss1_js_1.TONGUE_CODES) {
        const phase = (0, types_js_1.phaseToRadians)(tongue);
        const radius = 0.1 + 0.1 * Math.random();
        positions.set(tongue, {
            x: radius * Math.cos(phase),
            y: radius * Math.sin(phase),
            z: (Math.random() - 0.5) * 0.05,
        });
    }
    return positions;
}
/**
 * Create formation target
 */
function createFormationTarget(formation, transitionDuration = 5000) {
    let positions;
    switch (formation) {
        case 'ring':
            positions = generateRingFormation();
            break;
        case 'convergent':
            positions = generateConvergentFormation();
            break;
        case 'dispersed':
        default:
            positions = generateDispersedFormation();
            break;
    }
    return {
        formation,
        positions,
        transitionDuration,
    };
}
// ============================================================================
// Swarm State Management
// ============================================================================
/**
 * Swarm coordinator for managing multiple agents
 */
class SwarmCoordinator {
    agents = new Map();
    formation = 'dispersed';
    /**
     * Add agent to swarm
     */
    addAgent(agent) {
        this.agents.set(agent.id, agent);
    }
    /**
     * Remove agent from swarm
     */
    removeAgent(agentId) {
        this.agents.delete(agentId);
    }
    /**
     * Update agent position
     */
    updatePosition(agentId, position) {
        const agent = this.agents.get(agentId);
        if (!agent)
            return false;
        if ((0, types_js_1.poincareNorm)(position) >= 1)
            return false;
        agent.position = position;
        return true;
    }
    /**
     * Get current swarm state
     */
    getState() {
        const agentList = Array.from(this.agents.values());
        const activeAgents = agentList.filter((a) => a.status === 'active' || a.status === 'degraded');
        const centroid = hyperbolicCentroid(activeAgents.map((a) => a.position), activeAgents.map((a) => a.weight));
        const totalCoherence = activeAgents.reduce((sum, a) => sum + a.coherence, 0);
        const avgCoherence = activeAgents.length > 0 ? totalCoherence / activeAgents.length : 0;
        return {
            agents: this.agents,
            formation: this.formation,
            centroid,
            averageCoherence: avgCoherence,
            lastUpdate: Date.now(),
        };
    }
    /**
     * Set formation and transition agents
     */
    async setFormation(formation, onPositionUpdate) {
        this.formation = formation;
        const target = createFormationTarget(formation);
        for (const [agentId, agent] of this.agents) {
            const targetPos = target.positions.get(agent.tongue);
            if (targetPos) {
                agent.position = targetPos;
                if (onPositionUpdate) {
                    await onPositionUpdate(agentId, targetPos);
                }
            }
        }
    }
    /**
     * Get agents by tongue
     */
    getAgentsByTongue(tongue) {
        return Array.from(this.agents.values()).filter((a) => a.tongue === tongue);
    }
    /**
     * Get active agent count
     */
    getActiveCount() {
        return Array.from(this.agents.values()).filter((a) => a.status === 'active' || a.status === 'degraded').length;
    }
}
exports.SwarmCoordinator = SwarmCoordinator;
// ============================================================================
// Byzantine Fault Tolerance
// ============================================================================
/**
 * Collect votes for BFT consensus
 */
function collectVotes(votes, config) {
    const now = Date.now();
    // Filter valid votes (within timeout)
    const validVotes = votes.filter((v) => now - v.timestamp < config.timeoutMs);
    // Count votes by decision
    const allowVotes = validVotes.filter((v) => v.decision === 'ALLOW');
    const denyVotes = validVotes.filter((v) => v.decision === 'DENY');
    const quarantineVotes = validVotes.filter((v) => v.decision === 'QUARANTINE');
    // Determine decision based on quorum
    let decision = 'NO_QUORUM';
    let quorumReached = false;
    if (allowVotes.length >= config.quorum) {
        decision = 'ALLOW';
        quorumReached = true;
    }
    else if (denyVotes.length >= config.quorum) {
        decision = 'DENY';
        quorumReached = true;
    }
    else if (quarantineVotes.length >= config.quorum) {
        decision = 'QUARANTINE';
        quorumReached = true;
    }
    return {
        decision,
        votes: validVotes,
        quorumReached,
        consensusTimestamp: now,
    };
}
/**
 * Weight votes by tongue weight (φⁿ)
 */
function weightedVoteCount(votes) {
    return votes.reduce((sum, vote) => {
        const tongueIndex = types_js_1.TONGUE_INDICES[vote.tongue];
        const weight = Math.pow(types_js_1.GOLDEN_RATIO, tongueIndex);
        return sum + weight * vote.confidence;
    }, 0);
}
/**
 * Run BFT consensus with weighted votes
 */
function runWeightedConsensus(votes, config) {
    const now = Date.now();
    const validVotes = votes.filter((v) => now - v.timestamp < config.timeoutMs);
    const allowWeight = weightedVoteCount(validVotes.filter((v) => v.decision === 'ALLOW'));
    const denyWeight = weightedVoteCount(validVotes.filter((v) => v.decision === 'DENY'));
    const quarantineWeight = weightedVoteCount(validVotes.filter((v) => v.decision === 'QUARANTINE'));
    const totalWeight = allowWeight + denyWeight + quarantineWeight;
    const weightedQuorum = totalWeight * 0.5; // Need >50% of weight
    let decision = 'NO_QUORUM';
    let quorumReached = false;
    if (allowWeight > weightedQuorum) {
        decision = 'ALLOW';
        quorumReached = true;
    }
    else if (denyWeight > weightedQuorum) {
        decision = 'DENY';
        quorumReached = true;
    }
    else if (quarantineWeight > weightedQuorum) {
        decision = 'QUARANTINE';
        quorumReached = true;
    }
    return {
        decision,
        votes: validVotes,
        quorumReached,
        consensusTimestamp: now,
    };
}
// ============================================================================
// Rogue Detection
// ============================================================================
/**
 * Detect if an agent is behaving as rogue
 *
 * Uses PHDM (Polyhedral Holographic Distance Metric) coherence
 * and hyperbolic distance from expected position
 */
function detectRogueAgent(agent, swarmState, expectedPosition) {
    const indicators = [];
    let rogueScore = 0;
    // Check 1: Low coherence
    if (agent.coherence < exports.MIN_COHERENCE_THRESHOLD) {
        indicators.push(`low_coherence:${agent.coherence.toFixed(3)}`);
        rogueScore += 0.3;
    }
    // Check 2: Distance from centroid
    const distanceFromCentroid = (0, types_js_1.hyperbolicDistance)(agent.position, swarmState.centroid);
    if (distanceFromCentroid > exports.MAX_HYPERBOLIC_DISTANCE) {
        indicators.push(`far_from_centroid:${distanceFromCentroid.toFixed(3)}`);
        rogueScore += 0.25;
    }
    // Check 3: Distance from expected position
    if (expectedPosition) {
        const distanceFromExpected = (0, types_js_1.hyperbolicDistance)(agent.position, expectedPosition);
        if (distanceFromExpected > exports.MAX_HYPERBOLIC_DISTANCE * 0.5) {
            indicators.push(`deviated_position:${distanceFromExpected.toFixed(3)}`);
            rogueScore += 0.2;
        }
    }
    // Check 4: Degraded or quarantine status
    if (agent.status === 'degraded') {
        indicators.push('degraded_status');
        rogueScore += 0.15;
    }
    else if (agent.status === 'quarantine') {
        indicators.push('quarantine_status');
        rogueScore += 0.4;
    }
    // Check 5: Compare coherence to swarm average
    if (agent.coherence < swarmState.averageCoherence * 0.5) {
        indicators.push(`below_average_coherence`);
        rogueScore += 0.1;
    }
    // Clamp score to [0, 1]
    const confidence = Math.min(1, Math.max(0, rogueScore));
    const isRogue = confidence >= exports.ROGUE_QUARANTINE_THRESHOLD;
    let recommendedAction = 'none';
    if (confidence >= 0.9) {
        recommendedAction = 'terminate';
    }
    else if (confidence >= exports.ROGUE_QUARANTINE_THRESHOLD) {
        recommendedAction = 'quarantine';
    }
    else if (confidence >= 0.4) {
        recommendedAction = 'monitor';
    }
    return {
        agentId: agent.id,
        isRogue,
        confidence,
        indicators,
        recommendedAction,
    };
}
/**
 * Quarantine a rogue agent
 */
function quarantineAgent(agent) {
    return {
        ...agent,
        status: 'quarantine',
        coherence: 0,
        // Move to origin (isolated in hyperbolic space)
        position: { x: 0, y: 0, z: 0 },
    };
}
//# sourceMappingURL=swarm.js.map