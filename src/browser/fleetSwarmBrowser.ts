/**
 * @file fleetSwarmBrowser.ts
 * @module browser/fleetSwarmBrowser
 * @layer Layer 13, 14
 * @component Framework 4: Fleet Swarm Browser (FSB)
 *
 * Multi-agent browsing using roundtable consensus for critical operations.
 * Each sub-agent in the swarm specializes (navigator, extractor, validator,
 * sentinel) and votes on action outcomes via Sacred Tongue signatures.
 *
 * Consensus requires 4+ tongue signatures for critical actions (Byzantine
 * fault tolerant with f=1, n≥4, quorum≥3).
 *
 * A1: Composition — swarm results composed from validated sub-results
 * A4: Symmetry — each agent's vote weighted equally
 */

import { createHash, randomBytes } from 'crypto';

// ============================================================================
// Types
// ============================================================================

/** Agent specialization */
export type AgentRole = 'navigator' | 'extractor' | 'validator' | 'sentinel';

/** Tongue code for signatures */
export type TongueCode = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Individual swarm agent */
export interface SwarmAgent {
  /** Unique agent ID */
  id: string;
  /** Agent specialization */
  role: AgentRole;
  /** Current trust score [0,1] */
  trustScore: number;
  /** Assigned tongue */
  tongue: TongueCode;
  /** Agent status */
  status: 'active' | 'quarantined' | 'suspended';
  /** Tasks completed */
  tasksCompleted: number;
}

/** Sub-task for a swarm agent */
export interface SwarmSubTask {
  /** Task ID */
  id: string;
  /** Description */
  description: string;
  /** Required role */
  requiredRole: AgentRole;
  /** URL or target */
  target: string;
  /** Action to perform */
  action: string;
  /** Dependencies (task IDs that must complete first) */
  dependencies: string[];
}

/** Swarm task (top-level) */
export interface SwarmTask {
  /** Task objective */
  objective: string;
  /** Required agent count */
  requiredAgents: number;
  /** Consensus threshold (default: 4 for Sacred Tongues) */
  consensusThreshold: number;
  /** Sub-tasks to distribute */
  subTasks: SwarmSubTask[];
}

/** Sub-task execution result */
export interface SubTaskResult {
  /** Task ID */
  taskId: string;
  /** Agent that executed */
  agentId: string;
  /** Execution success */
  success: boolean;
  /** Result data */
  data?: unknown;
  /** Error message */
  error?: string;
  /** Tongue signature */
  tongueSignature: TongueSignature;
  /** Validation scores */
  validation: ValidationScores;
}

/** Tongue-signed validation */
export interface TongueSignature {
  /** Agent ID */
  agentId: string;
  /** Tongues that passed */
  passedTongues: TongueCode[];
  /** Signature hash */
  signatureHash: string;
  /** Timestamp */
  timestamp: number;
}

/** Validation scores per dimension */
export interface ValidationScores {
  /** KO: Control flow valid */
  controlValid: boolean;
  /** AV: I/O safe */
  ioSafe: boolean;
  /** RU: Policy compliant */
  policyCompliant: boolean;
  /** CA: Logically sound */
  logicSound: boolean;
  /** UM: Cryptographically secure */
  cryptoSecure: boolean;
  /** DR: Type safe */
  typeSafe: boolean;
}

/** Consensus result */
export interface ConsensusResult {
  /** Consensus reached */
  approved: boolean;
  /** Number of approving votes */
  approveCount: number;
  /** Number of rejecting votes */
  rejectCount: number;
  /** Total participants */
  totalParticipants: number;
  /** Quorum met */
  quorumMet: boolean;
  /** Tongues that achieved consensus */
  consensusTongues: TongueCode[];
  /** Combined trust score */
  trustScore: number;
}

/** Final swarm result */
export interface SwarmResult {
  /** Overall status */
  status: 'success' | 'consensus_failed' | 'partial' | 'failed';
  /** Consensus details */
  consensus: ConsensusResult;
  /** Per-subtask results */
  subTaskResults: SubTaskResult[];
  /** Merged data from all sub-tasks */
  mergedData: unknown[];
  /** Quarantined agents (if any) */
  quarantinedAgents: string[];
}

