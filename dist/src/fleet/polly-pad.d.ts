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
import { SpectralIdentity } from '../harmonic/spectral-identity';
import { DimensionalState, GovernanceTier } from './types';
/**
 * Audit status for pad review
 */
export type AuditStatus = 'clean' | 'flagged' | 'restricted' | 'pending';
/**
 * Note entry in a Polly Pad
 */
export interface PadNote {
    id: string;
    title: string;
    content: string;
    tags: string[];
    createdAt: number;
    updatedAt: number;
    /** Which task this note relates to */
    taskId?: string;
    /** Visibility to other pads */
    shared: boolean;
}
/**
 * Sketch/drawing in a Polly Pad
 */
export interface PadSketch {
    id: string;
    name: string;
    /** SVG or canvas data */
    data: string;
    /** Sketch type */
    type: 'diagram' | 'flowchart' | 'wireframe' | 'freehand' | 'architecture';
    createdAt: number;
    updatedAt: number;
    taskId?: string;
    shared: boolean;
}
/**
 * Saved tool configuration
 */
export interface PadTool {
    id: string;
    name: string;
    description: string;
    /** Tool type */
    type: 'snippet' | 'template' | 'script' | 'prompt' | 'config';
    /** Tool content/code */
    content: string;
    /** Usage count */
    usageCount: number;
    /** Last used timestamp */
    lastUsed?: number;
    createdAt: number;
    /** Effectiveness rating (0-1) */
    effectiveness: number;
}
/**
 * Audit log entry
 */
export interface AuditEntry {
    id: string;
    timestamp: number;
    /** Who performed the audit */
    auditorId: string;
    /** What was audited */
    target: 'notes' | 'sketches' | 'tools' | 'behavior' | 'full';
    /** Audit result */
    result: 'pass' | 'warning' | 'fail';
    /** Findings/comments */
    findings: string;
    /** Actions taken */
    actions?: string[];
}
/**
 * Growth milestone
 */
export interface GrowthMilestone {
    id: string;
    name: string;
    description: string;
    achievedAt: number;
    /** Tier when achieved */
    tierAtTime: GovernanceTier;
    /** What triggered this milestone */
    trigger: 'tasks' | 'audit' | 'promotion' | 'collaboration' | 'tool_creation';
}
/**
 * Polly Pad - Personal Agent Workspace
 */
export interface PollyPad {
    /** Unique pad ID */
    id: string;
    /** Agent ID this pad belongs to */
    agentId: string;
    /** Pad display name */
    name: string;
    /** Agent's spectral identity */
    spectralIdentity?: SpectralIdentity;
    /** Flux coefficient ν ∈ [0, 1] */
    nu: number;
    /** Current dimensional state */
    dimensionalState: DimensionalState;
    /** Rate of flux change */
    fluxRate: number;
    /** Target ν (for gradual transitions) */
    targetNu?: number;
    /** Notes the agent has written */
    notes: PadNote[];
    /** Sketches/diagrams */
    sketches: PadSketch[];
    /** Saved tools and templates */
    tools: PadTool[];
    /** Which swarm this pad belongs to */
    swarmId?: string;
    /** Coherence with swarm (0-1) */
    coherenceScore: number;
    /** Last swarm sync timestamp */
    lastSwarmSync?: number;
    /** Current governance tier (like grade level) */
    tier: GovernanceTier;
    /** 6D trust vector */
    trustVector: number[];
    /** Experience points toward next tier */
    experiencePoints: number;
    /** Points needed for next tier */
    nextTierThreshold: number;
    /** Tasks completed */
    tasksCompleted: number;
    /** Success rate (0-1) */
    successRate: number;
    /** Collaboration count */
    collaborations: number;
    /** Tools created */
    toolsCreated: number;
    /** Growth milestones achieved */
    milestones: GrowthMilestone[];
    /** Audit log */
    auditLog: AuditEntry[];
    /** Current audit status */
    auditStatus: AuditStatus;
    /** Last audit timestamp */
    lastAuditAt?: number;
    /** Who last audited */
    lastAuditBy?: string;
    createdAt: number;
    updatedAt: number;
}
/**
 * Tier progression thresholds (like grade levels)
 */
