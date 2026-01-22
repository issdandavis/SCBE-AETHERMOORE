/**
 * Collaboration Engine - Manages agent collaboration on tasks
 *
 * @module agentic/collaboration
 */

import {
  AgentContribution,
  AgentRole,
  BuiltInAgent,
  CodingTask,
  CodingTaskType,
  CollaborationMessage,
  TaskGroup,
} from './types';

/**
 * Collaboration workflow step
 */
interface WorkflowStep {
  agent: AgentRole;
  action: string;
  dependsOn?: string[];
}

/**
 * Collaboration workflows for different task types
 */
const COLLABORATION_WORKFLOWS: Record<CodingTaskType, WorkflowStep[]> = {
  design: [
    { agent: 'architect', action: 'create_design' },
    { agent: 'reviewer', action: 'review_design', dependsOn: ['create_design'] },
    { agent: 'architect', action: 'finalize_design', dependsOn: ['review_design'] },
  ],
  implement: [
    { agent: 'architect', action: 'define_interface' },
    { agent: 'coder', action: 'implement_code', dependsOn: ['define_interface'] },
    { agent: 'reviewer', action: 'review_code', dependsOn: ['implement_code'] },
  ],
  review: [
    { agent: 'reviewer', action: 'initial_review' },
    { agent: 'security', action: 'security_review' },
    { agent: 'reviewer', action: 'final_review', dependsOn: ['initial_review', 'security_review'] },
  ],
  test: [
    { agent: 'tester', action: 'design_tests' },
    { agent: 'coder', action: 'review_testability', dependsOn: ['design_tests'] },
    { agent: 'tester', action: 'implement_tests', dependsOn: ['review_testability'] },
  ],
  security_audit: [
    { agent: 'security', action: 'vulnerability_scan' },
    { agent: 'reviewer', action: 'code_review' },
    { agent: 'security', action: 'final_report', dependsOn: ['vulnerability_scan', 'code_review'] },
  ],
  deploy: [
    { agent: 'deployer', action: 'prepare_deployment' },
    { agent: 'security', action: 'security_check', dependsOn: ['prepare_deployment'] },
    { agent: 'deployer', action: 'execute_deployment', dependsOn: ['security_check'] },
  ],
  refactor: [
    { agent: 'reviewer', action: 'identify_issues' },
    { agent: 'coder', action: 'refactor_code', dependsOn: ['identify_issues'] },
    { agent: 'reviewer', action: 'verify_refactor', dependsOn: ['refactor_code'] },
  ],
  debug: [
    { agent: 'tester', action: 'reproduce_bug' },
    { agent: 'coder', action: 'fix_bug', dependsOn: ['reproduce_bug'] },
    { agent: 'tester', action: 'verify_fix', dependsOn: ['fix_bug'] },
  ],
  document: [
    { agent: 'architect', action: 'outline_docs' },
    { agent: 'coder', action: 'add_code_docs', dependsOn: ['outline_docs'] },
    { agent: 'reviewer', action: 'review_docs', dependsOn: ['add_code_docs'] },
  ],
  optimize: [
    { agent: 'reviewer', action: 'profile_code' },
    { agent: 'coder', action: 'optimize_code', dependsOn: ['profile_code'] },
    { agent: 'tester', action: 'benchmark', dependsOn: ['optimize_code'] },
  ],
};

/**
 * Collaboration Engine
 *
 * Orchestrates collaboration between agents in a group.
 */
export class CollaborationEngine {
  private messages: Map<string, CollaborationMessage[]> = new Map();
  private contributions: Map<string, AgentContribution[]> = new Map();

  /**
   * Execute collaborative workflow for a task
   */
  public async executeWorkflow(
    task: CodingTask,
    group: TaskGroup,
    agents: Map<string, BuiltInAgent>,
    executeStep: (
      agent: BuiltInAgent,
      action: string,
      context: string
    ) => Promise<{ output: string; confidence: number; tokens?: number }>
  ): Promise<AgentContribution[]> {
    const workflow = COLLABORATION_WORKFLOWS[task.type];
    const groupAgents = group.agents
      .map((id) => agents.get(id))
      .filter((a): a is BuiltInAgent => a !== undefined);
    const completedSteps: Map<string, AgentContribution> = new Map();
    const taskContributions: AgentContribution[] = [];

    // Filter workflow to only include steps for agents in the group
    const availableRoles = new Set(groupAgents.map((a) => a.role));
    const applicableSteps = workflow.filter((step) => availableRoles.has(step.agent));

    for (const step of applicableSteps) {
      // Check dependencies
      if (step.dependsOn) {
        const missingDeps = step.dependsOn.filter((dep) => !completedSteps.has(dep));
        if (missingDeps.length > 0) {
          // Skip if dependencies not met (agent not in group)
          continue;
        }
      }

      // Find agent for this step
      const agent = groupAgents.find((a) => a.role === step.agent);
      if (!agent) continue;

      // Build context from previous steps
      let context = this.buildContext(task, completedSteps, step.dependsOn);

      // Execute step
      const result = await executeStep(agent, step.action, context);

      const contribution: AgentContribution = {
        agentId: agent.id,
        role: agent.role,
        action: step.action,
        output: result.output,
        confidence: result.confidence,
        timestamp: Date.now(),
        tokensUsed: result.tokens,
      };

      completedSteps.set(step.action, contribution);
      taskContributions.push(contribution);

      // Record collaboration message
      this.recordMessage({
        id: this.generateMessageId(),
        groupId: group.id,
        taskId: task.id,
        fromAgent: agent.id,
        type: 'response',
        content: result.output,
        metadata: { action: step.action, confidence: result.confidence },
        timestamp: Date.now(),
      });
    }

    // Store contributions
    this.contributions.set(task.id, taskContributions);

    return taskContributions;
  }