/** FSB configuration */
export interface FSBConfig {
  /** Default consensus threshold */
  defaultConsensusThreshold: number;
  /** Minimum trust to participate */
  minTrustScore: number;
  /** Trust delta on successful task */
  trustDeltaSuccess: number;
  /** Trust delta on failed task */
  trustDeltaFailure: number;
  /** Quarantine trust threshold */
  quarantineTrustThreshold: number;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_CONFIG: FSBConfig = {
  defaultConsensusThreshold: 4, // 4+ tongues for Sacred Tongue alignment
  minTrustScore: 0.3,
  trustDeltaSuccess: 0.02,
  trustDeltaFailure: -0.1,
  quarantineTrustThreshold: 0.2,
};

/** Tongue assignments by agent role */
const ROLE_TONGUE_MAP: Record<AgentRole, TongueCode> = {
  navigator: 'KO',
  extractor: 'CA',
  validator: 'RU',
  sentinel: 'UM',
};

// ============================================================================
// Fleet Swarm Browser
// ============================================================================

/**
 * Fleet Swarm Browser (FSB).
 *
 * Orchestrates multi-agent browsing with Byzantine fault-tolerant
 * consensus. Each agent specializes and votes on results via
 * Sacred Tongue signatures.
 */
export class FleetSwarmBrowser {
  private readonly config: FSBConfig;
  private readonly agents: Map<string, SwarmAgent> = new Map();
  private nextAgentIndex = 0;