export declare const TIER_THRESHOLDS: Record<GovernanceTier, {
    xp: number;
    name: string;
    description: string;
}>;
/**
 * Get next tier in progression
 */
export declare function getNextTier(current: GovernanceTier): GovernanceTier | null;
/**
 * Calculate XP needed for next tier
 */
export declare function getXPForNextTier(current: GovernanceTier): number;
/**
 * Polly Pad Manager
 *
 * Manages all agent pads in the system.
 */
export declare class PollyPadManager {
    private pads;
    private padsByAgent;
    /**
     * Create a new Polly Pad for an agent
     */
    createPad(agentId: string, name: string, initialTier?: GovernanceTier, trustVector?: number[]): PollyPad;
    /**
     * Get pad by ID
     */
    getPad(id: string): PollyPad | undefined;
    /**
     * Get pad by agent ID
     */
    getPadByAgent(agentId: string): PollyPad | undefined;
    /**
     * Get all pads
     */
    getAllPads(): PollyPad[];
    /**
     * Get pads by dimensional state
     */
    getPadsByState(state: DimensionalState): PollyPad[];
    /**
     * Get pads by tier
     */
    getPadsByTier(tier: GovernanceTier): PollyPad[];
    /**
     * Add a note to a pad
     */
    addNote(padId: string, note: Omit<PadNote, 'id' | 'createdAt' | 'updatedAt'>): PadNote;
    /**
     * Add a sketch to a pad
     */
    addSketch(padId: string, sketch: Omit<PadSketch, 'id' | 'createdAt' | 'updatedAt'>): PadSketch;
    /**
     * Add a tool to a pad
     */
    addTool(padId: string, tool: Omit<PadTool, 'id' | 'createdAt' | 'usageCount' | 'lastUsed' | 'effectiveness'>): PadTool;
    /**
     * Use a tool (increment usage, update effectiveness)
     */
    useTool(padId: string, toolId: string, success: boolean): void;
    /**
     * Update flux coefficient ν
     */
    updateFlux(padId: string, newNu: number): void;
    /**
     * Gradually transition to target ν
     */
    setTargetFlux(padId: string, targetNu: number, rate?: number): void;
    /**
     * Step flux toward target (call periodically)
     */
    stepFlux(padId: string): void;
    /**
     * Add experience points
     */
    addXP(padId: string, amount: number, reason: string): void;
    /**
     * Promote to next tier
     */
    promoteTier(padId: string): boolean;
    /**
     * Demote to previous tier
     */
    demoteTier(padId: string, demotionReason: string): boolean;
    /**
     * Record task completion
     */
    recordTaskCompletion(padId: string, success: boolean): void;
    /**
     * Record collaboration
     */
    recordCollaboration(padId: string): void;
    /**
     * Add a milestone
     */
    private addMilestone;
    /**
     * Add audit entry
     */
    addAuditEntry(padId: string, entry: Omit<AuditEntry, 'id' | 'timestamp'>): void;
    /**
     * Perform full audit on a pad
     */
    auditPad(padId: string, auditorId: string): AuditEntry;
    /**
     * Get pad statistics
     */
    getPadStats(padId: string): {
        tier: GovernanceTier;
        tierName: string;
        xp: number;
        xpToNext: number;
        progress: number;
        tasksCompleted: number;
        successRate: number;
        toolsCreated: number;
        milestonesAchieved: number;
        dimensionalState: DimensionalState;
        nu: number;
    } | undefined;
    /**
     * Generate pad ID
     */
    private generatePadId;
}
//# sourceMappingURL=polly-pad.d.ts.map