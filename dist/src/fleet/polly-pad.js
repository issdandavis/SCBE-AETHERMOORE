"use strict";
/**
 * Polly Pad - Personal Agent Workspaces with Dimensional Flux
 *
 * Each AI agent gets their own "Kindle pad" - a persistent, auditable
 * workspace that grows with them. Like students at school, agents can
 * take notes, draw sketches, save tools, and level up through Sacred Tongue tiers.
 *
 * Dimensional States:
 * - POLLY (ν ≈ 1.0): Full participation, all tools active
 * - QUASI (0.5 < ν < 1): Partial, limited tools
 * - DEMI (0 < ν < 0.5): Minimal, read-only
 * - COLLAPSED (ν ≈ 0): Offline, archived
 *
 * @module fleet/polly-pad
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PollyPadManager = exports.TIER_THRESHOLDS = void 0;
exports.getNextTier = getNextTier;
exports.getXPForNextTier = getXPForNextTier;
const types_1 = require("./types");
/**
 * Tier progression thresholds (like grade levels)
 */
exports.TIER_THRESHOLDS = {
    KO: { xp: 0, name: 'Kindergarten', description: 'Basic tasks, high supervision' },
    AV: { xp: 100, name: 'Elementary', description: 'I/O tasks, moderate supervision' },
    RU: { xp: 300, name: 'Middle School', description: 'Policy-aware, some autonomy' },
    CA: { xp: 600, name: 'High School', description: 'Logic tasks, trusted' },
    UM: { xp: 1000, name: 'University', description: 'Security tasks, high trust' },
    DR: { xp: 2000, name: 'Doctorate', description: 'Architectural decisions, full autonomy' },
};
/**
 * Get next tier in progression
 */
function getNextTier(current) {
    const order = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const index = order.indexOf(current);
    if (index < order.length - 1) {
        return order[index + 1];
    }
    return null;
}
/**
 * Calculate XP needed for next tier
 */
function getXPForNextTier(current) {
    const next = getNextTier(current);
    if (!next)
        return Infinity;
    return exports.TIER_THRESHOLDS[next].xp;
}
/**
 * Polly Pad Manager
 *
 * Manages all agent pads in the system.
 */
