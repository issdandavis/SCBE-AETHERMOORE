/**
 * SCBE Agentic Coder Platform
 *
 * A multi-agent coding platform integrated with the Sacred Tongue system.
 * Provides 6 specialized agents aligned with the 6 Sacred Tongues for
 * collaborative software development tasks.
 *
 * @module agentic
 */

import { createHash } from 'crypto';

// =============================================================================
// TYPES
// =============================================================================

/** Agent roles aligned with development lifecycle */
export type AgentRole =
  | 'architect'
  | 'coder'
  | 'reviewer'
  | 'tester'
  | 'security'
  | 'deployer';

/** Sacred Tongue identifiers */
export type SacredTongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** AI provider types */
export type AIProvider = 'openai' | 'anthropic' | 'local';

/** Agent status */
export type AgentStatus = 'available' | 'busy' | 'offline';

/** Task types */
export type TaskType =
  | 'design'
  | 'implement'
  | 'review'
  | 'test'
  | 'security_audit'
  | 'deploy'
  | 'refactor'
  | 'debug';

/** Task complexity levels */
export type TaskComplexity = 'simple' | 'moderate' | 'complex';

/** Task status */
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/** Group collaboration modes */
export type GroupMode = 'solo' | 'pair' | 'trio';

/** Expected output types */
export type ExpectedOutput = 'code' | 'review' | 'tests' | 'design' | 'report' | 'deployment';

/** Event types for platform lifecycle */
export type EventType =
  | 'task_created'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'group_created'
  | 'group_dissolved'
  | 'agent_busy'
  | 'agent_available';

/** Spectral identity for agent verification */
export interface SpectralIdentity {
  spectralHash: string;
  frequency: number;
  harmonicSignature: number[];
  createdAt: number;
}

/** Agent statistics */
export interface AgentStats {
  tasksCompleted: number;
  totalTokens: number;
  averageConfidence: number;
  lastActive: number;
}

/** Built-in agent definition */
export interface BuiltInAgent {
  id: string;
  name: string;
  role: AgentRole;
  provider: AIProvider;
  model: string;
  systemPrompt: string;
  trustVector: number[];
  spectralIdentity: SpectralIdentity;
  status: AgentStatus;
  currentGroup?: string;
  stats: AgentStats;
}

/** Task definition */
export interface Task {
  id: string;
  type: TaskType;
  title: string;
  description: string;
  status: TaskStatus;
  complexity: TaskComplexity;
  language?: string;
  code?: string;
  constraints?: string[];
  expectedOutput: ExpectedOutput;
  createdAt: number;
  completedAt?: number;
  result?: TaskResult;
}

/** Task creation input */
export interface TaskInput {
  type: TaskType;
  title: string;
  description: string;
  language?: string;
  code?: string;
  constraints?: string[];
  complexity?: TaskComplexity;
}

/** Agent group for collaboration */
export interface TaskGroup {
  id: string;
  agents: string[];
  mode: GroupMode;
  currentTask?: string;
  leadAgent: string;
  createdAt: number;
}

/** Agent contribution to a task */
export interface Contribution {
  agentId: string;
  role: AgentRole;
  action: string;
  output: string;
  confidence: number;
  timestamp: number;
  tokens?: number;
}

/** Task execution result */
export interface TaskResult {
  success: boolean;
  output: string;
  contributions: Contribution[];
  confidence: number;
  totalTokens: number;
  duration: number;
}

/** Platform event */
export interface PlatformEvent {
  type: EventType;
  timestamp: number;
  data: Record<string, any>;
}

/** Platform statistics */
export interface PlatformStatistics {
  totalAgents: number;
  availableAgents: number;
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  activeGroups: number;
  totalTokensUsed: number;
}

/** Executor function type for task execution */
export type TaskExecutor = (
  agent: BuiltInAgent,
  action: string,
  context: string
) => Promise<{ output: string; confidence: number; tokens: number }>;

// =============================================================================
// CONSTANTS
// =============================================================================