  constructor(config?: Partial<FSBConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Spawn a swarm of agents with role-based specialization.
   */
  spawnSwarm(count: number, roles?: AgentRole[]): SwarmAgent[] {
    const defaultRoles: AgentRole[] = ['navigator', 'extractor', 'validator', 'sentinel'];
    const spawned: SwarmAgent[] = [];

    for (let i = 0; i < count; i++) {
      const role = roles ? roles[i % roles.length]! : defaultRoles[i % defaultRoles.length]!;
      const agent: SwarmAgent = {
        id: `swarm-${this.nextAgentIndex++}-${randomBytes(4).toString('hex')}`,
        role,
        trustScore: 0.7,
        tongue: ROLE_TONGUE_MAP[role],
        status: 'active',
        tasksCompleted: 0,
      };
      this.agents.set(agent.id, agent);
      spawned.push(agent);
    }

    return spawned;
  }

  /**
   * Execute a swarm browsing task with consensus.
   */
  executeSwarmTask(task: SwarmTask): SwarmResult {
    // Get available agents
    const available = Array.from(this.agents.values()).filter(
      (a) => a.status === 'active' && a.trustScore >= this.config.minTrustScore
    );

    if (available.length < task.requiredAgents) {
      return {
        status: 'failed',
        consensus: this.emptyConsensus(),
        subTaskResults: [],
        mergedData: [],
        quarantinedAgents: [],
      };
    }

    // Assign sub-tasks to agents by role matching
    const assignments = this.assignTasks(task.subTasks, available);

    // Execute sub-tasks
    const results: SubTaskResult[] = [];
    for (const { agent, subTask } of assignments) {
      const result = this.executeSubTask(agent, subTask);
      results.push(result);

      // Update trust based on result
      this.updateTrust(agent.id, result.success);
    }

    // Roundtable consensus
    const consensus = this.roundtableConsensus(
      results,
      task.consensusThreshold || this.config.defaultConsensusThreshold
    );

    // Quarantine dissenting agents if consensus failed
    const quarantined: string[] = [];
    if (!consensus.approved) {
      for (const result of results) {
        const agent = this.agents.get(result.agentId);
        if (agent && agent.trustScore < this.config.quarantineTrustThreshold) {
          agent.status = 'quarantined';
          quarantined.push(agent.id);
        }
      }
    }

    return {
      status: consensus.approved ? 'success' : 'consensus_failed',
      consensus,
      subTaskResults: results,
      mergedData: results.filter((r) => r.success).map((r) => r.data),
      quarantinedAgents: quarantined,
    };
  }

  /**
   * Get all agents and their current status.
   */
  getAgents(): SwarmAgent[] {
    return Array.from(this.agents.values());
  }

  /**
   * Get a specific agent by ID.
   */
  getAgent(agentId: string): SwarmAgent | null {
    return this.agents.get(agentId) ?? null;
  }

  /**
   * Reactivate a quarantined agent (requires trust restoration).
   */
  reactivateAgent(agentId: string, newTrust: number): boolean {
    const agent = this.agents.get(agentId);
    if (!agent || agent.status !== 'quarantined') return false;
    if (newTrust < this.config.minTrustScore) return false;

    agent.status = 'active';
    agent.trustScore = newTrust;
    return true;
  }

  // --------------------------------------------------------------------------
  // Internal
  // --------------------------------------------------------------------------

  /** Assign sub-tasks to agents by role matching */
  private assignTasks(
    subTasks: SwarmSubTask[],
    agents: SwarmAgent[]
  ): Array<{ agent: SwarmAgent; subTask: SwarmSubTask }> {
    const assignments: Array<{ agent: SwarmAgent; subTask: SwarmSubTask }> = [];
    const agentsByRole = new Map<AgentRole, SwarmAgent[]>();

    for (const agent of agents) {
      const list = agentsByRole.get(agent.role) ?? [];
      list.push(agent);
      agentsByRole.set(agent.role, list);
    }

    for (const subTask of subTasks) {
      const candidates = agentsByRole.get(subTask.requiredRole) ?? agents;
      // Pick highest-trust available agent
      const sorted = [...candidates].sort((a, b) => b.trustScore - a.trustScore);
      if (sorted.length > 0) {
        assignments.push({ agent: sorted[0]!, subTask });
      }
    }

    return assignments;
  }

  /** Execute a single sub-task with an agent */
  private executeSubTask(agent: SwarmAgent, subTask: SwarmSubTask): SubTaskResult {
    // Validate the action
    const validation = this.validateAction(subTask, agent);

    // Build tongue signature
    const tongueSignature = this.signWithTongues(agent, validation);

    // Simulate execution (in production, this would use the actual browser backend)
    const success = validation.controlValid && validation.ioSafe && validation.policyCompliant;

    agent.tasksCompleted++;

    return {
      taskId: subTask.id,
      agentId: agent.id,
      success,
      data: success ? { target: subTask.target, action: subTask.action } : undefined,
      error: success ? undefined : 'Validation failed',
      tongueSignature,
      validation,
    };
  }

  /** Validate an action across all tongue dimensions */
  private validateAction(subTask: SwarmSubTask, agent: SwarmAgent): ValidationScores {
    return {
      controlValid: agent.status === 'active',
      ioSafe: !subTask.target.match(/^(javascript:|data:)/i),
      policyCompliant: subTask.action !== 'execute_script' || agent.trustScore > 0.8,
      logicSound: subTask.dependencies.length === 0, // Simplified: no unmet deps
      cryptoSecure:
        subTask.target.startsWith('https://') ||
        subTask.target.startsWith('about:') ||
        subTask.action !== 'navigate',
      typeSafe: !subTask.target.match(/\.(exe|dll|sh|bat)$/i),
    };
  }

  /** Create tongue signature from validation scores */
  private signWithTongues(agent: SwarmAgent, validation: ValidationScores): TongueSignature {
    const passedTongues: TongueCode[] = [];

    if (validation.controlValid) passedTongues.push('KO');
    if (validation.ioSafe) passedTongues.push('AV');
    if (validation.policyCompliant) passedTongues.push('RU');
    if (validation.logicSound) passedTongues.push('CA');
    if (validation.cryptoSecure) passedTongues.push('UM');
    if (validation.typeSafe) passedTongues.push('DR');

    const signatureHash = createHash('sha256')
      .update(`${agent.id}:${passedTongues.join(',')}:${Date.now()}`)
      .digest('hex')
      .slice(0, 32);

    return {
      agentId: agent.id,
      passedTongues,
      signatureHash,
      timestamp: Date.now(),
    };
  }

  /** Roundtable consensus: require threshold tongue signatures */
  private roundtableConsensus(results: SubTaskResult[], threshold: number): ConsensusResult {
    if (results.length === 0) return this.emptyConsensus();

    // Count tongue coverage across all results
    const tongueCounts: Record<TongueCode, number> = {
      KO: 0,
      AV: 0,
      RU: 0,
      CA: 0,
      UM: 0,
      DR: 0,
    };

    let approveCount = 0;
    let rejectCount = 0;

    for (const result of results) {
      if (result.success) {
        approveCount++;
        for (const tongue of result.tongueSignature.passedTongues) {
          tongueCounts[tongue]++;
        }
      } else {
        rejectCount++;
      }
    }

    // A tongue achieves consensus if majority of agents pass it
    const majorityThreshold = Math.ceil(results.length / 2);
    const consensusTongues: TongueCode[] = [];
    for (const [tongue, count] of Object.entries(tongueCounts) as Array<[TongueCode, number]>) {
      if (count >= majorityThreshold) {
        consensusTongues.push(tongue);
      }
    }

    // Compute combined trust score
    const activeAgents = results.map((r) => this.agents.get(r.agentId)).filter(Boolean) as SwarmAgent[];
    const avgTrust =
      activeAgents.length > 0
        ? activeAgents.reduce((sum, a) => sum + a.trustScore, 0) / activeAgents.length
        : 0;

    const approved =
      consensusTongues.length >= threshold && approveCount > rejectCount;

    return {
      approved,
      approveCount,
      rejectCount,
      totalParticipants: results.length,
      quorumMet: consensusTongues.length >= threshold,
      consensusTongues,
      trustScore: avgTrust,
    };
  }

  /** Update agent trust based on task outcome */
  private updateTrust(agentId: string, success: boolean): void {
    const agent = this.agents.get(agentId);
    if (!agent) return;

    const delta = success ? this.config.trustDeltaSuccess : this.config.trustDeltaFailure;
    agent.trustScore = Math.max(0, Math.min(1, agent.trustScore + delta));

    if (agent.trustScore < this.config.quarantineTrustThreshold) {
      agent.status = 'quarantined';
    }
  }

  private emptyConsensus(): ConsensusResult {
    return {
      approved: false,
      approveCount: 0,
      rejectCount: 0,
      totalParticipants: 0,
      quorumMet: false,
      consensusTongues: [],
      trustScore: 0,
    };
  }
}