class PollyPadManager {
    pads = new Map();
    padsByAgent = new Map(); // agentId -> padId
    /**
     * Create a new Polly Pad for an agent
     */
    createPad(agentId, name, initialTier = 'KO', trustVector = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]) {
        const id = this.generatePadId(agentId);
        const pad = {
            id,
            agentId,
            name,
            // Start at full participation
            nu: 1.0,
            dimensionalState: 'POLLY',
            fluxRate: 0,
            // Empty workspace
            notes: [],
            sketches: [],
            tools: [],
            // No swarm initially
            coherenceScore: 1.0,
            // Governance
            tier: initialTier,
            trustVector,
            experiencePoints: 0,
            nextTierThreshold: getXPForNextTier(initialTier),
            // Stats
            tasksCompleted: 0,
            successRate: 1.0,
            collaborations: 0,
            toolsCreated: 0,
            milestones: [],
            // Audit
            auditLog: [],
            auditStatus: 'clean',
            createdAt: Date.now(),
            updatedAt: Date.now(),
        };
        this.pads.set(id, pad);
        this.padsByAgent.set(agentId, id);
        return pad;
    }
    /**
     * Get pad by ID
     */
    getPad(id) {
        return this.pads.get(id);
    }
    /**
     * Get pad by agent ID
     */
    getPadByAgent(agentId) {
        const padId = this.padsByAgent.get(agentId);
        return padId ? this.pads.get(padId) : undefined;
    }
    /**
     * Get all pads
     */
    getAllPads() {
        return Array.from(this.pads.values());
    }
    /**
     * Get pads by dimensional state
     */
    getPadsByState(state) {
        return this.getAllPads().filter((p) => p.dimensionalState === state);
    }
    /**
     * Get pads by tier
     */
    getPadsByTier(tier) {
        return this.getAllPads().filter((p) => p.tier === tier);
    }
    // === Workspace Operations ===
    /**
     * Add a note to a pad
     */
    addNote(padId, note) {
        const pad = this.pads.get(padId);
        if (!pad)
            throw new Error(`Pad ${padId} not found`);
        if (pad.dimensionalState === 'COLLAPSED') {
            throw new Error('Cannot add notes to collapsed pad');
        }
        const newNote = {
            ...note,
            id: `note-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
            createdAt: Date.now(),
            updatedAt: Date.now(),
        };
        pad.notes.push(newNote);
        pad.updatedAt = Date.now();
        this.addXP(padId, 5, 'note_created');
        return newNote;
    }
    /**
     * Add a sketch to a pad
     */
    addSketch(padId, sketch) {
        const pad = this.pads.get(padId);
        if (!pad)
            throw new Error(`Pad ${padId} not found`);
        if (pad.dimensionalState === 'COLLAPSED' || pad.dimensionalState === 'DEMI') {
            throw new Error('Cannot add sketches in current dimensional state');
        }
        const newSketch = {
            ...sketch,
            id: `sketch-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
            createdAt: Date.now(),
            updatedAt: Date.now(),
        };
        pad.sketches.push(newSketch);
        pad.updatedAt = Date.now();
        this.addXP(padId, 10, 'sketch_created');
        return newSketch;
    }
    /**
     * Add a tool to a pad
     */
    addTool(padId, tool) {
        const pad = this.pads.get(padId);
        if (!pad)
            throw new Error(`Pad ${padId} not found`);
        if (pad.dimensionalState !== 'POLLY') {
            throw new Error('Can only create tools in POLLY state');
        }
        const newTool = {
            ...tool,
            id: `tool-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
            createdAt: Date.now(),
            usageCount: 0,
            effectiveness: 0.5,
        };
        pad.tools.push(newTool);
        pad.toolsCreated++;
        pad.updatedAt = Date.now();
        this.addXP(padId, 20, 'tool_created');
        // Check for tool creation milestone
        if (pad.toolsCreated === 5) {
            this.addMilestone(padId, 'Tool Smith', 'Created 5 custom tools', 'tool_creation');
        }
        return newTool;
    }
    /**
     * Use a tool (increment usage, update effectiveness)
     */
    useTool(padId, toolId, success) {
        const pad = this.pads.get(padId);
        if (!pad)
            throw new Error(`Pad ${padId} not found`);
        const tool = pad.tools.find((t) => t.id === toolId);
        if (!tool)
            throw new Error(`Tool ${toolId} not found`);
        tool.usageCount++;
        tool.lastUsed = Date.now();
        // Update effectiveness with exponential moving average
        const alpha = 0.2;
        tool.effectiveness = alpha * (success ? 1 : 0) + (1 - alpha) * tool.effectiveness;
        pad.updatedAt = Date.now();
    }
    // === Dimensional Flux ===
    /**
     * Update flux coefficient ν
     */
    updateFlux(padId, newNu) {
        const pad = this.pads.get(padId);
        if (!pad)
            throw new Error(`Pad ${padId} not found`);
        const oldState = pad.dimensionalState;
        pad.nu = Math.max(0, Math.min(1, newNu));
        pad.dimensionalState = (0, types_1.getDimensionalState)(pad.nu);
        pad.updatedAt = Date.now();
        // Log state transition
        if (oldState !== pad.dimensionalState) {
            this.addAuditEntry(padId, {
                auditorId: 'system',
                target: 'behavior',
                result: 'pass',
                findings: `Dimensional state changed: ${oldState} → ${pad.dimensionalState}`,
                actions: [`nu updated to ${pad.nu.toFixed(3)}`],
            });
        }
    }
    /**
     * Gradually transition to target ν
     */
    setTargetFlux(padId, targetNu, rate = 0.01) {
        const pad = this.pads.get(padId);
        if (!pad)
            throw new Error(`Pad ${padId} not found`);
        pad.targetNu = Math.max(0, Math.min(1, targetNu));
        pad.fluxRate = rate;
    }
    /**
     * Step flux toward target (call periodically)
     */
    stepFlux(padId) {
        const pad = this.pads.get(padId);
        if (!pad || pad.targetNu === undefined)
            return;
        const diff = pad.targetNu - pad.nu;
        if (Math.abs(diff) < 0.001) {
            pad.nu = pad.targetNu;
            pad.targetNu = undefined;
            pad.fluxRate = 0;
        }
        else {
            pad.nu += Math.sign(diff) * pad.fluxRate;
            pad.nu = Math.max(0, Math.min(1, pad.nu));
        }
        pad.dimensionalState = (0, types_1.getDimensionalState)(pad.nu);
        pad.updatedAt = Date.now();
    }
    // === Growth & Progression ===
    /**
     * Add experience points
     */
    addXP(padId, amount, reason) {
        const pad = this.pads.get(padId);
        if (!pad)
            return;
        pad.experiencePoints += amount;
        // Check for tier promotion
        const nextTier = getNextTier(pad.tier);
        if (nextTier && pad.experiencePoints >= exports.TIER_THRESHOLDS[nextTier].xp) {
            this.promoteTier(padId);
        }
        pad.updatedAt = Date.now();
    }
    /**
     * Promote to next tier
     */
    promoteTier(padId) {
        const pad = this.pads.get(padId);
        if (!pad)
            return false;
        const nextTier = getNextTier(pad.tier);
        if (!nextTier)
            return false;
        const oldTier = pad.tier;
        pad.tier = nextTier;
        pad.nextTierThreshold = getXPForNextTier(nextTier);
        // Add promotion milestone
        this.addMilestone(padId, `Promoted to ${exports.TIER_THRESHOLDS[nextTier].name}`, `Advanced from ${oldTier} to ${nextTier}`, 'promotion');
        // Audit the promotion
        this.addAuditEntry(padId, {
            auditorId: 'system',
            target: 'behavior',
            result: 'pass',
            findings: `Tier promotion: ${oldTier} → ${nextTier}`,
            actions: ['Tier updated', 'Milestone added'],
        });
        pad.updatedAt = Date.now();
        return true;
    }
    /**
     * Demote to previous tier
     */
    demoteTier(padId, demotionReason) {
        const pad = this.pads.get(padId);
        if (!pad)
            return false;
        const order = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
        const index = order.indexOf(pad.tier);
        if (index <= 0)
            return false;
        const oldTier = pad.tier;
        pad.tier = order[index - 1];
        pad.nextTierThreshold = getXPForNextTier(pad.tier);
        // Audit the demotion
        this.addAuditEntry(padId, {
            auditorId: 'system',
            target: 'behavior',
            result: 'warning',
            findings: `Tier demotion: ${oldTier} → ${pad.tier}. Reason: ${demotionReason}`,
            actions: ['Tier reduced'],
        });
        pad.updatedAt = Date.now();
        return true;
    }
    /**
     * Record task completion
     */
    recordTaskCompletion(padId, success) {
        const pad = this.pads.get(padId);
        if (!pad)
            return;
        pad.tasksCompleted++;
        // Update success rate
        const alpha = 0.1;
        pad.successRate = alpha * (success ? 1 : 0) + (1 - alpha) * pad.successRate;
        // Add XP
        this.addXP(padId, success ? 15 : 2, success ? 'task_success' : 'task_attempt');
        // Check milestones
        if (pad.tasksCompleted === 10) {
            this.addMilestone(padId, 'First Steps', 'Completed 10 tasks', 'tasks');
        }
        else if (pad.tasksCompleted === 50) {
            this.addMilestone(padId, 'Journeyman', 'Completed 50 tasks', 'tasks');
        }
        else if (pad.tasksCompleted === 100) {
            this.addMilestone(padId, 'Veteran', 'Completed 100 tasks', 'tasks');
        }
        pad.updatedAt = Date.now();
    }
    /**
     * Record collaboration
     */
    recordCollaboration(padId) {
        const pad = this.pads.get(padId);
        if (!pad)
            return;
        pad.collaborations++;
        this.addXP(padId, 10, 'collaboration');
        if (pad.collaborations === 10) {
            this.addMilestone(padId, 'Team Player', 'Collaborated 10 times', 'collaboration');
        }
        pad.updatedAt = Date.now();
    }
    /**
     * Add a milestone
     */
    addMilestone(padId, name, description, trigger) {
        const pad = this.pads.get(padId);
        if (!pad)
            return;
        pad.milestones.push({
            id: `milestone-${Date.now().toString(36)}`,
            name,
            description,
            achievedAt: Date.now(),
            tierAtTime: pad.tier,
            trigger,
        });
    }
    // === Audit ===
    /**
     * Add audit entry
     */
    addAuditEntry(padId, entry) {
        const pad = this.pads.get(padId);
        if (!pad)
            return;
        pad.auditLog.push({
            ...entry,
            id: `audit-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
            timestamp: Date.now(),
        });
        pad.lastAuditAt = Date.now();
        pad.lastAuditBy = entry.auditorId;
        // Update audit status based on result
        if (entry.result === 'fail') {
            pad.auditStatus = 'restricted';
        }
        else if (entry.result === 'warning' && pad.auditStatus === 'clean') {
            pad.auditStatus = 'flagged';
        }
        pad.updatedAt = Date.now();
    }
    /**
     * Perform full audit on a pad
     */
    auditPad(padId, auditorId) {
        const pad = this.pads.get(padId);
        if (!pad)
            throw new Error(`Pad ${padId} not found`);
        const findings = [];
        let result = 'pass';
        // Check success rate
        if (pad.successRate < 0.5) {
            findings.push(`Low success rate: ${(pad.successRate * 100).toFixed(1)}%`);
            result = 'warning';
        }
        // Check tool effectiveness
        const lowEffectTools = pad.tools.filter((t) => t.effectiveness < 0.3 && t.usageCount > 5);
        if (lowEffectTools.length > 0) {
            findings.push(`${lowEffectTools.length} tools with low effectiveness`);
            result = 'warning';
        }
        // Check dimensional state
        if (pad.dimensionalState === 'DEMI' || pad.dimensionalState === 'COLLAPSED') {
            findings.push(`Pad in ${pad.dimensionalState} state`);
        }
        // Check coherence
        if (pad.coherenceScore < 0.5) {
            findings.push(`Low swarm coherence: ${(pad.coherenceScore * 100).toFixed(1)}%`);
            result = 'warning';
        }
        if (findings.length === 0) {
            findings.push('All checks passed');
        }
        const entry = {
            auditorId,
            target: 'full',
            result,
            findings: findings.join('; '),
            actions: result === 'pass' ? ['Audit complete'] : ['Review recommended'],
        };
        this.addAuditEntry(padId, entry);
        // Clear flagged status if passing
        if (result === 'pass' && pad.auditStatus === 'flagged') {
            pad.auditStatus = 'clean';
        }
        return { ...entry, id: pad.auditLog[pad.auditLog.length - 1].id, timestamp: Date.now() };
    }
    // === Statistics ===
    /**
     * Get pad statistics
     */
    getPadStats(padId) {
        const pad = this.pads.get(padId);
        if (!pad)
            return undefined;
        const xpToNext = pad.nextTierThreshold - pad.experiencePoints;
        const prevThreshold = exports.TIER_THRESHOLDS[pad.tier].xp;
        const progress = (pad.experiencePoints - prevThreshold) / (pad.nextTierThreshold - prevThreshold);
        return {
            tier: pad.tier,
            tierName: exports.TIER_THRESHOLDS[pad.tier].name,
            xp: pad.experiencePoints,
            xpToNext: Math.max(0, xpToNext),
            progress: Math.min(1, Math.max(0, progress)),
            tasksCompleted: pad.tasksCompleted,
            successRate: pad.successRate,
            toolsCreated: pad.toolsCreated,
            milestonesAchieved: pad.milestones.length,
            dimensionalState: pad.dimensionalState,
            nu: pad.nu,
        };
    }
    /**
     * Generate pad ID
     */
    generatePadId(agentId) {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 6);
        return `pad-${agentId.substring(0, 8)}-${timestamp}-${random}`;
    }
}
exports.PollyPadManager = PollyPadManager;
//# sourceMappingURL=polly-pad.js.map