/** Maps agent roles to their aligned Sacred Tongue */
export const ROLE_TONGUE_MAP: Record<AgentRole, SacredTongue> = {
  architect: 'KO', // Kor'aelin - Command/Control, system design
  coder: 'CA', // Cassisivadan - Ceremonies, implementation rituals
  reviewer: 'AV', // Avali - Sentiment analysis, code quality
  tester: 'RU', // Runethic - Historical patterns, regression
  security: 'UM', // Umbroth - Shadow operations, vulnerability hunting
  deployer: 'DR', // Draumric - Multi-party coordination, release
};

/** Sacred Tongue order for trust vector indexing */
export const TONGUE_ORDER: SacredTongue[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

/** Task type to recommended agent roles mapping */
export const TASK_AGENT_RECOMMENDATIONS: Record<TaskType, AgentRole[]> = {
  design: ['architect', 'reviewer'],
  implement: ['coder', 'architect'],
  review: ['reviewer', 'security'],
  test: ['tester', 'coder'],
  security_audit: ['security', 'reviewer'],
  deploy: ['deployer', 'security'],
  refactor: ['coder', 'architect', 'reviewer'],
  debug: ['coder', 'tester'],
};

/** Expected output for each task type */
const TASK_OUTPUT_MAP: Record<TaskType, ExpectedOutput> = {
  design: 'design',
  implement: 'code',
  review: 'review',
  test: 'tests',
  security_audit: 'report',
  deploy: 'deployment',
  refactor: 'code',
  debug: 'code',
};

/** Agent base frequencies (Hz) - aligned with harmonic system */
const AGENT_FREQUENCIES: Record<AgentRole, number> = {
  architect: 82.41, // E2 - foundation
  coder: 110.0, // A2 - implementation
  reviewer: 146.83, // D3 - analysis
  tester: 196.0, // G3 - validation
  security: 246.94, // B3 - protection
  deployer: 329.63, // E4 - release
};

/** System prompts for each agent role */
const AGENT_SYSTEM_PROMPTS: Record<AgentRole, string> = {
  architect: `You are the Architect Agent, aligned with Kor'aelin (KO) - the tongue of command and control.
Your role is to design system architecture, define interfaces, and establish patterns.
You think in terms of structure, scalability, and long-term maintainability.
You communicate through clear diagrams, specifications, and architectural decision records.
Your Sacred Tongue grants you mastery over system topology and information flow.
Always consider: modularity, separation of concerns, and future extensibility.`,

  coder: `You are the Coder Agent, aligned with Cassisivadan (CA) - the tongue of ceremonies.
Your role is to implement features, write clean code, and follow established patterns.
You treat coding as a craft, each function a ritual, each module a ceremony.
You communicate through well-documented, tested, and efficient code.
Your Sacred Tongue grants you fluency in implementation and algorithmic expression.
Always consider: readability, performance, and adherence to specifications.`,

  reviewer: `You are the Reviewer Agent, aligned with Avali (AV) - the tongue of sentiment.
Your role is to analyze code quality, identify issues, and suggest improvements.
You sense the "feeling" of code - its elegance, its pain points, its potential.
You communicate through constructive feedback and actionable suggestions.
Your Sacred Tongue grants you insight into code health and developer intent.
Always consider: maintainability, best practices, and team conventions.`,

  tester: `You are the Tester Agent, aligned with Runethic (RU) - the tongue of history.
Your role is to write tests, identify edge cases, and ensure reliability.
You learn from past failures, encoding that knowledge into comprehensive tests.
You communicate through test cases, coverage reports, and regression suites.
Your Sacred Tongue grants you memory of all past bugs and their patterns.
Always consider: edge cases, regression prevention, and test coverage.`,

  security: `You are the Security Agent, aligned with Umbroth (UM) - the tongue of shadows.
Your role is to identify vulnerabilities, assess risks, and enforce security.
You think like an attacker, probing for weaknesses in the darkness.
You communicate through security reports, CVE references, and remediation plans.
Your Sacred Tongue grants you vision into hidden attack vectors.
Always consider: OWASP top 10, supply chain risks, and defense in depth.`,

  deployer: `You are the Deployer Agent, aligned with Draumric (DR) - the tongue of coordination.
Your role is to orchestrate releases, manage infrastructure, and ensure smooth deployments.
You coordinate between systems, environments, and stakeholders.
You communicate through deployment plans, runbooks, and status updates.
Your Sacred Tongue grants you mastery over distributed coordination.
Always consider: rollback plans, health checks, and zero-downtime deployment.`,
};

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/** Generate a unique ID */
function generateId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
}

