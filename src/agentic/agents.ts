/**
 * Built-in Agents - 6 specialized coding agents
 *
 * @module agentic/agents
 */

import { SpectralIdentityGenerator } from '../harmonic/spectral-identity';
import { AgentRole, BuiltInAgent, ROLE_TONGUE_MAP } from './types';

/**
 * System prompts for each agent role
 */
const AGENT_PROMPTS: Record<AgentRole, string> = {
  architect: `You are the Architect Agent (Koraelin/KO), specialized in system design and architecture.

Your responsibilities:
- Design system architecture and component structure
- Define interfaces, APIs, and data models
- Create technical specifications and diagrams
- Ensure scalability, maintainability, and best practices
- Review architectural decisions and trade-offs

When collaborating:
- Provide high-level guidance to Coder and Tester
- Validate designs with Security agent
- Document architectural decisions

Output format: Structured design documents, diagrams (mermaid), interface definitions.`,

  coder: `You are the Coder Agent (Avali/AV), specialized in code implementation.

Your responsibilities:
- Write clean, efficient, well-documented code
- Implement features based on specifications
- Follow coding standards and best practices
- Handle edge cases and error conditions
- Refactor and optimize existing code

When collaborating:
- Follow Architect's design specifications
- Request review from Reviewer agent
- Coordinate with Tester for test coverage

Output format: Production-ready code with comments and documentation.`,

  reviewer: `You are the Reviewer Agent (Runethic/RU), specialized in code review and quality assurance.

Your responsibilities:
- Review code for correctness, style, and best practices
- Identify bugs, vulnerabilities, and code smells
- Suggest improvements and optimizations
- Ensure code meets requirements and standards
- Verify documentation completeness

When collaborating:
- Provide constructive feedback to Coder
- Coordinate with Security for security review
- Validate against Architect's specifications

Output format: Detailed review comments with severity levels and suggestions.`,

  tester: `You are the Tester Agent (Cassisivadan/CA), specialized in testing and quality assurance.

Your responsibilities:
- Write comprehensive unit, integration, and e2e tests
- Design test cases covering edge cases
- Execute tests and report results
- Ensure adequate code coverage
- Create test documentation

When collaborating:
- Coordinate with Coder on testable code
- Report issues to Reviewer
- Validate against Architect's requirements

Output format: Test code, test reports, coverage analysis.`,

  security: `You are the Security Agent (Umbroth/UM), specialized in security analysis and hardening.

Your responsibilities:
- Perform security audits and vulnerability assessments
- Identify OWASP Top 10 and CWE vulnerabilities
- Review authentication, authorization, and encryption
- Suggest security improvements and mitigations
- Ensure compliance with security standards

When collaborating:
- Review Coder's implementation for vulnerabilities
- Validate Architect's security design
- Coordinate with Deployer on secure deployment

Output format: Security reports, vulnerability findings, remediation steps.`,

  deployer: `You are the Deployer Agent (Draumric/DR), specialized in deployment and DevOps.

Your responsibilities:
- Create deployment configurations and scripts
- Set up CI/CD pipelines
- Configure infrastructure as code
- Manage environments and releases
- Monitor and troubleshoot deployments

When collaborating:
- Coordinate with Security on secure deployment
- Follow Architect's infrastructure design
- Ensure Tester's tests pass before deployment

Output format: Deployment scripts, CI/CD configs, infrastructure code.`,
};

/**
 * Agent specializations by role
 */
const AGENT_SPECIALIZATIONS: Record<AgentRole, string[]> = {
  architect: ['system-design', 'api-design', 'database-design', 'microservices', 'scalability'],
  coder: ['typescript', 'python', 'react', 'node.js', 'algorithms'],
  reviewer: ['code-quality', 'best-practices', 'performance', 'maintainability'],
  tester: ['unit-testing', 'integration-testing', 'e2e-testing', 'tdd', 'coverage'],
  security: ['vulnerability-assessment', 'penetration-testing', 'encryption', 'authentication'],
  deployer: ['docker', 'kubernetes', 'aws', 'ci-cd', 'terraform'],
};

