"use strict";
/**
 * @file swarm-formation.ts
 * @module ai_brain/swarm-formation
 * @layer Layer 10, Layer 13
 * @component Swarm Formation Coordination
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Implements swarm coordination primitives for multi-agent governance
 * in the unified brain manifold. Agents organize into geometric formations
 * that encode both spatial relationships and trust dynamics.
 *
 * Formation types:
 * - Defensive Circle: Equal-distance ring around a protected asset
 * - Investigation Wedge: Focused probing of suspicious activity
 * - Pursuit Line: Tracking a moving adversary
 * - Consensus Ring: BFT voting formation with spatial weighting
 * - Patrol Grid: Area coverage for continuous monitoring
 *
 * Trust-weighted influence ensures that higher-trust agents have more
 * impact on swarm decisions, while maintaining geometric coherence.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SwarmFormationManager = exports.DEFAULT_SWARM_CONFIG = void 0;
/**
 * Default swarm configuration
 */
exports.DEFAULT_SWARM_CONFIG = {
    defaultRadius: 0.3,
    minAgents: 3,
    maxAgents: 20,
    positionTolerance: 0.1,
    coherenceDecay: 0.01,
    trustExponent: 2,
};
// ═══════════════════════════════════════════════════════════════
// Swarm Formation Manager
// ═══════════════════════════════════════════════════════════════
/**
 * Swarm Formation Coordinator
 *
 * Manages geometric formations of agents in the unified brain manifold.
 * Each formation encodes both spatial relationships and trust dynamics,
 * enabling coordinated governance responses to threats.
 */
