/**
 * Agentic Coder Platform - Main orchestration
 *
 * @module agentic/platform
 */

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

    // Update task status
    task.status = 'in_progress';
    task.startedAt = Date.now();
    this.groupManager.assignTask(group.id, taskId);

    this.emitEvent({
      type: 'task_started',
      timestamp: Date.now(),
      data: { taskId, groupId: group.id },
    });

    try {
      // Use default executor if not provided
      const executeStep = executor || this.createDefaultExecutor();

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
          async (agent, proposal) => ({
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

      // Calculate confidence
      const confidence = this.collaboration.calculateGroupConfidence(contributions);

      if (confidence < this.config.minConfidence) {
        throw new Error(
          `Confidence ${confidence.toFixed(2)} below threshold ${this.config.minConfidence}`
        );
      }

      // Merge contributions into final output
      const output = this.collaboration.mergeContributions(contributions);

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
   * Create default executor (mock for testing)
   */
  private createDefaultExecutor(): (
    agent: BuiltInAgent,
    action: string,
    context: string
  ) => Promise<{ output: string; confidence: number; tokens?: number }> {
    return async (agent, action, context) => {
      // Mock execution - in production, this would call the AI provider
      return {
        output: `[${agent.name}/${action}] Processed task based on context.\n\nContext length: ${context.length} chars`,
        confidence: 0.85 + Math.random() * 0.1,
        tokens: Math.floor(context.length / 4),
      };
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
        console.error('Event listener error:', e);
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