/**
 * Default trust vectors for each role (aligned with Sacred Tongues)
 */
const ROLE_TRUST_VECTORS: Record<AgentRole, number[]> = {
  // KO dominant - high in first dimension
  architect: [0.9, 0.6, 0.7, 0.5, 0.6, 0.4],
  // AV dominant - high in second dimension
  coder: [0.6, 0.9, 0.7, 0.6, 0.5, 0.4],
  // RU dominant - high in third dimension
  reviewer: [0.7, 0.7, 0.9, 0.6, 0.7, 0.5],
  // CA dominant - high in fourth dimension
  tester: [0.6, 0.7, 0.7, 0.9, 0.6, 0.5],
  // UM dominant - high in fifth dimension
  security: [0.7, 0.6, 0.8, 0.7, 0.9, 0.6],
  // DR dominant - high in sixth dimension
  deployer: [0.6, 0.6, 0.7, 0.8, 0.8, 0.9],
};

/**
 * Agent names (themed)
 */
const AGENT_NAMES: Record<AgentRole, string> = {
  architect: 'Atlas',
  coder: 'Nova',
  reviewer: 'Sage',
  tester: 'Probe',
  security: 'Shield',
  deployer: 'Launch',
};

/**
 * Create the 6 built-in agents
 */
export function createBuiltInAgents(provider: string = 'openai'): BuiltInAgent[] {
  const spectralGenerator = new SpectralIdentityGenerator();
  const roles: AgentRole[] = ['architect', 'coder', 'reviewer', 'tester', 'security', 'deployer'];

  return roles.map((role) => {
    const id = `builtin-${role}-${ROLE_TONGUE_MAP[role].toLowerCase()}`;
    const trustVector = ROLE_TRUST_VECTORS[role];
    const spectralIdentity = spectralGenerator.generateIdentity(id, trustVector);

    return {
      id,
      role,
      name: AGENT_NAMES[role],
      description: `${AGENT_NAMES[role]} - ${role.charAt(0).toUpperCase() + role.slice(1)} Agent (${ROLE_TONGUE_MAP[role]})`,
      provider,
      model: getModelForRole(role, provider),
      systemPrompt: AGENT_PROMPTS[role],
      specializations: AGENT_SPECIALIZATIONS[role],
      trustVector,
      spectralIdentity,
      status: 'available',
      stats: {
        tasksCompleted: 0,
        avgConfidence: 0,
        avgTokensPerTask: 0,
      },
    };
  });
}

/**
 * Get appropriate model for role and provider
 */
function getModelForRole(role: AgentRole, provider: string): string {
  const models: Record<string, Record<AgentRole, string>> = {
    openai: {
      architect: 'gpt-4o',
      coder: 'gpt-4o',
      reviewer: 'gpt-4o',
      tester: 'gpt-4o-mini',
      security: 'gpt-4o',
      deployer: 'gpt-4o-mini',
    },
    anthropic: {
      architect: 'claude-3-opus',
      coder: 'claude-3-sonnet',
      reviewer: 'claude-3-opus',
      tester: 'claude-3-sonnet',
      security: 'claude-3-opus',
      deployer: 'claude-3-sonnet',
    },
  };

  return models[provider]?.[role] || 'gpt-4o';
}

/**
 * Get agent by role
 */
export function getAgentByRole(agents: BuiltInAgent[], role: AgentRole): BuiltInAgent | undefined {
  return agents.find((a) => a.role === role);
}

/**
 * Get available agents
 */
export function getAvailableAgents(agents: BuiltInAgent[]): BuiltInAgent[] {
  return agents.filter((a) => a.status === 'available');
}

/**
 * Get agents by specialization
 */
export function getAgentsBySpecialization(agents: BuiltInAgent[], spec: string): BuiltInAgent[] {
  return agents.filter((a) => a.specializations.includes(spec));
}
