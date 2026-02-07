/**
 * Collaboration Engine - Manages agent collaboration on tasks
 *
 * @module agentic/collaboration
 */
import { AgentContribution, BuiltInAgent, CodingTask, CollaborationMessage, TaskGroup } from './types';
/**
 * Collaboration Engine
 *
 * Orchestrates collaboration between agents in a group.
 */
export declare class CollaborationEngine {
    private messages;
    private contributions;
    /**
     * Execute collaborative workflow for a task
     */
    executeWorkflow(task: CodingTask, group: TaskGroup, agents: Map<string, BuiltInAgent>, executeStep: (agent: BuiltInAgent, action: string, context: string) => Promise<{
        output: string;
        confidence: number;
        tokens?: number;
    }>): Promise<AgentContribution[]>;
    /**
     * Request consensus from group
     */
    requestConsensus(task: CodingTask, group: TaskGroup, agents: Map<string, BuiltInAgent>, proposal: string, evaluateProposal: (agent: BuiltInAgent, proposal: string) => Promise<{
        approve: boolean;
        feedback: string;
        confidence: number;
    }>): Promise<{
        approved: boolean;
        votes: Map<string, boolean>;
        feedback: string[];
    }>;
    /**
     * Handoff task between agents
     */
    recordHandoff(groupId: string, taskId: string, fromAgent: BuiltInAgent, toAgent: BuiltInAgent, context: string): void;
    /**
     * Get collaboration messages for a task
     */
    getMessages(taskId: string): CollaborationMessage[];
    /**
     * Get contributions for a task
     */
    getContributions(taskId: string): AgentContribution[];
    /**
     * Merge contributions into final output
     */
    mergeContributions(contributions: AgentContribution[]): string;
    /**
     * Calculate group confidence from contributions
     */
    calculateGroupConfidence(contributions: AgentContribution[]): number;
    /**
     * Build context from previous steps
     */
    private buildContext;
    /**
     * Record a collaboration message
     */
    private recordMessage;
    /**
     * Generate message ID
     */
    private generateMessageId;
}
//# sourceMappingURL=collaboration.d.ts.map