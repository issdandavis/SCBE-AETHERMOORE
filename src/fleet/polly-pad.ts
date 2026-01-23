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
import { GovernanceTier } from './types';

/**
 * Dimensional state based on flux coefficient ν
 */
export type DimensionalState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';

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
  // === Identity ===
  /** Unique pad ID */
  id: string;
  /** Agent ID this pad belongs to */
  agentId: string;
  /** Pad display name */
  name: string;
  /** Agent's spectral identity */
  spectralIdentity?: SpectralIdentity;
  
  // === Dimensional Flux State ===
  /** Flux coefficient ν ∈ [0, 1] */
  nu: number;
  /** Current dimensional state */
  dimensionalState: DimensionalState;
  /** Rate of flux change */
  fluxRate: number;
  /** Target ν (for gradual transitions) */
  targetNu?: number;
  
  // === Workspace Content ===
  /** Notes the agent has written */
  notes: PadNote[];
  /** Sketches/diagrams */
  sketches: PadSketch[];
  /** Saved tools and templates */
  tools: PadTool[];
  
  // === Swarm Coordination ===
  /** Which swarm this pad belongs to */
  swarmId?: string;
  /** Coherence with swarm (0-1) */
  coherenceScore: number;
  /** Last swarm sync timestamp */
  lastSwarmSync?: number;
  
  // === Governance (Sacred Tongue Tier) ===
  /** Current governance tier (like grade level) */
  tier: GovernanceTier;
  /** 6D trust vector */
  trustVector: number[];
  /** Experience points toward next tier */
  experiencePoints: number;
  /** Points needed for next tier */
  nextTierThreshold: number;
  
  // === Growth & Stats ===
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
  
  // === Audit Trail ===
  /** Audit log */
  auditLog: AuditEntry[];
  /** Current audit status */
  auditStatus: AuditStatus;
  /** Last audit timestamp */
  lastAuditAt?: number;
  /** Who last audited */
  lastAuditBy?: string;
  
  // === Timestamps ===
  createdAt: number;
  updatedAt: number;
}

/**
 * Tier progression thresholds (like grade levels)
 */
export const TIER_THRESHOLDS: Record<GovernanceTier, { xp: number; name: string; description: string }> = {
  KO: { xp: 0,    name: 'Kindergarten', description: 'Basic tasks, high supervision' },
  AV: { xp: 100,  name: 'Elementary',   description: 'I/O tasks, moderate supervision' },
  RU: { xp: 300,  name: 'Middle School', description: 'Policy-aware, some autonomy' },
  CA: { xp: 600,  name: 'High School',  description: 'Logic tasks, trusted' },
  UM: { xp: 1000, name: 'University',   description: 'Security tasks, high trust' },
  DR: { xp: 2000, name: 'Doctorate',    description: 'Architectural decisions, full autonomy' }
};

/**
 * Get dimensional state from flux coefficient
 */
export function getDimensionalState(nu: number): DimensionalState {
  if (nu >= 0.9) return 'POLLY';
  if (nu >= 0.5) return 'QUASI';
  if (nu > 0.1) return 'DEMI';
  return 'COLLAPSED';
}

/**
 * Get next tier in progression
 */
export function getNextTier(current: GovernanceTier): GovernanceTier | null {
  const order: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
  const index = order.indexOf(current);
  if (index < order.length - 1) {
    return order[index + 1];
  }
  return null;
}

/**
 * Calculate XP needed for next tier
 */
export function getXPForNextTier(current: GovernanceTier): number {
  const next = getNextTier(current);
  if (!next) return Infinity;
  return TIER_THRESHOLDS[next].xp;
}

/**
 * Polly Pad Manager
 * 
 * Manages all agent pads in the system.
 */
export class PollyPadManager {
  private pads: Map<string, PollyPad> = new Map();
  private padsByAgent: Map<string, string> = new Map(); // agentId -> padId
  
