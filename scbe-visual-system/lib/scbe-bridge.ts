/**
 * SCBE-AETHERMOORE Security Bridge for Visual Computer
 *
 * Integrates SCBE security framework with InkOS visual computer,
 * enabling high-grade security, AI building, and fleet management.
 *
 * @version 1.0.0
 * @author Issac Davis
 * @license MIT
 */

// ========== SCBE TYPES ==========

/** Six Sacred Tongues as governance tiers */
export type GovernanceTier = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Dimensional flux states for Polly Pads */
export type DimensionalState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';

/** Polly Pad note */
export interface PadNote {
  id: string;
  title: string;
  content: string;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
}

/** Polly Pad sketch */
export interface PadSketch {
  id: string;
  name: string;
  data: string;  // SVG or base64 image
  sketchType: 'freeform' | 'diagram' | 'flowchart' | 'wireframe';
  createdAt: Date;
}

/** Polly Pad tool */
export interface PadTool {
  id: string;
  name: string;
  description: string;
  toolType: 'script' | 'template' | 'shortcut' | 'automation';
  content: string;
  enabled: boolean;
}

/** Polly Pad - personal workspace for AI agents */
export interface PollyPad {
  id: string;
  agentId: string;
  name: string;
  nu: number;  // 0.0-1.0 dimensional participation
  dimensionalState: DimensionalState;
  notes: PadNote[];
  sketches: PadSketch[];
  tools: PadTool[];
  tier: GovernanceTier;
  xp: number;
  level: number;
  coherenceScore: number;
  auditStatus: 'clean' | 'flagged' | 'restricted';
  createdAt: Date;
  updatedAt: Date;
}

/** Fleet agent */
export interface FleetAgent {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'busy' | 'error';
  capabilities: string[];
  tier: GovernanceTier;
  pad?: PollyPad;
  lastSeen: Date;
}

/** Security verification result */
export interface SecurityResult {
  valid: boolean;
  tier: GovernanceTier;
  requiredSignatures: GovernanceTier[];
  presentSignatures: GovernanceTier[];
  timestamp: Date;
}

// ========== DIMENSIONAL THRESHOLDS ==========

export const DIMENSIONAL_THRESHOLDS = {
  POLLY: 0.8,     // Full participation (ν ≥ 0.8)
  QUASI: 0.5,     // Partial participation (0.5 ≤ ν < 0.8)
  DEMI: 0.1,      // Minimal participation (0.1 ≤ ν < 0.5)
  COLLAPSED: 0    // Offline/archived (ν < 0.1)
};

/** Get dimensional state from nu value */
export function getDimensionalState(nu: number): DimensionalState {
  if (nu >= DIMENSIONAL_THRESHOLDS.POLLY) return 'POLLY';
  if (nu >= DIMENSIONAL_THRESHOLDS.QUASI) return 'QUASI';
  if (nu >= DIMENSIONAL_THRESHOLDS.DEMI) return 'DEMI';
  return 'COLLAPSED';
}

// ========== TIER PROGRESSION ==========

export const TIER_THRESHOLDS: Record<GovernanceTier, { minXP: number; name: string }> = {
  'KO': { minXP: 0, name: 'Kindergarten' },
  'AV': { minXP: 100, name: 'Elementary' },
  'RU': { minXP: 500, name: 'Middle School' },
  'CA': { minXP: 2000, name: 'High School' },
  'UM': { minXP: 10000, name: 'University' },
  'DR': { minXP: 50000, name: 'Doctorate' }
};

/** Get tier from XP */
export function getTierFromXP(xp: number): GovernanceTier {
  if (xp >= TIER_THRESHOLDS.DR.minXP) return 'DR';
  if (xp >= TIER_THRESHOLDS.UM.minXP) return 'UM';
  if (xp >= TIER_THRESHOLDS.CA.minXP) return 'CA';
  if (xp >= TIER_THRESHOLDS.RU.minXP) return 'RU';
  if (xp >= TIER_THRESHOLDS.AV.minXP) return 'AV';
  return 'KO';
}

// ========== SCBE BRIDGE CLASS ==========

/**
 * Bridge between Visual Computer and SCBE security system
 */
export class SCBEBridge {
  private agents: Map<string, FleetAgent> = new Map();
  private pads: Map<string, PollyPad> = new Map();
  private swarmId: string;

  constructor(swarmId: string = 'visual-computer-swarm') {
    this.swarmId = swarmId;
    this.initializeLocalAgent();
  }