  /**
   * Request consensus from group
   */
  public async requestConsensus(
    task: CodingTask,
    group: TaskGroup,
    agents: Map<string, BuiltInAgent>,
    proposal: string,
    evaluateProposal: (
      agent: BuiltInAgent,
      proposal: string
    ) => Promise<{ approve: boolean; feedback: string; confidence: number }>
  ): Promise<{ approved: boolean; votes: Map<string, boolean>; feedback: string[] }> {
    const groupAgents = group.agents
      .map((id) => agents.get(id))
      .filter((a): a is BuiltInAgent => a !== undefined);
    const votes = new Map<string, boolean>();
    const feedback: string[] = [];

    for (const agent of groupAgents) {
      const result = await evaluateProposal(agent, proposal);
      votes.set(agent.id, result.approve);
      if (result.feedback) {
        feedback.push(`${agent.name}: ${result.feedback}`);
      }

      // Record vote message
      this.recordMessage({
        id: this.generateMessageId(),
        groupId: group.id,
        taskId: task.id,
        fromAgent: agent.id,
        type: 'consensus',
        content: result.approve ? 'APPROVE' : 'REJECT',
        metadata: { feedback: result.feedback, confidence: result.confidence },
        timestamp: Date.now(),
      });
    }

    // Majority vote
    const approvals = Array.from(votes.values()).filter((v) => v).length;
    const approved = approvals > groupAgents.length / 2;

    return { approved, votes, feedback };
  }

  /**
   * Handoff task between agents
   */
  public recordHandoff(
    groupId: string,
    taskId: string,
    fromAgent: BuiltInAgent,
    toAgent: BuiltInAgent,
    context: string
  ): void {
    this.recordMessage({
      id: this.generateMessageId(),
      groupId,
      taskId,
      fromAgent: fromAgent.id,
      toAgent: toAgent.id,
      type: 'handoff',
      content: context,
      timestamp: Date.now(),
    });
  }

  /**
   * Get collaboration messages for a task
   */
  public getMessages(taskId: string): CollaborationMessage[] {
    return this.messages.get(taskId) || [];
  }

  /**
   * Get contributions for a task
   */
  public getContributions(taskId: string): AgentContribution[] {
    return this.contributions.get(taskId) || [];
  }

  /**
   * Merge contributions into final output
   */
  public mergeContributions(contributions: AgentContribution[]): string {
    if (contributions.length === 0) return '';
    if (contributions.length === 1) return contributions[0].output;

    // Sort by timestamp
    const sorted = [...contributions].sort((a, b) => a.timestamp - b.timestamp);

    // Build merged output
    const sections: string[] = [];
    for (const contrib of sorted) {
      sections.push(`## ${contrib.role.toUpperCase()} - ${contrib.action}\n\n${contrib.output}`);
    }

    return sections.join('\n\n---\n\n');
  }

  /**
   * Calculate group confidence from contributions
   */
  public calculateGroupConfidence(contributions: AgentContribution[]): number {
    if (contributions.length === 0) return 0;

    const totalConfidence = contributions.reduce((sum, c) => sum + c.confidence, 0);
    return totalConfidence / contributions.length;
  }

  /**
   * Build context from previous steps
   */
  private buildContext(
    task: CodingTask,
    completedSteps: Map<string, AgentContribution>,
    dependencies?: string[]
  ): string {
    const parts: string[] = [];

    // Add task context
    parts.push(`Task: ${task.title}`);
    parts.push(`Description: ${task.description}`);

    if (task.context.code) {
      parts.push(`\nCode:\n\`\`\`\n${task.context.code}\n\`\`\``);
    }

    if (task.context.requirements) {
      parts.push(`\nRequirements: ${task.context.requirements}`);
    }

    // Add outputs from dependencies
    if (dependencies) {
      for (const dep of dependencies) {
        const contrib = completedSteps.get(dep);
        if (contrib) {
          parts.push(`\n--- Previous: ${dep} (by ${contrib.role}) ---\n${contrib.output}`);
        }
      }
    }

    return parts.join('\n');
  }

  /**
   * Record a collaboration message
   */
  private recordMessage(message: CollaborationMessage): void {
    const messages = this.messages.get(message.taskId) || [];
    messages.push(message);
    this.messages.set(message.taskId, messages);
  }

  /**
   * Generate message ID
   */
  private generateMessageId(): string {
    return `msg-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
  }
}