  /**
   * Create a new Polly Pad for an agent
   */
  public createPad(
    agentId: string,
    name: string,
    initialTier: GovernanceTier = 'KO',
    trustVector: number[] = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
  ): PollyPad {
    const id = this.generatePadId(agentId);
    
    const pad: PollyPad = {
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
      updatedAt: Date.now()
    };
    
    this.pads.set(id, pad);
    this.padsByAgent.set(agentId, id);
    
    return pad;
  }
  
  /**
   * Get pad by ID
   */
  public getPad(id: string): PollyPad | undefined {
    return this.pads.get(id);
  }
  
  /**
   * Get pad by agent ID
   */
  public getPadByAgent(agentId: string): PollyPad | undefined {
    const padId = this.padsByAgent.get(agentId);
    return padId ? this.pads.get(padId) : undefined;
  }
  
  /**
   * Get all pads
   */
  public getAllPads(): PollyPad[] {
    return Array.from(this.pads.values());
  }
  
  /**
   * Get pads by dimensional state
   */
  public getPadsByState(state: DimensionalState): PollyPad[] {
    return this.getAllPads().filter(p => p.dimensionalState === state);
  }
  
  /**
   * Get pads by tier
   */
  public getPadsByTier(tier: GovernanceTier): PollyPad[] {
    return this.getAllPads().filter(p => p.tier === tier);
  }
  
  // === Workspace Operations ===
  