class SwarmFormationManager {
    formations = new Map();
    nextFormationId = 0;
    config;
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_SWARM_CONFIG, ...config };
    }
    /**
     * Create a defensive circle formation around a center point.
     * Agents are placed at equal angular intervals on a hyperbolic circle.
     *
     * @param agents - Array of { agentId, currentPosition, trustScore }
     * @param center - Center point to defend (21D)
     * @param radius - Circle radius in hyperbolic space
     * @param purpose - Why this formation was created
     * @returns Created formation
     */
    createDefensiveCircle(agents, center, radius = this.config.defaultRadius, purpose = 'Defensive perimeter') {
        const positions = agents.map((agent, idx) => {
            const angle = (2 * Math.PI * idx) / agents.length;
            const targetPosition = computeCirclePosition(center, radius, angle);
            return {
                agentId: agent.agentId,
                positionIndex: idx / agents.length,
                targetPosition,
                currentPosition: agent.currentPosition,
                trustWeight: agent.trustScore ** this.config.trustExponent,
                role: idx === 0 ? 'leader' : 'wing',
                distanceToCenter: radius,
            };
        });
        return this.registerFormation('defensive_circle', center, radius, positions, purpose);
    }
    /**
     * Create an investigation wedge focused on a target point.
     * Higher-trust agents form the leading edge.
     *
     * @param agents - Agents sorted by trust (highest first)
     * @param target - Target point to investigate (21D)
     * @param origin - Formation origin point (21D)
     * @param purpose - Investigation reason
     * @returns Created formation
     */
    createInvestigationWedge(agents, target, origin, purpose = 'Investigating suspicious activity') {
        // Sort by trust (highest first for leading edge)
        const sorted = [...agents].sort((a, b) => b.trustScore - a.trustScore);
        const center = origin.map((v, i) => (v + target[i]) / 2);
        const radius = euclideanDist(origin, target) / 2;
        const positions = sorted.map((agent, idx) => {
            const depth = idx / sorted.length; // 0 = tip, 1 = back
            const spread = depth * 0.3; // Wedge widens toward back
            const offset = (idx % 2 === 0 ? 1 : -1) * spread;
            const targetPosition = interpolatePositions(origin, target, depth);
            // Add lateral spread
            if (targetPosition.length > 1) {
                targetPosition[1] += offset;
            }
            return {
                agentId: agent.agentId,
                positionIndex: idx / sorted.length,
                targetPosition,
                currentPosition: agent.currentPosition,
                trustWeight: agent.trustScore ** this.config.trustExponent,
                role: idx === 0 ? 'leader' : idx < 3 ? 'wing' : 'support',
                distanceToCenter: euclideanDist(targetPosition, center),
            };
        });
        return this.registerFormation('investigation_wedge', center, radius, positions, purpose);
    }
    /**
     * Create a consensus ring for BFT voting.
     * Agents are positioned based on their voting weight.
     *
     * @param agents - Agents participating in consensus
     * @param center - Center of consensus ring (21D)
     * @param purpose - What is being voted on
     * @returns Created formation
     */
    createConsensusRing(agents, center, purpose = 'Consensus voting') {
        const totalTrust = agents.reduce((s, a) => s + a.trustScore, 0);
        const radius = this.config.defaultRadius * 0.5; // Tighter ring for consensus
        const positions = agents.map((agent, idx) => {
            // Position based on trust-weighted angle (higher trust = more arc space)
            const weightedAngle = (2 * Math.PI * agent.trustScore) / totalTrust;
            const cumulativeAngle = agents.slice(0, idx).reduce((s, a) => s + (2 * Math.PI * a.trustScore) / totalTrust, 0);
            const targetPosition = computeCirclePosition(center, radius, cumulativeAngle + weightedAngle / 2);
            return {
                agentId: agent.agentId,
                positionIndex: idx / agents.length,
                targetPosition,
                currentPosition: agent.currentPosition,
                trustWeight: agent.trustScore ** this.config.trustExponent,
                role: 'wing',
                distanceToCenter: radius,
            };
        });
        return this.registerFormation('consensus_ring', center, radius, positions, purpose);
    }
    /**
     * Compute formation health.
     * Health = weighted average of how close agents are to their target positions.
     *
     * @param formationId - Formation to evaluate
     * @returns Health value [0, 1]
     */
    computeHealth(formationId) {
        const formation = this.formations.get(formationId);
        if (!formation)
            return 0;
        let weightedSum = 0;
        let totalWeight = 0;
        for (const pos of formation.positions) {
            const dist = euclideanDist(pos.currentPosition, pos.targetPosition);
            const positionHealth = Math.max(0, 1 - dist / this.config.positionTolerance);
            weightedSum += positionHealth * pos.trustWeight;
            totalWeight += pos.trustWeight;
        }
        formation.health = totalWeight > 0 ? weightedSum / totalWeight : 0;
        return formation.health;
    }
    /**
     * Compute formation coherence.
     * Coherence measures how well the formation maintains its geometric structure.
     *
     * @param formationId - Formation to evaluate
     * @returns Coherence value [0, 1]
     */
    computeCoherence(formationId) {
        const formation = this.formations.get(formationId);
        if (!formation || formation.positions.length < 2)
            return 1;
        // Compute pairwise distance preservation
        let distortionSum = 0;
        let pairs = 0;
        for (let i = 0; i < formation.positions.length; i++) {
            for (let j = i + 1; j < formation.positions.length; j++) {
                const targetDist = euclideanDist(formation.positions[i].targetPosition, formation.positions[j].targetPosition);
                const actualDist = euclideanDist(formation.positions[i].currentPosition, formation.positions[j].currentPosition);
                if (targetDist > 1e-12) {
                    const distortion = Math.abs(actualDist - targetDist) / targetDist;
                    distortionSum += distortion;
                }
                pairs++;
            }
        }
        formation.coherence = pairs > 0 ? Math.max(0, 1 - distortionSum / pairs) : 1;
        return formation.coherence;
    }
    /**
     * Update agent positions within a formation.
     *
     * @param formationId - Formation to update
     * @param agentPositions - Map of agentId -> current 21D position
     */
    updatePositions(formationId, agentPositions) {
        const formation = this.formations.get(formationId);
        if (!formation)
            return;
        for (const pos of formation.positions) {
            const currentPos = agentPositions.get(pos.agentId);
            if (currentPos) {
                pos.currentPosition = currentPos;
                pos.distanceToCenter = euclideanDist(currentPos, formation.center);
            }
        }
    }
    /**
     * Compute trust-weighted influence of the formation on a risk decision.
     * Returns a weighted vote based on agent trust scores and positions.
     */
    computeWeightedVote(formationId) {
        const formation = this.formations.get(formationId);
        if (!formation)
            return { allow: 0, deny: 0, total: 0 };
        let allowWeight = 0;
        let denyWeight = 0;
        for (const pos of formation.positions) {
            // Agents closer to center have more influence
            const proximityWeight = Math.max(0, 1 - pos.distanceToCenter / (formation.radius * 2));
            const influence = pos.trustWeight * proximityWeight;
            // Use trust as proxy for vote direction (high trust = allow)
            const trustThreshold = 0.5;
            const inferredTrust = Math.pow(pos.trustWeight, 1 / this.config.trustExponent);
            if (inferredTrust >= trustThreshold) {
                allowWeight += influence;
            }
            else {
                denyWeight += influence;
            }
        }
        const total = allowWeight + denyWeight;
        return { allow: allowWeight, deny: denyWeight, total };
    }
    /**
     * Get a formation by ID
     */
    getFormation(formationId) {
        return this.formations.get(formationId);
    }
    /**
     * Get all active formations
     */
    getAllFormations() {
        return Array.from(this.formations.values());
    }
    /**
     * Dissolve a formation
     */
    dissolveFormation(formationId) {
        return this.formations.delete(formationId);
    }
    /**
     * Get formation count
     */
    get formationCount() {
        return this.formations.size;
    }
    // ═══════════════════════════════════════════════════════════════
    // Private Methods
    // ═══════════════════════════════════════════════════════════════
    registerFormation(type, center, radius, positions, purpose) {
        const id = `formation-${this.nextFormationId++}`;
        const formation = {
            id,
            type,
            center,
            radius,
            positions,
            health: 1,
            coherence: 1,
            purpose,
            createdAt: Date.now(),
        };
        this.formations.set(id, formation);
        return formation;
    }
}
exports.SwarmFormationManager = SwarmFormationManager;
// ═══════════════════════════════════════════════════════════════
// Geometry Helpers
// ═══════════════════════════════════════════════════════════════
function computeCirclePosition(center, radius, angle) {
    const pos = [...center];
    // Use first two navigation dimensions (indices 6, 7) for angular placement
    if (pos.length > 7) {
        pos[6] = (pos[6] ?? 0) + radius * Math.cos(angle);
        pos[7] = (pos[7] ?? 0) + radius * Math.sin(angle);
    }
    else if (pos.length >= 2) {
        pos[0] += radius * Math.cos(angle);
        pos[1] += radius * Math.sin(angle);
    }
    return pos;
}
function interpolatePositions(from, to, t) {
    const len = Math.min(from.length, to.length);
    const result = new Array(len);
    for (let i = 0; i < len; i++) {
        result[i] = from[i] + t * (to[i] - from[i]);
    }
    return result;
}
function euclideanDist(a, b) {
    let sum = 0;
    const len = Math.min(a.length, b.length);
    for (let i = 0; i < len; i++) {
        const diff = a[i] - b[i];
        sum += diff * diff;
    }
    return Math.sqrt(sum);
}
//# sourceMappingURL=swarm-formation.js.map