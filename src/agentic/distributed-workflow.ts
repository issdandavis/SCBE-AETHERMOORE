/**
 * Distributed Agentic Workflow Service
 *
 * Enables cross-branded, tenant-aware workflow execution where tiny LLM adapters
 * can be plugged in and immediately inherit SCBE governance context.
 *
 * @module agentic/distributed-workflow
 */

import { AgentRole, BuiltInAgent, ROLE_TONGUE_MAP } from './types';

export type TinyLLMCapability =
  | 'planning'
  | 'implementation'
  | 'analysis'
  | 'testing'
  | 'security'
  | 'deployment';

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
export class DistributedWorkflowService {
  private brandProfiles = new Map<string, BrandProfile>();
  private adapters = new Map<string, TinyLLMAdapter>();
  private templates = new Map<string, WorkflowTemplate>();

  public registerBrandProfile(profile: BrandProfile): void {
    this.brandProfiles.set(profile.id, profile);
  }

  public registerAdapter(adapter: TinyLLMAdapter): void {
    this.adapters.set(adapter.id, adapter);
  }

  public registerTemplate(template: WorkflowTemplate): void {
    this.templates.set(template.id, template);
  }

  public getAdaptersByCapability(capability: TinyLLMCapability): TinyLLMAdapter[] {
    return Array.from(this.adapters.values()).filter((adapter) =>
      adapter.capabilities.includes(capability)
    );
  }

  public static bootstrapAgentsAsProfiles(agents: BuiltInAgent[]): BrandProfile[] {
    return agents.map((agent) => ({
      id: `${agent.role}-profile`,
      displayName: `${agent.name} Runtime`,
      voice: 'neutral',
      promptPrefix: `You are ${agent.name}, role=${agent.role}, tongue=${ROLE_TONGUE_MAP[agent.role]}.`,
      outputTagline: 'Governed by SCBE-AETHERMOORE',
    }));
  }

  public async executeWorkflow(request: WorkflowExecutionRequest): Promise<WorkflowExecutionResult> {
    const profile = this.brandProfiles.get(request.brandProfileId);
    if (!profile) {
      throw new Error(`Unknown brand profile: ${request.brandProfileId}`);
    }

    const template = this.templates.get(request.workflowTemplateId);
    if (!template) {
      throw new Error(`Unknown workflow template: ${request.workflowTemplateId}`);
    }

    const executionId = this.newExecutionId();
    const outputs: WorkflowStepResult[] = [];

    for (const step of template.steps) {
      const adapter = this.selectAdapter(step.capability);
      const stepPrompt = this.renderPrompt(step.promptTemplate, request.userPrompt, outputs);
      const systemPrompt = this.buildSystemPrompt(profile, step);

      const response = await adapter.generate({
        tenantId: request.tenantId,
        workflowId: template.id,
        stepId: step.id,
        role: step.role,
        systemPrompt,
        userPrompt: stepPrompt,
        context: request.context || {},
      });

      outputs.push({
        stepId: step.id,
        adapterId: adapter.id,
        output: this.decorateOutput(profile, response.text),
        tokensUsed: response.tokensUsed,
        latencyMs: response.latencyMs,
      });
    }

    const totalTokens = outputs.reduce((sum, out) => sum + out.tokensUsed, 0);

    return {
      executionId,
      workflowTemplateId: template.id,
      brandProfileId: profile.id,
      outputs,
      totalTokens,
    };
  }

  private selectAdapter(capability: TinyLLMCapability): TinyLLMAdapter {
    const candidates = this.getAdaptersByCapability(capability);
    if (candidates.length === 0) {
      throw new Error(`No adapters registered for capability: ${capability}`);
    }

    return candidates.sort((a, b) => b.maxContextTokens - a.maxContextTokens)[0];
  }

  private buildSystemPrompt(profile: BrandProfile, step: WorkflowStep): string {
    return [
      profile.promptPrefix,
      `Brand voice: ${profile.voice}.`,
      `Workflow step: ${step.name} (${step.id}).`,
      `Agent role: ${step.role}.`,
      `Capability: ${step.capability}.`,
      'Comply with SCBE risk governance and produce deterministic, auditable output.',
    ].join(' ');
  }

  private decorateOutput(profile: BrandProfile, output: string): string {
    if (!profile.outputTagline) {
      return output;
    }

    return `${output}\n\n— ${profile.outputTagline}`;
  }

  private renderPrompt(
    template: string,
    userPrompt: string,
    previous: WorkflowStepResult[]
  ): string {
    const previousOutput = previous.length > 0 ? previous[previous.length - 1].output : 'None';

    return template
      .replaceAll('{{user_prompt}}', userPrompt)
      .replaceAll('{{previous_output}}', previousOutput);
  }

  private newExecutionId(): string {
    return `wf_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  }
}

export const DEFAULT_DISTRIBUTED_TEMPLATE: WorkflowTemplate = {
  id: 'distributed-build-and-verify',
  name: 'Distributed Build and Verify',
  description: 'Plan, implement, test, and security-check with tiny LLM workers.',
  steps: [
    {
      id: 'plan',
      name: 'Planning',
      role: 'architect',
      capability: 'planning',
      promptTemplate:
        'Create an implementation plan for: {{user_prompt}}. Consider SCBE constraints.',
    },
    {
      id: 'implement',
      name: 'Implementation',
      role: 'coder',
      capability: 'implementation',
      promptTemplate:
        'Using this plan: {{previous_output}}, implement core logic for: {{user_prompt}}.',
    },
    {
      id: 'test',
      name: 'Testing',
      role: 'tester',
      capability: 'testing',
      promptTemplate: 'Generate tests for implementation output: {{previous_output}}.',
    },
    {
      id: 'security',
      name: 'Security Review',
      role: 'security',
      capability: 'security',
      promptTemplate: 'Review for vulnerabilities: {{previous_output}}.',
    },
  ],
};
