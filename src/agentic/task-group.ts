/**
 * Task Group - Manages groups of 1-3 agents working together
 *
 * @module agentic/task-group
 */

import {
  AgentRole,
  BuiltInAgent,
  COMPLEXITY_GROUP_SIZE,
  CodingTask,
  CodingTaskType,
  CollaborationMode,
  TASK_AGENT_RECOMMENDATIONS,
  TaskComplexity,
  TaskGroup,
} from './types';

/**
 * Task Group Manager
 *
 * Creates and manages groups of agents for collaborative coding tasks.
 */
export class TaskGroupManager {
  private groups: Map<string, TaskGroup> = new Map();
  private agents: Map<string, BuiltInAgent> = new Map();

  constructor(agents: BuiltInAgent[]) {
    for (const agent of agents) {
      this.agents.set(agent.id, agent);
    }
  }

  /**
   * Create a task group for a specific task
   */
  public createGroup(task: CodingTask, preferredAgents?: AgentRole[]): TaskGroup {
    // Determine group size based on complexity
    const mode = COMPLEXITY_GROUP_SIZE[task.complexity];
    const groupSize = mode === 'solo' ? 1 : mode === 'pair' ? 2 : 3;

    // Get recommended agents for this task type
    const recommended = preferredAgents || TASK_AGENT_RECOMMENDATIONS[task.type];

    // Select available agents
    const selectedAgents = this.selectAgents(recommended, groupSize);

    if (selectedAgents.length === 0) {
      throw new Error('No available agents for this task');
    }

    const id = this.generateGroupId();
    const group: TaskGroup = {
      id,
      name: this.generateGroupName(selectedAgents),
      agents: selectedAgents.map((a) => a.id),
      currentTask: task.id,
      mode: this.getModeForSize(selectedAgents.length),
      status: 'idle',
      tasksCompleted: 0,
      successRate: 1.0,
      createdAt: Date.now(),
    };

    // Mark agents as busy
    for (const agent of selectedAgents) {
      agent.status = 'busy';
      agent.currentGroup = id;
    }

    this.groups.set(id, group);
    return group;
  }

  /**
   * Create a custom group with specific agents
   */
  public createCustomGroup(agentRoles: AgentRole[]): TaskGroup {
    if (agentRoles.length < 1 || agentRoles.length > 3) {
      throw new Error('Group must have 1-3 agents');
    }

    const selectedAgents: BuiltInAgent[] = [];
    for (const role of agentRoles) {
      const agent = this.getAvailableAgentByRole(role);
      if (!agent) {
        throw new Error(`No available agent for role: ${role}`);
      }
      selectedAgents.push(agent);
    }

    const id = this.generateGroupId();
    const group: TaskGroup = {
      id,
      name: this.generateGroupName(selectedAgents),
      agents: selectedAgents.map((a) => a.id),
      mode: this.getModeForSize(selectedAgents.length),
      status: 'idle',
      tasksCompleted: 0,
      successRate: 1.0,
      createdAt: Date.now(),
    };

    // Mark agents as busy
    for (const agent of selectedAgents) {
      agent.status = 'busy';
      agent.currentGroup = id;
    }

    this.groups.set(id, group);
    return group;
  }

  /**
   * Get group by ID
   */
  public getGroup(id: string): TaskGroup | undefined {
    return this.groups.get(id);
  }

  /**
   * Get all groups
   */
  public getAllGroups(): TaskGroup[] {
    return Array.from(this.groups.values());
  }

  /**
   * Get active groups
   */
  public getActiveGroups(): TaskGroup[] {
    return this.getAllGroups().filter((g) => g.status === 'working' || g.status === 'reviewing');
  }

  /**
   * Assign task to group
   */
  public assignTask(groupId: string, taskId: string): void {
    const group = this.groups.get(groupId);
    if (!group) {
      throw new Error(`Group ${groupId} not found`);
    }

    group.currentTask = taskId;
    group.status = 'working';
  }

  /**
   * Complete task for group
   */
  public completeTask(groupId: string, success: boolean): void {
    const group = this.groups.get(groupId);
    if (!group) {
      throw new Error(`Group ${groupId} not found`);
    }

    group.tasksCompleted++;
    group.currentTask = undefined;
    group.status = 'idle';

    // Update success rate
    const alpha = 0.2;
    group.successRate = alpha * (success ? 1 : 0) + (1 - alpha) * group.successRate;
  }

  /**
   * Dissolve a group and release agents
   */
  public dissolveGroup(groupId: string): void {
    const group = this.groups.get(groupId);
    if (!group) return;

    // Release agents
    for (const agentId of group.agents) {
      const agent = this.agents.get(agentId);
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
  public getGroupAgents(groupId: string): BuiltInAgent[] {
    const group = this.groups.get(groupId);
    if (!group) return [];

    return group.agents
      .map((id) => this.agents.get(id))
      .filter((a): a is BuiltInAgent => a !== undefined);
  }

  /**
   * Get lead agent for a group (first agent)
   */
  public getLeadAgent(groupId: string): BuiltInAgent | undefined {
    const agents = this.getGroupAgents(groupId);
    return agents[0];
  }

  /**
   * Recommend group composition for a task
   */
  public recommendGroup(taskType: CodingTaskType, complexity: TaskComplexity): AgentRole[] {
    const recommended = TASK_AGENT_RECOMMENDATIONS[taskType];
    const mode = COMPLEXITY_GROUP_SIZE[complexity];
    const size = mode === 'solo' ? 1 : mode === 'pair' ? 2 : 3;

    return recommended.slice(0, size);
  }

  /**
   * Select agents for a group
   */
  private selectAgents(roles: AgentRole[], maxSize: number): BuiltInAgent[] {
    const selected: BuiltInAgent[] = [];

    for (const role of roles) {
      if (selected.length >= maxSize) break;

      const agent = this.getAvailableAgentByRole(role);
      if (agent && !selected.includes(agent)) {
        selected.push(agent);
      }
    }

    return selected;
  }

  /**
   * Get available agent by role
   */
  private getAvailableAgentByRole(role: AgentRole): BuiltInAgent | undefined {
    for (const agent of this.agents.values()) {
      if (agent.role === role && agent.status === 'available') {
        return agent;
      }
    }
    return undefined;
  }

  /**
   * Generate group ID
   */
  private generateGroupId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 6);
    return `grp-${timestamp}-${random}`;
  }

  /**
   * Generate group name from agents
   */
  private generateGroupName(agents: BuiltInAgent[]): string {
    if (agents.length === 1) {
      return `Solo-${agents[0].name}`;
    }
    return agents.map((a) => a.name).join('-');
  }

  /**
   * Get collaboration mode for group size
   */
  private getModeForSize(size: number): CollaborationMode {
    if (size === 1) return 'solo';
    if (size === 2) return 'pair';
    return 'trio';
  }
}