  /**
   * Add a note to a pad
   */
  public addNote(padId: string, note: Omit<PadNote, 'id' | 'createdAt' | 'updatedAt'>): PadNote {
    const pad = this.pads.get(padId);
    if (!pad) throw new Error(`Pad ${padId} not found`);
    
    if (pad.dimensionalState === 'COLLAPSED') {
      throw new Error('Cannot add notes to collapsed pad');
    }
    
    const newNote: PadNote = {
      ...note,
      id: `note-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    
    pad.notes.push(newNote);
    pad.updatedAt = Date.now();
    this.addXP(padId, 5, 'note_created');
    
    return newNote;
  }
  
  /**
   * Add a sketch to a pad
   */
  public addSketch(padId: string, sketch: Omit<PadSketch, 'id' | 'createdAt' | 'updatedAt'>): PadSketch {
    const pad = this.pads.get(padId);
    if (!pad) throw new Error(`Pad ${padId} not found`);
    
    if (pad.dimensionalState === 'COLLAPSED' || pad.dimensionalState === 'DEMI') {
      throw new Error('Cannot add sketches in current dimensional state');
    }
    
    const newSketch: PadSketch = {
      ...sketch,
      id: `sketch-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    
    pad.sketches.push(newSketch);
    pad.updatedAt = Date.now();
    this.addXP(padId, 10, 'sketch_created');
    
    return newSketch;
  }
  
  /**
   * Add a tool to a pad
   */
  public addTool(padId: string, tool: Omit<PadTool, 'id' | 'createdAt' | 'usageCount' | 'lastUsed' | 'effectiveness'>): PadTool {
    const pad = this.pads.get(padId);
    if (!pad) throw new Error(`Pad ${padId} not found`);
    
    if (pad.dimensionalState !== 'POLLY') {
      throw new Error('Can only create tools in POLLY state');
    }
    
    const newTool: PadTool = {
      ...tool,
      id: `tool-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      createdAt: Date.now(),
      usageCount: 0,
      effectiveness: 0.5
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
  public useTool(padId: string, toolId: string, success: boolean): void {
    const pad = this.pads.get(padId);
    if (!pad) throw new Error(`Pad ${padId} not found`);
    
    const tool = pad.tools.find(t => t.id === toolId);
    if (!tool) throw new Error(`Tool ${toolId} not found`);
    
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
  public updateFlux(padId: string, newNu: number): void {
    const pad = this.pads.get(padId);
    if (!pad) throw new Error(`Pad ${padId} not found`);
    
    const oldState = pad.dimensionalState;
    pad.nu = Math.max(0, Math.min(1, newNu));
    pad.dimensionalState = getDimensionalState(pad.nu);
    pad.updatedAt = Date.now();
    
    // Log state transition
    if (oldState !== pad.dimensionalState) {
      this.addAuditEntry(padId, {
        auditorId: 'system',
        target: 'behavior',
        result: 'pass',
        findings: `Dimensional state changed: ${oldState} → ${pad.dimensionalState}`,
        actions: [`nu updated to ${pad.nu.toFixed(3)}`]
      });
    }
  }
  
  /**
   * Gradually transition to target ν
   */
  public setTargetFlux(padId: string, targetNu: number, rate: number = 0.01): void {
    const pad = this.pads.get(padId);
    if (!pad) throw new Error(`Pad ${padId} not found`);
    
    pad.targetNu = Math.max(0, Math.min(1, targetNu));
    pad.fluxRate = rate;
  }
  
  /**
   * Step flux toward target (call periodically)
   */
  public stepFlux(padId: string): void {
    const pad = this.pads.get(padId);
    if (!pad || pad.targetNu === undefined) return;
    
    const diff = pad.targetNu - pad.nu;
    if (Math.abs(diff) < 0.001) {
      pad.nu = pad.targetNu;
      pad.targetNu = undefined;
      pad.fluxRate = 0;
    } else {
      pad.nu += Math.sign(diff) * pad.fluxRate;
      pad.nu = Math.max(0, Math.min(1, pad.nu));
    }
    
    pad.dimensionalState = getDimensionalState(pad.nu);
    pad.updatedAt = Date.now();
  }
  
  // === Growth & Progression ===
  
  /**
   * Add experience points
   */
  public addXP(padId: string, amount: number, reason: string): void {
    const pad = this.pads.get(padId);
    if (!pad) return;
    
    pad.experiencePoints += amount;
    
    // Check for tier promotion
    const nextTier = getNextTier(pad.tier);
    if (nextTier && pad.experiencePoints >= TIER_THRESHOLDS[nextTier].xp) {
      this.promoteTier(padId);
    }
    
    pad.updatedAt = Date.now();
  }
  
  /**
   * Promote to next tier
   */
  public promoteTier(padId: string): boolean {
    const pad = this.pads.get(padId);
    if (!pad) return false;
    
    const nextTier = getNextTier(pad.tier);
    if (!nextTier) return false;
    
    const oldTier = pad.tier;
    pad.tier = nextTier;
    pad.nextTierThreshold = getXPForNextTier(nextTier);
    
    // Add promotion milestone
    this.addMilestone(
      padId,
      `Promoted to ${TIER_THRESHOLDS[nextTier].name}`,
      `Advanced from ${oldTier} to ${nextTier}`,
      'promotion'
    );
    
    // Audit the promotion
    this.addAuditEntry(padId, {
      auditorId: 'system',
      target: 'behavior',
      result: 'pass',
      findings: `Tier promotion: ${oldTier} → ${nextTier}`,
      actions: ['Tier updated', 'Milestone added']
    });
    
    pad.updatedAt = Date.now();
    return true;
  }
  
  /**
   * Demote to previous tier
   */
  public demoteTier(padId: string, reason: string): boolean {
    const pad = this.pads.get(padId);
    if (!pad) return false;
    
    const order: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const index = order.indexOf(pad.tier);
    if (index <= 0) return false;
    
    const oldTier = pad.tier;
    pad.tier = order[index - 1];
    pad.nextTierThreshold = getXPForNextTier(pad.tier);
    
    // Audit the demotion
    this.addAuditEntry(padId, {
      auditorId: 'system',
      target: 'behavior',
      result: 'warning',
      findings: `Tier demotion: ${oldTier} → ${pad.tier}. Reason: ${reason}`,
      actions: ['Tier reduced']
    });
    
    pad.updatedAt = Date.now();
    return true;
  }
  
  /**
   * Record task completion
   */
  public recordTaskCompletion(padId: string, success: boolean): void {
    const pad = this.pads.get(padId);
    if (!pad) return;
    
    pad.tasksCompleted++;
    
    // Update success rate
    const alpha = 0.1;
    pad.successRate = alpha * (success ? 1 : 0) + (1 - alpha) * pad.successRate;
    
    // Add XP
    this.addXP(padId, success ? 15 : 2, success ? 'task_success' : 'task_attempt');
    
    // Check milestones
    if (pad.tasksCompleted === 10) {
      this.addMilestone(padId, 'First Steps', 'Completed 10 tasks', 'tasks');
    } else if (pad.tasksCompleted === 50) {
      this.addMilestone(padId, 'Journeyman', 'Completed 50 tasks', 'tasks');
    } else if (pad.tasksCompleted === 100) {
      this.addMilestone(padId, 'Veteran', 'Completed 100 tasks', 'tasks');
    }
    
    pad.updatedAt = Date.now();
  }
  
  /**
   * Record collaboration
   */
  public recordCollaboration(padId: string): void {
    const pad = this.pads.get(padId);
    if (!pad) return;
    
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
  private addMilestone(
    padId: string,
    name: string,
    description: string,
    trigger: GrowthMilestone['trigger']
  ): void {
    const pad = this.pads.get(padId);
    if (!pad) return;
    
    pad.milestones.push({
      id: `milestone-${Date.now().toString(36)}`,
      name,
      description,
      achievedAt: Date.now(),
      tierAtTime: pad.tier,
      trigger
    });
  }
  
  // === Audit ===
  
  /**
   * Add audit entry
   */
  public addAuditEntry(padId: string, entry: Omit<AuditEntry, 'id' | 'timestamp'>): void {
    const pad = this.pads.get(padId);
    if (!pad) return;
    
    pad.auditLog.push({
      ...entry,
      id: `audit-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      timestamp: Date.now()
    });
    
    pad.lastAuditAt = Date.now();
    pad.lastAuditBy = entry.auditorId;
    
    // Update audit status based on result
    if (entry.result === 'fail') {
      pad.auditStatus = 'restricted';
    } else if (entry.result === 'warning' && pad.auditStatus === 'clean') {
      pad.auditStatus = 'flagged';
    }
    
    pad.updatedAt = Date.now();
  }
  
