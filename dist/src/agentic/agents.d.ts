/**
 * Built-in Agents - 6 specialized coding agents
 *
 * @module agentic/agents
 */
import { AgentRole, BuiltInAgent } from './types';
/**
 * Create the 6 built-in agents
 */
export declare function createBuiltInAgents(provider?: string): BuiltInAgent[];
/**
 * Get agent by role
 */
export declare function getAgentByRole(agents: BuiltInAgent[], role: AgentRole): BuiltInAgent | undefined;
/**
 * Get available agents
 */
export declare function getAvailableAgents(agents: BuiltInAgent[]): BuiltInAgent[];
/**
 * Get agents by specialization
 */
export declare function getAgentsBySpecialization(agents: BuiltInAgent[], spec: string): BuiltInAgent[];
//# sourceMappingURL=agents.d.ts.map