  /** Initialize the local visual computer as an agent */
  private initializeLocalAgent(): void {
    const localAgent: FleetAgent = {
      id: 'visual-computer-local',
      name: 'InkOS Visual Computer',
      status: 'online',
      capabilities: ['ide', 'drawing', 'notes', 'automation'],
      tier: 'AV',
      lastSeen: new Date()
    };

    const localPad: PollyPad = {
      id: `pad-${localAgent.id}`,
      agentId: localAgent.id,
      name: 'My Polly Pad',
      nu: 0.9,
      dimensionalState: 'POLLY',
      notes: [],
      sketches: [],
      tools: [],
      tier: 'AV',
      xp: 150,
      level: 2,
      coherenceScore: 0.95,
      auditStatus: 'clean',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    localAgent.pad = localPad;
    this.agents.set(localAgent.id, localAgent);
    this.pads.set(localPad.id, localPad);
  }

  // ========== AGENT METHODS ==========

  /** Get all agents */
  getAllAgents(): FleetAgent[] {
    return Array.from(this.agents.values());
  }

  /** Get agent by ID */
  getAgent(id: string): FleetAgent | undefined {
    return this.agents.get(id);
  }

  /** Register a new agent */
  registerAgent(name: string, capabilities: string[]): FleetAgent {
    const id = `agent-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const agent: FleetAgent = {
      id,
      name,
      status: 'online',
      capabilities,
      tier: 'KO',
      lastSeen: new Date()
    };

    // Create Polly Pad for the agent
    const pad = this.createPad(id, name);
    agent.pad = pad;

    this.agents.set(id, agent);
    return agent;
  }

  // ========== PAD METHODS ==========

  /** Get all pads */
  getAllPads(): PollyPad[] {
    return Array.from(this.pads.values());
  }

  /** Get pad by agent ID */
  getPadByAgent(agentId: string): PollyPad | undefined {
    return Array.from(this.pads.values()).find(p => p.agentId === agentId);
  }

  /** Create a new Polly Pad */
  createPad(agentId: string, name: string): PollyPad {
    const pad: PollyPad = {
      id: `pad-${agentId}`,
      agentId,
      name: `${name}'s Pad`,
      nu: 0.5,
      dimensionalState: 'QUASI',
      notes: [],
      sketches: [],
      tools: [],
      tier: 'KO',
      xp: 0,
      level: 1,
      coherenceScore: 0.5,
      auditStatus: 'clean',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.pads.set(pad.id, pad);
    return pad;
  }

  /** Add note to pad */
  addNote(padId: string, title: string, content: string, tags: string[] = []): PadNote | undefined {
    const pad = this.pads.get(padId);
    if (!pad) return undefined;

    const note: PadNote = {
      id: `note-${Date.now()}`,
      title,
      content,
      tags,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    pad.notes.push(note);
    pad.updatedAt = new Date();
    this.addXP(padId, 10);
    return note;
  }

  /** Add sketch to pad */
  addSketch(padId: string, name: string, data: string, sketchType: PadSketch['sketchType'] = 'freeform'): PadSketch | undefined {
    const pad = this.pads.get(padId);
    if (!pad) return undefined;

    const sketch: PadSketch = {
      id: `sketch-${Date.now()}`,
      name,
      data,
      sketchType,
      createdAt: new Date()
    };

    pad.sketches.push(sketch);
    pad.updatedAt = new Date();
    this.addXP(padId, 15);
    return sketch;
  }

  /** Add tool to pad */
  addTool(padId: string, name: string, description: string, toolType: PadTool['toolType'], content: string): PadTool | undefined {
    const pad = this.pads.get(padId);
    if (!pad) return undefined;

    const tool: PadTool = {
      id: `tool-${Date.now()}`,
      name,
      description,
      toolType,
      content,
      enabled: true
    };

    pad.tools.push(tool);
    pad.updatedAt = new Date();
    this.addXP(padId, 25);
    return tool;
  }

  /** Add XP to pad and check tier progression */
  addXP(padId: string, amount: number): void {
    const pad = this.pads.get(padId);
    if (!pad) return;

    pad.xp += amount;
    const newTier = getTierFromXP(pad.xp);
    if (newTier !== pad.tier) {
      pad.tier = newTier;
      pad.level = Object.keys(TIER_THRESHOLDS).indexOf(newTier) + 1;
    }
    pad.updatedAt = new Date();
  }

  /** Update dimensional flux */
  updateFlux(padId: string, targetNu: number): void {
    const pad = this.pads.get(padId);
    if (!pad) return;

    // Gradual flux adjustment
    const delta = (targetNu - pad.nu) * 0.1;
    pad.nu = Math.max(0, Math.min(1, pad.nu + delta));
    pad.dimensionalState = getDimensionalState(pad.nu);
    pad.updatedAt = new Date();
  }

  // ========== SECURITY METHODS ==========

  /** Verify action with SCBE security */
  verifyAction(action: string, requiredTier: GovernanceTier): SecurityResult {
    const tierOrder: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const requiredIndex = tierOrder.indexOf(requiredTier);

    // Get signatures from all agents at or above required tier
    const presentSignatures = this.getAllAgents()
      .filter(a => tierOrder.indexOf(a.tier) >= requiredIndex)
      .map(a => a.tier);

    return {
      valid: presentSignatures.length > 0,
      tier: requiredTier,
      requiredSignatures: [requiredTier],
      presentSignatures: Array.from(new Set(presentSignatures)) as GovernanceTier[],
      timestamp: new Date()
    };
  }

  /** Classify action by security tier */
  classifyAction(action: string): GovernanceTier {
    const criticalActions = ['deploy', 'delete', 'rotate_key', 'grant_access'];
    const highActions = ['modify_state', 'execute_command', 'send_signal'];
    const mediumActions = ['query_state', 'log_event', 'update_metadata'];
    const lowActions = ['read', 'view', 'list'];

    if (criticalActions.some(a => action.includes(a))) return 'DR';
    if (highActions.some(a => action.includes(a))) return 'UM';
    if (mediumActions.some(a => action.includes(a))) return 'CA';
    if (lowActions.some(a => action.includes(a))) return 'AV';
    return 'KO';
  }

  // ========== SWARM METHODS ==========

  /** Get swarm status */
  getSwarmStatus(): {
    swarmId: string;
    totalAgents: number;
    onlineAgents: number;
    avgCoherence: number;
    avgNu: number;
  } {
    const agents = this.getAllAgents();
    const pads = this.getAllPads();

    return {
      swarmId: this.swarmId,
      totalAgents: agents.length,
      onlineAgents: agents.filter(a => a.status === 'online').length,
      avgCoherence: pads.length > 0
        ? pads.reduce((sum, p) => sum + p.coherenceScore, 0) / pads.length
        : 0,
      avgNu: pads.length > 0
        ? pads.reduce((sum, p) => sum + p.nu, 0) / pads.length
        : 0
    };
  }
}

// ========== SINGLETON INSTANCE ==========

let bridgeInstance: SCBEBridge | null = null;

/** Get or create the SCBE bridge instance */
export function getSCBEBridge(): SCBEBridge {
  if (!bridgeInstance) {
    bridgeInstance = new SCBEBridge();
  }
  return bridgeInstance;
}

// ========== REACT HOOKS ==========

import { useState, useEffect, useCallback } from 'react';

/** Hook to use SCBE bridge */
export function useSCBEBridge() {
  const [bridge] = useState(() => getSCBEBridge());
  const [agents, setAgents] = useState<FleetAgent[]>([]);
  const [pads, setPads] = useState<PollyPad[]>([]);

  const refresh = useCallback(() => {
    setAgents(bridge.getAllAgents());
    setPads(bridge.getAllPads());
  }, [bridge]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  return {
    bridge,
    agents,
    pads,
    refresh
  };
}

/** Hook to use a specific Polly Pad */
export function usePollyPad(agentId: string) {
  const bridge = getSCBEBridge();
  const [pad, setPad] = useState<PollyPad | undefined>();

  const refresh = useCallback(() => {
    setPad(bridge.getPadByAgent(agentId));
  }, [bridge, agentId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 2000);
    return () => clearInterval(interval);
  }, [refresh]);

  const addNote = useCallback((title: string, content: string, tags?: string[]) => {
    if (pad) {
      bridge.addNote(pad.id, title, content, tags);
      refresh();
    }
  }, [bridge, pad, refresh]);

  const addSketch = useCallback((name: string, data: string, type?: PadSketch['sketchType']) => {
    if (pad) {
      bridge.addSketch(pad.id, name, data, type);
      refresh();
    }
  }, [bridge, pad, refresh]);

  const addTool = useCallback((name: string, desc: string, type: PadTool['toolType'], content: string) => {
    if (pad) {
      bridge.addTool(pad.id, name, desc, type, content);
      refresh();
    }
  }, [bridge, pad, refresh]);

  return {
    pad,
    addNote,
    addSketch,
    addTool,
    refresh
  };
}