  /**
   * Perform full audit on a pad
   */
  public auditPad(padId: string, auditorId: string): AuditEntry {
    const pad = this.pads.get(padId);
    if (!pad) throw new Error(`Pad ${padId} not found`);
    
    const findings: string[] = [];
    let result: AuditEntry['result'] = 'pass';
    
    // Check success rate
    if (pad.successRate < 0.5) {
      findings.push(`Low success rate: ${(pad.successRate * 100).toFixed(1)}%`);
      result = 'warning';
    }
    
    // Check tool effectiveness
    const lowEffectTools = pad.tools.filter(t => t.effectiveness < 0.3 && t.usageCount > 5);
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
    
    const entry: Omit<AuditEntry, 'id' | 'timestamp'> = {
      auditorId,
      target: 'full',
      result,
      findings: findings.join('; '),
      actions: result === 'pass' ? ['Audit complete'] : ['Review recommended']
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
  public getPadStats(padId: string): {
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
  } | undefined {
    const pad = this.pads.get(padId);
    if (!pad) return undefined;
    
    const xpToNext = pad.nextTierThreshold - pad.experiencePoints;
    const prevThreshold = TIER_THRESHOLDS[pad.tier].xp;
    const progress = (pad.experiencePoints - prevThreshold) / (pad.nextTierThreshold - prevThreshold);
    
    return {
      tier: pad.tier,
      tierName: TIER_THRESHOLDS[pad.tier].name,
      xp: pad.experiencePoints,
      xpToNext: Math.max(0, xpToNext),
      progress: Math.min(1, Math.max(0, progress)),
      tasksCompleted: pad.tasksCompleted,
      successRate: pad.successRate,
      toolsCreated: pad.toolsCreated,
      milestonesAchieved: pad.milestones.length,
      dimensionalState: pad.dimensionalState,
      nu: pad.nu
    };
  }
  
  /**
   * Generate pad ID
   */
  private generatePadId(agentId: string): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 6);
    return `pad-${agentId.substring(0, 8)}-${timestamp}-${random}`;
  }
}
