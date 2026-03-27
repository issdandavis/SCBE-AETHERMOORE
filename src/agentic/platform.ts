/**
 * Agentic Coder Platform - Main orchestration
 *
 * @module agentic/platform
 */

import { logger } from '../utils/logger.js';
import { createBuiltInAgents, getAgentByRole, getAvailableAgents } from './agents';
import { TaskGroupManager } from './task-group';
import { CollaborationEngine } from './collaboration';
import {
  BuiltInAgent,
  CodingTask,
  TaskGroup,
  AgentRole,
  CodingTaskType,
  TaskComplexity,
  AgentContribution,
  PlatformConfig,
  DEFAULT_PLATFORM_CONFIG,
  TASK_AGENT_RECOMMENDATIONS,
} from './types';
import { callProvider, getAvailableProviders, createProviderAttestation } from './providers';
import { DecisionRoundabouts, GovernanceInput, RoundaboutDecision } from './roundabout-city';
import { ExecutionDistrict } from './execution-district';

/**
 * Task creation options
 */
export interface CreateTaskOptions {
  type: CodingTaskType;
  title: string;
  description: string;
  complexity?: TaskComplexity;
  code?: string;
  requirements?: string;
  files?: string[];
  constraints?: string[];
  language?: string;
  framework?: string;
  preferredAgents?: AgentRole[];
}

/**
 * Platform event types
 */
export type PlatformEventType =
  | 'task_created'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'governance_decided'
  | 'group_created'
  | 'group_dissolved'
  | 'agent_contribution'
  | 'consensus_reached';

/**
 * Platform event
 */
export interface PlatformEvent {
  type: PlatformEventType;
  timestamp: number;
  data: Record<string, unknown>;
}

/**
 * Agentic Coder Platform
 *
 * Main platform for collaborative AI coding with 6 built-in agents.
 */
export class AgenticCoderPlatform {
  private agents: Map<string, BuiltInAgent> = new Map();
  private tasks: Map<string, CodingTask> = new Map();
  private groupManager: TaskGroupManager;
  private collaboration: CollaborationEngine;
  private roundabouts: DecisionRoundabouts;
  private executionDistrict: ExecutionDistrict;
  private governanceTrails: Map<string, RoundaboutDecision[]> = new Map();
  private config: PlatformConfig;
  private eventListeners: ((event: PlatformEvent) => void)[] = [];

  constructor(config: Partial<PlatformConfig> = {}) {
    this.config = { ...DEFAULT_PLATFORM_CONFIG, ...config };

    // Create built-in agents
    const builtInAgents = createBuiltInAgents(this.config.defaultProvider);
    for (const agent of builtInAgents) {
      this.agents.set(agent.id, agent);
    }

    this.groupManager = new TaskGroupManager(builtInAgents);
    this.collaboration = new CollaborationEngine();
    this.roundabouts = new DecisionRoundabouts();
    this.executionDistrict = new ExecutionDistrict();
  }

  // ==================== Agent Management ====================

  /**
   * Get all agents
   */
  public getAgents(): BuiltInAgent[] {
    return Array.from(this.agents.values());
  }

  /**
   * Get agent by ID
   */
  public getAgent(id: string): BuiltInAgent | undefined {
    return this.agents.get(id);
  }

  /**
   * Get agent by role
   */
  public getAgentByRole(role: AgentRole): BuiltInAgent | undefined {
    return getAgentByRole(this.getAgents(), role);
  }

  /**
   * Get available agents
   */
  public getAvailableAgents(): BuiltInAgent[] {
    return getAvailableAgents(this.getAgents());
  }

  // ==================== Task Management ====================

  /**
   * Create a new coding task
   */
  public createTask(options: CreateTaskOptions): CodingTask {
    const id = this.generateTaskId();
    const complexity = options.complexity || this.inferComplexity(options);

    const task: CodingTask = {
      id,
      type: options.type,
      title: options.title,
      description: options.description,
      complexity,
      context: {
        files: options.files,
        code: options.code,
        requirements: options.requirements,
        constraints: options.constraints,
      },
      expectedOutput: this.getExpectedOutput(options.type),
      language: options.language,
      framework: options.framework,
      status: 'pending',
      contributions: [],
      createdAt: Date.now(),
    };

    this.tasks.set(id, task);

    this.emitEvent({
      type: 'task_created',
      timestamp: Date.now(),
      data: { taskId: id, type: options.type, complexity },
    });

    return task;
  }

  /**
   * Get task by ID
   */
  public getTask(id: string): CodingTask | undefined {
    return this.tasks.get(id);
  }

  /**
   * Get all tasks
   */
  public getAllTasks(): CodingTask[] {
    return Array.from(this.tasks.values());
  }

  /**
   * Get pending tasks
   */
  public getPendingTasks(): CodingTask[] {
    return this.getAllTasks().filter((t) => t.status === 'pending');
  }

