import { describe, expect, it } from 'vitest';
import {
  DEFAULT_DISTRIBUTED_TEMPLATE,
  DistributedWorkflowService,
  TinyLLMAdapter,
} from '../../src/agentic/distributed-workflow';
import { createBuiltInAgents } from '../../src/agentic/agents';

function makeAdapter(
  id: string,
  capability: TinyLLMAdapter['capabilities'][number],
  maxContextTokens = 4096
): TinyLLMAdapter {
  return {
    id,
    provider: 'local',
    model: 'tiny-llm',
    capabilities: [capability],
    maxContextTokens,
    async generate(input) {
      return {
        text: `[${id}] ${input.stepId}: ${input.userPrompt.slice(0, 40)}`,
        tokensUsed: 42,
        latencyMs: 10,
      };
    },
  };
}

describe('DistributedWorkflowService', () => {
  it('executes distributed template end-to-end with tiny adapters', async () => {
    const svc = new DistributedWorkflowService();

    svc.registerBrandProfile({
      id: 'acme',
      displayName: 'Acme Labs',
      voice: 'formal',
      promptPrefix: 'You represent Acme Labs engineering.',
      outputTagline: 'Acme Secure Runtime',
    });

    svc.registerTemplate(DEFAULT_DISTRIBUTED_TEMPLATE);
    svc.registerAdapter(makeAdapter('plan-adapter', 'planning'));
    svc.registerAdapter(makeAdapter('impl-adapter', 'implementation'));
    svc.registerAdapter(makeAdapter('test-adapter', 'testing'));
    svc.registerAdapter(makeAdapter('sec-adapter', 'security'));

    const result = await svc.executeWorkflow({
      tenantId: 'tenant-1',
      brandProfileId: 'acme',
      workflowTemplateId: DEFAULT_DISTRIBUTED_TEMPLATE.id,
      userPrompt: 'build a secure API endpoint for invoice creation',
    });

    expect(result.outputs).toHaveLength(4);
    expect(result.totalTokens).toBe(168);
    expect(result.outputs[0].adapterId).toBe('plan-adapter');
    expect(result.outputs[3].output).toContain('Acme Secure Runtime');
  });

  it('prefers higher-context adapter when multiple satisfy capability', async () => {
    const svc = new DistributedWorkflowService();

    svc.registerBrandProfile({
      id: 'brand',
      displayName: 'Brand',
      voice: 'neutral',
      promptPrefix: 'Brand prompt',
    });

    svc.registerTemplate({
      id: 'single-step',
      name: 'Single',
      description: 'single step test',
      steps: [
        {
          id: 'plan',
          name: 'Plan',
          role: 'architect',
          capability: 'planning',
          promptTemplate: '{{user_prompt}}',
        },
      ],
    });

    svc.registerAdapter(makeAdapter('small-planner', 'planning', 1024));
    svc.registerAdapter(makeAdapter('large-planner', 'planning', 8192));

    const result = await svc.executeWorkflow({
      tenantId: 't',
      brandProfileId: 'brand',
      workflowTemplateId: 'single-step',
      userPrompt: 'plan this',
    });

    expect(result.outputs[0].adapterId).toBe('large-planner');
  });

  it('throws clear error when capability adapter is missing', async () => {
    const svc = new DistributedWorkflowService();

    svc.registerBrandProfile({
      id: 'brand',
      displayName: 'Brand',
      voice: 'neutral',
      promptPrefix: 'Brand prompt',
    });

    svc.registerTemplate(DEFAULT_DISTRIBUTED_TEMPLATE);

    await expect(
      svc.executeWorkflow({
        tenantId: 'tenant',
        brandProfileId: 'brand',
        workflowTemplateId: DEFAULT_DISTRIBUTED_TEMPLATE.id,
        userPrompt: 'missing adapters should fail',
      })
    ).rejects.toThrow('No adapters registered for capability: planning');
  });

  it('can bootstrap cross-brand profiles from built-in agents', () => {
    const agents = createBuiltInAgents('openai');
    const profiles = DistributedWorkflowService.bootstrapAgentsAsProfiles(agents);

    expect(profiles).toHaveLength(6);
    expect(profiles[0].promptPrefix).toContain('tongue=');
    expect(profiles[0].outputTagline).toBe('Governed by SCBE-AETHERMOORE');
  });
});
