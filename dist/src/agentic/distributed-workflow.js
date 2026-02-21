"use strict";
/**
 * Distributed Agentic Workflow Service
 *
 * Enables cross-branded, tenant-aware workflow execution where tiny LLM adapters
 * can be plugged in and immediately inherit SCBE governance context.
 *
 * @module agentic/distributed-workflow
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_DISTRIBUTED_TEMPLATE = exports.DistributedWorkflowService = void 0;
const types_1 = require("./types");
/**
 * Core service for distributed execution across tiny LLM adapters.
 */
class DistributedWorkflowService {
    brandProfiles = new Map();
    adapters = new Map();
    templates = new Map();
    registerBrandProfile(profile) {
        this.brandProfiles.set(profile.id, profile);
    }
    registerAdapter(adapter) {
        this.adapters.set(adapter.id, adapter);
    }
    registerTemplate(template) {
        this.templates.set(template.id, template);
    }
    getAdaptersByCapability(capability) {
        return Array.from(this.adapters.values()).filter((adapter) => adapter.capabilities.includes(capability));
    }
    static bootstrapAgentsAsProfiles(agents) {
        return agents.map((agent) => ({
            id: `${agent.role}-profile`,
            displayName: `${agent.name} Runtime`,
            voice: 'neutral',
            promptPrefix: `You are ${agent.name}, role=${agent.role}, tongue=${types_1.ROLE_TONGUE_MAP[agent.role]}.`,
            outputTagline: 'Governed by SCBE-AETHERMOORE',
        }));
    }
    async executeWorkflow(request) {
        const profile = this.brandProfiles.get(request.brandProfileId);
        if (!profile) {
            throw new Error(`Unknown brand profile: ${request.brandProfileId}`);
        }
        const template = this.templates.get(request.workflowTemplateId);
        if (!template) {
            throw new Error(`Unknown workflow template: ${request.workflowTemplateId}`);
        }
        const executionId = this.newExecutionId();
        const outputs = [];
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
    selectAdapter(capability) {
        const candidates = this.getAdaptersByCapability(capability);
        if (candidates.length === 0) {
            throw new Error(`No adapters registered for capability: ${capability}`);
        }
        return candidates.sort((a, b) => b.maxContextTokens - a.maxContextTokens)[0];
    }
    buildSystemPrompt(profile, step) {
        return [
            profile.promptPrefix,
            `Brand voice: ${profile.voice}.`,
            `Workflow step: ${step.name} (${step.id}).`,
            `Agent role: ${step.role}.`,
            `Capability: ${step.capability}.`,
            'Comply with SCBE risk governance and produce deterministic, auditable output.',
        ].join(' ');
    }
    decorateOutput(profile, output) {
        if (!profile.outputTagline) {
            return output;
        }
        return `${output}\n\n— ${profile.outputTagline}`;
    }
    renderPrompt(template, userPrompt, previous) {
        const previousOutput = previous.length > 0 ? previous[previous.length - 1].output : 'None';
        return template
            .replaceAll('{{user_prompt}}', userPrompt)
            .replaceAll('{{previous_output}}', previousOutput);
    }
    newExecutionId() {
        return `wf_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    }
}
exports.DistributedWorkflowService = DistributedWorkflowService;
exports.DEFAULT_DISTRIBUTED_TEMPLATE = {
    id: 'distributed-build-and-verify',
    name: 'Distributed Build and Verify',
    description: 'Plan, implement, test, and security-check with tiny LLM workers.',
    steps: [
        {
            id: 'plan',
            name: 'Planning',
            role: 'architect',
            capability: 'planning',
            promptTemplate: 'Create an implementation plan for: {{user_prompt}}. Consider SCBE constraints.',
        },
        {
            id: 'implement',
            name: 'Implementation',
            role: 'coder',
            capability: 'implementation',
            promptTemplate: 'Using this plan: {{previous_output}}, implement core logic for: {{user_prompt}}.',
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
//# sourceMappingURL=distributed-workflow.js.map