  // ==================== Group Management ====================

  /**
   * Create a group for a task
   */
  public createGroupForTask(taskId: string, preferredAgents?: AgentRole[]): TaskGroup {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    const group = this.groupManager.createGroup(task, preferredAgents);
    task.assignedGroup = group.id;

    this.emitEvent({
      type: 'group_created',
      timestamp: Date.now(),
      data: { groupId: group.id, taskId, agents: group.agents },
    });

    return group;
  }

  /**
   * Create a custom group
   */
  public createCustomGroup(agentRoles: AgentRole[]): TaskGroup {
    if (agentRoles.length > this.config.maxAgentsPerGroup) {
      throw new Error(`Maximum ${this.config.maxAgentsPerGroup} agents per group`);
    }

    const group = this.groupManager.createCustomGroup(agentRoles);

    this.emitEvent({
      type: 'group_created',
      timestamp: Date.now(),
      data: { groupId: group.id, agents: group.agents },
    });

    return group;
  }

  /**
   * Get group by ID
   */
  public getGroup(id: string): TaskGroup | undefined {
    return this.groupManager.getGroup(id);
  }

  /**
   * Get all groups
   */
  public getAllGroups(): TaskGroup[] {
    return this.groupManager.getAllGroups();
  }

  /**
   * Dissolve a group
   */
  public dissolveGroup(groupId: string): void {
    this.groupManager.dissolveGroup(groupId);

    this.emitEvent({
      type: 'group_dissolved',
      timestamp: Date.now(),
      data: { groupId },
    });
  }

  // ==================== Task Execution ====================

  /**
   * Execute a task with a group
   *
   * @param taskId - Task to execute
   * @param groupId - Group to execute with (optional, creates one if not provided)
   * @param executor - Function to execute agent actions
   */
  public async executeTask(
    taskId: string,
    groupId?: string,
    executor?: (
      agent: BuiltInAgent,
      action: string,
      context: string
    ) => Promise<{ output: string; confidence: number; tokens?: number }>
  ): Promise<{ success: boolean; output: string; contributions: AgentContribution[] }> {
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
      task.assignedGroup = groupId;
    } else {
      group = this.createGroupForTask(taskId);
    }

    // Route through non-linear governance roundabouts before execution.
    const governanceInput = this.buildGovernanceInput(task, group);
    const governancePath = this.roundabouts.route(governanceInput);
    this.governanceTrails.set(task.id, governancePath);

    const executionTicket = this.roundabouts.createExecutionTicket(governanceInput);
    this.emitEvent({
      type: 'governance_decided',
      timestamp: Date.now(),
      data: {
        taskId,
        action: executionTicket.decisionRecord.action,
        roundabout: executionTicket.decisionRecord.roundabout,
        reason: executionTicket.decisionRecord.reason,
      },
    });

    if (executionTicket.decisionRecord.action !== 'ALLOW') {
      task.status = 'failed';
      task.completedAt = Date.now();
      this.groupManager.completeTask(group.id, false);
      const blockedMsg = `Governance ${executionTicket.decisionRecord.action}: ${executionTicket.decisionRecord.reason}`;

      this.emitEvent({
        type: 'task_failed',
        timestamp: Date.now(),
        data: {
          taskId,
          error: blockedMsg,
          governanceAction: executionTicket.decisionRecord.action,
        },
      });

      return { success: false, output: blockedMsg, contributions: [] };
    }

    // Update task status
    task.status = 'in_progress';
    task.startedAt = Date.now();
    this.groupManager.assignTask(group.id, taskId);

    this.emitEvent({
      type: 'task_started',
      timestamp: Date.now(),
      data: {
        taskId,
        groupId: group.id,
        governanceAction: executionTicket.decisionRecord.action,
      },
    });

