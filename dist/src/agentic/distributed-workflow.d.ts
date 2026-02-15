/**
 * Distributed Agentic Workflow Service
 *
 * Enables cross-branded, tenant-aware workflow execution where tiny LLM adapters
 * can be plugged in and immediately inherit SCBE governance context.
 *
 * @module agentic/distributed-workflow
 */
import { AgentRole, BuiltInAgent } from './types';
export type TinyLLMCapability = 'planning' | 'implementation' | 'analysis' | 'testing' | 'security' | 'deployment';
export interface TinyLLMAdapter {
    id: string;
    provider: string;
    model: string;
    capabilities: TinyLLMCapability[];
    maxContextTokens: number;
    generate(input: TinyLLMInput): Promise<TinyLLMOutput>;
}
export interface TinyLLMInput {
    tenantId: string;
    workflowId: string;
    stepId: string;
    role: AgentRole;
    systemPrompt: string;
    userPrompt: string;
    context: Record<string, unknown>;
}
export interface TinyLLMOutput {
    text: string;
    tokensUsed: number;
    latencyMs: number;
}
export interface BrandProfile {
    id: string;
    displayName: string;
    voice: 'formal' | 'neutral' | 'concise';
    promptPrefix: string;
    outputTagline?: string;
}
export interface WorkflowStep {
    id: string;
    name: string;
    role: AgentRole;
    capability: TinyLLMCapability;
    promptTemplate: string;
}
export interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    steps: WorkflowStep[];
}
export interface WorkflowExecutionRequest {
    tenantId: string;
    brandProfileId: string;
    workflowTemplateId: string;
    userPrompt: string;
    context?: Record<string, unknown>;
}
export interface WorkflowStepResult {
    stepId: string;
    adapterId: string;
    output: string;
    tokensUsed: number;
    latencyMs: number;
}
export interface WorkflowExecutionResult {
    executionId: string;
    workflowTemplateId: string;
    brandProfileId: string;
    outputs: WorkflowStepResult[];
    totalTokens: number;
}
/**
 * Core service for distributed execution across tiny LLM adapters.
 */
export declare class DistributedWorkflowService {
    private brandProfiles;
    private adapters;
    private templates;
    registerBrandProfile(profile: BrandProfile): void;
    registerAdapter(adapter: TinyLLMAdapter): void;
    registerTemplate(template: WorkflowTemplate): void;
    getAdaptersByCapability(capability: TinyLLMCapability): TinyLLMAdapter[];
    static bootstrapAgentsAsProfiles(agents: BuiltInAgent[]): BrandProfile[];
    executeWorkflow(request: WorkflowExecutionRequest): Promise<WorkflowExecutionResult>;
    private selectAdapter;
    private buildSystemPrompt;
    private decorateOutput;
    private renderPrompt;
    private newExecutionId;
}
export declare const DEFAULT_DISTRIBUTED_TEMPLATE: WorkflowTemplate;
//# sourceMappingURL=distributed-workflow.d.ts.map