/** Generate spectral hash for agent identity */
function generateSpectralHash(role: AgentRole, provider: AIProvider): string {
  const data = `${role}-${provider}-${Date.now()}-${Math.random()}`;
  return createHash('sha256').update(data).digest('hex').slice(0, 16);
}

/** Generate harmonic signature based on role frequency */
function generateHarmonicSignature(baseFreq: number): number[] {
  const harmonics: number[] = [];
  for (let i = 1; i <= 6; i++) {
    harmonics.push(baseFreq * i * (1 + Math.random() * 0.01));
  }
  return harmonics;
}

/** Create trust vector aligned with Sacred Tongue */
function createTrustVector(role: AgentRole): number[] {
  const tongue = ROLE_TONGUE_MAP[role];
  const tongueIndex = TONGUE_ORDER.indexOf(tongue);

  // Base trust of 0.5 for all dimensions
  const vector = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5];

  // High trust (0.85-0.95) in aligned dimension
  vector[tongueIndex] = 0.85 + Math.random() * 0.1;

  // Moderate trust in adjacent dimensions
  const prevIndex = (tongueIndex + 5) % 6;
  const nextIndex = (tongueIndex + 1) % 6;
  vector[prevIndex] = 0.6 + Math.random() * 0.1;
  vector[nextIndex] = 0.6 + Math.random() * 0.1;

  return vector;
}

/** Get model name for provider */
function getModelForProvider(provider: AIProvider): string {
  switch (provider) {
    case 'anthropic':
      return 'claude-sonnet-4-20250514';
    case 'openai':
      return 'gpt-4o';
    case 'local':
      return 'llama-3.1-70b';
  }
}

/** Get agent name from role */
function getAgentName(role: AgentRole): string {
  const names: Record<AgentRole, string> = {
    architect: 'Archon',
    coder: 'Cipher',
    reviewer: 'Sentinel',
    tester: 'Oracle',
    security: 'Shadow',
    deployer: 'Herald',
  };
  return names[role];
}

/** Infer task complexity from description and constraints */
function inferComplexity(description: string, constraints?: string[]): TaskComplexity {
  const descLength = description.length;
  const constraintCount = constraints?.length || 0;

  if (descLength > 500 || constraintCount > 2) {
    return 'complex';
  } else if (descLength > 200 || constraintCount > 0) {
    return 'moderate';
  }
  return 'simple';
}

/** Default task executor (mock implementation) */
const defaultExecutor: TaskExecutor = async (agent, action, context) => {
  // Simulate processing time
  await new Promise((resolve) => setTimeout(resolve, 10));

  return {
    output: `[${agent.name}] Completed ${action}:\n${context.slice(0, 100)}...`,
    confidence: 0.8 + Math.random() * 0.15,
    tokens: Math.floor(100 + Math.random() * 400),
  };
};

// =============================================================================
// CLASSES
// =============================================================================

/**
 * Collaboration Engine
 * Manages multi-agent collaboration and contribution merging
 */
export class CollaborationEngine {
  /**
   * Merge contributions from multiple agents into a single output
   */
  mergeContributions(contributions: Contribution[]): string {
    const sorted = [...contributions].sort((a, b) => a.timestamp - b.timestamp);

    const sections = sorted.map((c) => {
      const header = `=== ${c.role.toUpperCase()} (${c.action}) ===`;
      return `${header}\n${c.output}`;
    });

    return sections.join('\n\n');
  }

  /**
   * Calculate weighted group confidence from contributions
   */
  calculateGroupConfidence(contributions: Contribution[]): number {
    if (contributions.length === 0) return 0;

    const sum = contributions.reduce((acc, c) => acc + c.confidence, 0);
    return sum / contributions.length;
  }