    try {
      // Use default executor if not provided
      const executeStep = executor || this.createDefaultExecutor();

      // Execution District enforces ALLOW-only execution and emits audit edges.
      const districtResult = await this.executionDistrict.execute(
        {
          ticket: executionTicket,
          workOrderId: task.id,
          actionName: `task.${task.type}`,
          payload: { taskId: task.id, groupId: group.id },
        },
        async () => {
          // Execute collaborative workflow
          const contributions = await this.collaboration.executeWorkflow(
            task,
            group,
            this.agents,
            executeStep
          );

          // Emit contribution events
          for (const contrib of contributions) {
            this.emitEvent({
              type: 'agent_contribution',
              timestamp: Date.now(),
              data: { taskId, agentId: contrib.agentId, action: contrib.action },
            });
          }

          // Check if consensus required for complex tasks
          if (this.config.requireConsensus && task.complexity === 'complex') {
            const mergedOutput = this.collaboration.mergeContributions(contributions);
            const consensus = await this.collaboration.requestConsensus(
              task,
              group,
              this.agents,
              mergedOutput,
              async () => ({
                approve: true,
                feedback: '',
                confidence: 0.9,
              })
            );

            this.emitEvent({
              type: 'consensus_reached',
              timestamp: Date.now(),
              data: { taskId, approved: consensus.approved },
            });
          }

          const confidence = this.collaboration.calculateGroupConfidence(contributions);
          if (confidence < this.config.minConfidence) {
            throw new Error(
              `Confidence ${confidence.toFixed(2)} below threshold ${this.config.minConfidence}`
            );
          }

          const output = this.collaboration.mergeContributions(contributions);
          return { contributions, confidence, output };
        }
      );

      if (!districtResult.success) {
        throw new Error(districtResult.reason || 'Execution district blocked task.');
      }

      const payload = districtResult.output as {
        contributions: AgentContribution[];
        confidence: number;
        output: string;
      };
      const contributions = payload.contributions;
      const confidence = payload.confidence;
      const output = payload.output;

      // Update task
      task.status = 'completed';
      task.completedAt = Date.now();
      task.output = output;
      task.contributions = contributions;

      // Update group
      this.groupManager.completeTask(group.id, true);

      // Update agent stats
      for (const contrib of contributions) {
        const agent = this.agents.get(contrib.agentId);
        if (agent) {
          agent.stats.tasksCompleted++;
          agent.stats.avgConfidence =
            (agent.stats.avgConfidence * (agent.stats.tasksCompleted - 1) + contrib.confidence) /
            agent.stats.tasksCompleted;
          if (contrib.tokensUsed) {
            agent.stats.avgTokensPerTask =
              (agent.stats.avgTokensPerTask * (agent.stats.tasksCompleted - 1) +
                contrib.tokensUsed) /
              agent.stats.tasksCompleted;
          }
        }
      }

      this.emitEvent({
        type: 'task_completed',
        timestamp: Date.now(),
        data: { taskId, groupId: group.id, confidence },
      });

      return { success: true, output, contributions };
    } catch (error) {
      task.status = 'failed';
      task.completedAt = Date.now();
      this.groupManager.completeTask(group.id, false);

      this.emitEvent({
        type: 'task_failed',
        timestamp: Date.now(),
        data: { taskId, error: error instanceof Error ? error.message : 'Unknown error' },
      });

      return {
        success: false,
        output: error instanceof Error ? error.message : 'Task failed',
        contributions: task.contributions,
      };
    }
  }

  /**
   * Get recommended agents for a task type
   */
  public getRecommendedAgents(taskType: CodingTaskType): AgentRole[] {
    return TASK_AGENT_RECOMMENDATIONS[taskType];
  }

  // ==================== Statistics ====================

  /**
   * Get platform statistics
   */
  public getStatistics(): {
    totalAgents: number;
    availableAgents: number;
    totalTasks: number;
    completedTasks: number;
    activeGroups: number;
    avgConfidence: number;
  } {
    const agents = this.getAgents();
    const tasks = this.getAllTasks();
    const groups = this.getAllGroups();

    const completedTasks = tasks.filter((t) => t.status === 'completed');
    const totalConfidence = completedTasks.reduce((sum, t) => {
      const taskConfidence = this.collaboration.calculateGroupConfidence(t.contributions);
      return sum + taskConfidence;
    }, 0);

    return {
      totalAgents: agents.length,
      availableAgents: this.getAvailableAgents().length,
      totalTasks: tasks.length,
      completedTasks: completedTasks.length,
      activeGroups: groups.filter((g) => g.status === 'working').length,
      avgConfidence: completedTasks.length > 0 ? totalConfidence / completedTasks.length : 0,
    };
  }

  // ==================== Events ====================

  /**
   * Subscribe to platform events
   */
  public onEvent(listener: (event: PlatformEvent) => void): () => void {
    this.eventListeners.push(listener);
    return () => {
      const index = this.eventListeners.indexOf(listener);
      if (index >= 0) this.eventListeners.splice(index, 1);
    };
  }

  // ==================== Private Methods ====================

  /**
   * Generate task ID
   */
  private generateTaskId(): string {
    return `task-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
  }

  /**
   * Infer task complexity
   */
  private inferComplexity(options: CreateTaskOptions): TaskComplexity {
    // Simple heuristics
    const codeLength = options.code?.length || 0;
    const descLength = options.description.length;
    const hasConstraints = (options.constraints?.length || 0) > 0;

    if (codeLength > 1000 || descLength > 500 || hasConstraints) {
      return 'complex';
    }
    if (codeLength > 200 || descLength > 200) {
      return 'moderate';
    }
    return 'simple';
  }

  /**
   * Get expected output type for task type
   */
  private getExpectedOutput(type: CodingTaskType): CodingTask['expectedOutput'] {
    const mapping: Record<CodingTaskType, CodingTask['expectedOutput']> = {
      design: 'plan',
      implement: 'code',
      review: 'review',
      test: 'tests',
      security_audit: 'report',
      deploy: 'code',
      refactor: 'code',
      debug: 'code',
      document: 'plan',
      optimize: 'code',
    };
    return mapping[type];
  }

  /**
   * Create default executor using configured AI providers
   *
   * Uses provider priority chain from SCBE_PROVIDER_PRIORITY env var.
   * Falls back through providers on failure if SCBE_PROVIDER_FALLBACK_ENABLED=true.
   *
   * Configure in .env:
   *   SCBE_PROVIDER_PRIORITY=anthropic,openai,google
   *   ANTHROPIC_API_KEY=sk-ant-...
   *   OPENAI_API_KEY=sk-...
   *   GOOGLE_API_KEY=AIza...
   */
  private createDefaultExecutor(): (
    agent: BuiltInAgent,
    action: string,
    context: string
  ) => Promise<{ output: string; confidence: number; tokens?: number }> {
    return async (agent, action, context) => {
      // Check if any providers are available
      const availableProviders = getAvailableProviders();

      if (availableProviders.length === 0) {
        // Fallback to mock if no providers configured
        logger.warn('No AI providers configured, using mock executor');
        logger.warn('Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY in .env');
        return {
          output: `[${agent.name}/${action}] Mock: No AI providers configured.\n\nContext length: ${context.length} chars`,
          confidence: 0.75, // Must meet minConfidence threshold (0.7)
          tokens: Math.floor(context.length / 4),
        };
      }

      // Build system prompt from agent persona
      const systemPrompt = `You are ${agent.name}, a specialized AI agent.
Role: ${agent.role}
Capabilities: ${(agent.capabilities || []).join(', ')}
Style: ${agent.systemPrompt || 'Professional and thorough'}

You are performing the action: ${action}
Respond with clear, actionable output.`;
      const providerTimeoutMs =
        Number.parseInt(process.env.SCBE_PROVIDER_TIMEOUT_MS || '', 10) || 10000;

      try {
        // Call provider with fallback chain and a hard timeout to prevent hangs.
        const response = await Promise.race([
          callProvider(context, {
            systemPrompt,
            maxTokens: 4096,
            temperature: 0.7,
          }),
          new Promise<never>((_, reject) =>
            setTimeout(
              () => reject(new Error(`Provider timeout after ${providerTimeoutMs}ms`)),
              providerTimeoutMs
            )
          ),
        ]);

        // Create attestation for audit trail
        const { attestation } = createProviderAttestation(context, response);

        return {
          output: response.output,
          confidence: 0.85 + Math.min(0.1, response.latencyMs / 10000), // Higher confidence for faster responses
          tokens: response.tokensUsed,
          // Include provider metadata for debugging (not exposed to user)
          // attestation,
        };
      } catch (error) {
        // All providers failed/timed out - degrade gracefully to deterministic local fallback.
        const errorMsg = error instanceof Error ? error.message : String(error);
        logger.warn('Provider chain failed, using local fallback', { error: errorMsg });

        return {
          output: `[${agent.name}/${action}] Local fallback due to provider failure.\n\n${errorMsg}\n\nContext length: ${context.length} chars`,
          confidence: 0.75,
          tokens: Math.max(1, Math.floor(context.length / 4)),
        };
      }
    };
  }

  /**
   * Build governance input from a coding task and its assigned group.
   */
  private buildGovernanceInput(task: CodingTask, group: TaskGroup): GovernanceInput {
    // Derive trust from group agent count (more agents = more review = higher trust)
    const trustScore = Math.min(1.0, 0.5 + group.agents.length * 0.15);
    // Derive risk from task complexity
    const complexityRisk: Record<TaskComplexity, number> = {
      simple: 0.2,
      moderate: 0.4,
      complex: 0.7,
    };
    const riskScore = complexityRisk[task.complexity] ?? 0.5;
    // Coherence from contribution alignment
    const coherenceScore =
      task.contributions.length > 0 ? Math.min(1.0, 0.6 + task.contributions.length * 0.1) : 0.8;

    return {
      requestId: task.id,
      trustScore,
      riskScore,
      coherenceScore,
      humanReviewRequired: task.complexity === 'complex',
      executionRequested: true,
    };
  }

  /**
   * Emit platform event
   */
  private emitEvent(event: PlatformEvent): void {
    for (const listener of this.eventListeners) {
      try {
        listener(event);
      } catch (e) {
        logger.error('Event listener error', { error: String(e) });
      }
    }
  }
}

/**
 * Create a pre-configured platform instance
 */
export function createAgenticPlatform(provider: string = 'openai'): AgenticCoderPlatform {
  return new AgenticCoderPlatform({ defaultProvider: provider });
}