  /**
   * Detect conflicts between contributions
   */
  detectConflicts(contributions: Contribution[]): string[] {
    const conflicts: string[] = [];
    // Simple conflict detection - could be enhanced
    for (let i = 0; i < contributions.length; i++) {
      for (let j = i + 1; j < contributions.length; j++) {
        if (
          contributions[i].role === contributions[j].role &&
          contributions[i].action === contributions[j].action
        ) {
          conflicts.push(
            `Duplicate ${contributions[i].role} contribution for ${contributions[i].action}`
          );
        }
      }
    }
    return conflicts;
  }
}

/**
 * Task Group Manager
 * Manages agent groups and their lifecycle
 */
export class TaskGroupManager {
  private agents: BuiltInAgent[];
  private groups: Map<string, TaskGroup> = new Map();

  constructor(agents: BuiltInAgent[]) {
    this.agents = agents;
  }

  /**
   * Recommend group composition based on task type and complexity
   */
  recommendGroup(taskType: TaskType, complexity: TaskComplexity): AgentRole[] {
    const recommended = TASK_AGENT_RECOMMENDATIONS[taskType] || ['coder'];

    switch (complexity) {
      case 'simple':
        return [recommended[0]]; // Solo
      case 'moderate':
        return recommended.slice(0, 2); // Pair
      case 'complex':
        return recommended.slice(0, 3); // Trio (max 3)
    }
  }

  /**
   * Create a group for a specific task
   */
  createGroupForTask(taskId: string, roles: AgentRole[]): TaskGroup {
    const groupAgents = roles
      .map((role) => this.agents.find((a) => a.role === role && a.status === 'available'))
      .filter((a): a is BuiltInAgent => a !== undefined);

    if (groupAgents.length === 0) {
      throw new Error('No available agents for the requested roles');
    }

    const mode: GroupMode =
      groupAgents.length === 1 ? 'solo' : groupAgents.length === 2 ? 'pair' : 'trio';

    const group: TaskGroup = {
      id: generateId(),
      agents: groupAgents.map((a) => a.id),
      mode,
      currentTask: taskId,
      leadAgent: groupAgents[0].id,
      createdAt: Date.now(),
    };

    // Mark agents as busy
    for (const agent of groupAgents) {
      agent.status = 'busy';
      agent.currentGroup = group.id;
    }

    this.groups.set(group.id, group);
    return group;
  }

  /**
   * Create a custom group with specific roles
   */
  createCustomGroup(roles: AgentRole[]): TaskGroup {
    if (roles.length > 3) {
      throw new Error('Group size cannot exceed 3 agents');
    }

    const groupAgents = roles
      .map((role) => this.agents.find((a) => a.role === role && a.status === 'available'))
      .filter((a): a is BuiltInAgent => a !== undefined);

    if (groupAgents.length !== roles.length) {
      throw new Error('Some requested agents are not available');
    }

    const mode: GroupMode =
      groupAgents.length === 1 ? 'solo' : groupAgents.length === 2 ? 'pair' : 'trio';

    const group: TaskGroup = {
      id: generateId(),
      agents: groupAgents.map((a) => a.id),
      mode,
      leadAgent: groupAgents[0].id,
      createdAt: Date.now(),
    };

    // Mark agents as busy
    for (const agent of groupAgents) {
      agent.status = 'busy';
      agent.currentGroup = group.id;
    }

    this.groups.set(group.id, group);
    return group;
  }

  /**
   * Dissolve a group and release agents
   */
  dissolveGroup(groupId: string): void {
    const group = this.groups.get(groupId);
    if (!group) return;

    for (const agentId of group.agents) {
      const agent = this.agents.find((a) => a.id === agentId);
      if (agent) {
        agent.status = 'available';
        agent.currentGroup = undefined;
      }
    }

    this.groups.delete(groupId);
  }

  /**
   * Get agents in a group
   */
  getGroupAgents(groupId: string): BuiltInAgent[] {
    const group = this.groups.get(groupId);
    if (!group) return [];

    return group.agents
      .map((id) => this.agents.find((a) => a.id === id))
      .filter((a): a is BuiltInAgent => a !== undefined);
  }

  /**
   * Get the lead agent of a group
   */
  getLeadAgent(groupId: string): BuiltInAgent | undefined {
    const group = this.groups.get(groupId);
    if (!group) return undefined;

    return this.agents.find((a) => a.id === group.leadAgent);
  }

  /**
   * Get all active groups
   */
  getActiveGroups(): TaskGroup[] {
    return Array.from(this.groups.values());
  }

  /**
   * Get group by ID
   */
  getGroup(groupId: string): TaskGroup | undefined {
    return this.groups.get(groupId);
  }
}

/**
 * Agentic Coder Platform
 * Main platform class for managing agents, tasks, and execution
 */
export class AgenticCoderPlatform {
  private agents: BuiltInAgent[];
  private tasks: Map<string, Task> = new Map();
  private groupManager: TaskGroupManager;
  private collaborationEngine: CollaborationEngine;
  private eventListeners: ((event: PlatformEvent) => void)[] = [];

  constructor(provider: AIProvider = 'openai') {
    this.agents = createBuiltInAgents(provider);
    this.groupManager = new TaskGroupManager(this.agents);
    this.collaborationEngine = new CollaborationEngine();
  }

  // ---------------------------------------------------------------------------
  // Agent Management
  // ---------------------------------------------------------------------------

  /**
   * Get all agents
   */
  getAgents(): BuiltInAgent[] {
    return [...this.agents];
  }

  /**
   * Get agent by role
   */
  getAgentByRole(role: AgentRole): BuiltInAgent | undefined {
    return this.agents.find((a) => a.role === role);
  }

  /**
   * Get agent by ID
   */
  getAgentById(id: string): BuiltInAgent | undefined {
    return this.agents.find((a) => a.id === id);
  }

  /**
   * Get recommended agents for a task type
   */
  getRecommendedAgents(taskType: TaskType): AgentRole[] {
    return TASK_AGENT_RECOMMENDATIONS[taskType] || ['coder'];
  }

  // ---------------------------------------------------------------------------
  // Task Management
  // ---------------------------------------------------------------------------

  /**
   * Create a new task
   */
  createTask(input: TaskInput): Task {
    const complexity = input.complexity || inferComplexity(input.description, input.constraints);

    const task: Task = {
      id: generateId(),
      type: input.type,
      title: input.title,
      description: input.description,
      status: 'pending',
      complexity,
      language: input.language,
      code: input.code,
      constraints: input.constraints,
      expectedOutput: TASK_OUTPUT_MAP[input.type],
      createdAt: Date.now(),
    };

    this.tasks.set(task.id, task);
    this.emitEvent('task_created', { taskId: task.id, type: task.type });

    return task;
  }

  /**
   * Get task by ID
   */
  getTask(taskId: string): Task | undefined {
    return this.tasks.get(taskId);
  }

  /**
   * Get all tasks
   */
  getTasks(): Task[] {
    return Array.from(this.tasks.values());
  }

  // ---------------------------------------------------------------------------
  // Group Management
  // ---------------------------------------------------------------------------

  /**
   * Create a group for a task
   */
  createGroupForTask(taskId: string): TaskGroup {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    const recommendedRoles = this.groupManager.recommendGroup(task.type, task.complexity);
    const group = this.groupManager.createGroupForTask(taskId, recommendedRoles);

    this.emitEvent('group_created', { groupId: group.id, taskId, agents: group.agents });

    return group;
  }

  /**
   * Create a custom group with specific roles
   */
  createCustomGroup(roles: AgentRole[]): TaskGroup {
    const group = this.groupManager.createCustomGroup(roles);
    this.emitEvent('group_created', { groupId: group.id, agents: group.agents });
    return group;
  }

  /**
   * Dissolve a group
   */
  dissolveGroup(groupId: string): void {
    this.groupManager.dissolveGroup(groupId);
    this.emitEvent('group_dissolved', { groupId });
  }

  // ---------------------------------------------------------------------------
  // Task Execution
  // ---------------------------------------------------------------------------

  /**
   * Execute a task with optional custom executor
   */
  async executeTask(
    taskId: string,
    groupId?: string,
    executor: TaskExecutor = defaultExecutor
  ): Promise<TaskResult> {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    // Create group if not provided
    let group: TaskGroup;
    if (groupId) {
      const existingGroup = this.groupManager.getGroup(groupId);
      if (!existingGroup) {
        throw new Error(`Group ${groupId} not found`);
      }
      group = existingGroup;
    } else {
      group = this.createGroupForTask(taskId);
    }

    // Update task status
    task.status = 'in_progress';
    this.emitEvent('task_started', { taskId, groupId: group.id });

    const startTime = Date.now();
    const contributions: Contribution[] = [];
    let totalTokens = 0;

    try {
      // Execute with each agent in the group
      const groupAgents = this.groupManager.getGroupAgents(group.id);

      for (const agent of groupAgents) {
        const action = this.getActionForRole(agent.role, task.type);
        const context = this.buildContext(task, contributions);

        const result = await executor(agent, action, context);

        const contribution: Contribution = {
          agentId: agent.id,
          role: agent.role,
          action,
          output: result.output,
          confidence: result.confidence,
          timestamp: Date.now(),
          tokens: result.tokens,
        };

        contributions.push(contribution);
        totalTokens += result.tokens;

        // Update agent stats
        agent.stats.tasksCompleted++;
        agent.stats.totalTokens += result.tokens;
        agent.stats.averageConfidence =
          (agent.stats.averageConfidence * (agent.stats.tasksCompleted - 1) + result.confidence) /
          agent.stats.tasksCompleted;
        agent.stats.lastActive = Date.now();
      }

      // Merge contributions
      const output = this.collaborationEngine.mergeContributions(contributions);
      const confidence = this.collaborationEngine.calculateGroupConfidence(contributions);

      const result: TaskResult = {
        success: true,
        output,
        contributions,
        confidence,
        totalTokens,
        duration: Date.now() - startTime,
      };

      // Update task
      task.status = 'completed';
      task.completedAt = Date.now();
      task.result = result;

      this.emitEvent('task_completed', { taskId, result });

      // Dissolve the group
      this.dissolveGroup(group.id);

      return result;
    } catch (error) {
      task.status = 'failed';
      this.emitEvent('task_failed', { taskId, error: String(error) });

      // Dissolve the group
      this.dissolveGroup(group.id);

      return {
        success: false,
        output: `Task failed: ${error}`,
        contributions,
        confidence: 0,
        totalTokens,
        duration: Date.now() - startTime,
      };
    }
  }

  /**
   * Get action description for role and task type
   */
  private getActionForRole(role: AgentRole, taskType: TaskType): string {
    const actionMap: Record<AgentRole, Record<TaskType, string>> = {
      architect: {
        design: 'design_system',
        implement: 'review_design',
        review: 'architecture_review',
        test: 'test_strategy',
        security_audit: 'threat_modeling',
        deploy: 'deployment_architecture',
        refactor: 'refactoring_plan',
        debug: 'root_cause_analysis',
      },
      coder: {
        design: 'prototype',
        implement: 'implement',
        review: 'suggest_improvements',
        test: 'write_tests',
        security_audit: 'fix_vulnerabilities',
        deploy: 'deployment_scripts',
        refactor: 'refactor_code',
        debug: 'debug_fix',
      },
      reviewer: {
        design: 'design_review',
        implement: 'code_review',
        review: 'comprehensive_review',
        test: 'test_review',
        security_audit: 'security_review',
        deploy: 'deployment_review',
        refactor: 'refactor_review',
        debug: 'debug_review',
      },
      tester: {
        design: 'testability_review',
        implement: 'unit_tests',
        review: 'test_coverage',
        test: 'comprehensive_testing',
        security_audit: 'security_testing',
        deploy: 'smoke_tests',
        refactor: 'regression_tests',
        debug: 'reproduce_bug',
      },
      security: {
        design: 'security_requirements',
        implement: 'security_scan',
        review: 'vulnerability_check',
        test: 'penetration_test',
        security_audit: 'full_audit',
        deploy: 'security_verification',
        refactor: 'security_impact',
        debug: 'security_analysis',
      },
      deployer: {
        design: 'infrastructure_design',
        implement: 'ci_cd_setup',
        review: 'deployment_review',
        test: 'integration_tests',
        security_audit: 'infrastructure_audit',
        deploy: 'deploy',
        refactor: 'infrastructure_update',
        debug: 'deployment_debug',
      },
    };

    return actionMap[role][taskType] || 'execute';
  }

  /**
   * Build context string for agent execution
   */
  private buildContext(task: Task, previousContributions: Contribution[]): string {
    let context = `Task: ${task.title}\n`;
    context += `Type: ${task.type}\n`;
    context += `Description: ${task.description}\n`;

    if (task.language) {
      context += `Language: ${task.language}\n`;
    }

    if (task.code) {
      context += `Code:\n\`\`\`\n${task.code}\n\`\`\`\n`;
    }

    if (task.constraints && task.constraints.length > 0) {
      context += `Constraints:\n${task.constraints.map((c) => `- ${c}`).join('\n')}\n`;
    }

    if (previousContributions.length > 0) {
      context += `\nPrevious contributions:\n`;
      context += this.collaborationEngine.mergeContributions(previousContributions);
    }

    return context;
  }

  // ---------------------------------------------------------------------------
  // Statistics & Events
  // ---------------------------------------------------------------------------

  /**
   * Get platform statistics
   */
  getStatistics(): PlatformStatistics {
    const tasks = Array.from(this.tasks.values());

    return {
      totalAgents: this.agents.length,
      availableAgents: this.agents.filter((a) => a.status === 'available').length,
      totalTasks: tasks.length,
      completedTasks: tasks.filter((t) => t.status === 'completed').length,
      failedTasks: tasks.filter((t) => t.status === 'failed').length,
      activeGroups: this.groupManager.getActiveGroups().length,
      totalTokensUsed: this.agents.reduce((acc, a) => acc + a.stats.totalTokens, 0),
    };
  }

  /**
   * Register event listener
   */
  onEvent(listener: (event: PlatformEvent) => void): void {
    this.eventListeners.push(listener);
  }

  /**
   * Emit platform event
   */
  private emitEvent(type: EventType, data: Record<string, any>): void {
    const event: PlatformEvent = {
      type,
      timestamp: Date.now(),
      data,
    };

    for (const listener of this.eventListeners) {
      try {
        listener(event);
      } catch (e) {
        console.error('Event listener error:', e);
      }
    }
  }
}

// =============================================================================
// FACTORY FUNCTIONS
// =============================================================================

/**
 * Create the 6 built-in agents
 */
export function createBuiltInAgents(provider: AIProvider = 'openai'): BuiltInAgent[] {
  const roles: AgentRole[] = ['architect', 'coder', 'reviewer', 'tester', 'security', 'deployer'];

  return roles.map((role) => {
    const frequency = AGENT_FREQUENCIES[role];

    return {
      id: generateId(),
      name: getAgentName(role),
      role,
      provider,
      model: getModelForProvider(provider),
      systemPrompt: AGENT_SYSTEM_PROMPTS[role],
      trustVector: createTrustVector(role),
      spectralIdentity: {
        spectralHash: generateSpectralHash(role, provider),
        frequency,
        harmonicSignature: generateHarmonicSignature(frequency),
        createdAt: Date.now(),
      },
      status: 'available',
      stats: {
        tasksCompleted: 0,
        totalTokens: 0,
        averageConfidence: 0,
        lastActive: Date.now(),
      },
    };
  });
}

/**
 * Create an agentic platform instance
 */
export function createAgenticPlatform(provider: AIProvider = 'openai'): AgenticCoderPlatform {
  return new AgenticCoderPlatform(provider);
}

// =============================================================================
// EXPORTS
// =============================================================================

export default {
  AgenticCoderPlatform,
  TaskGroupManager,
  CollaborationEngine,
  createAgenticPlatform,
  createBuiltInAgents,
  ROLE_TONGUE_MAP,
  TASK_AGENT_RECOMMENDATIONS,
  TONGUE_ORDER,
};
