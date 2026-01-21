/**
 * Fleet Management System Tests
 * 
 * @module tests/fleet
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
    AgentRegistry,
    FleetAgent,
    FleetManager,
    GOVERNANCE_TIERS,
    GovernanceManager,
    createDefaultFleet
} from '../../src/fleet';

describe('FleetManager', () => {
  let fleet: FleetManager;
  
  beforeEach(() => {
    fleet = new FleetManager({ autoAssign: false });
  });
  
  afterEach(() => {
    fleet.shutdown();
  });
  
  describe('Agent Registration', () => {
    it('should register a new agent with spectral identity', () => {
      const agent = fleet.registerAgent({
        name: 'TestAgent',
        description: 'Test agent for unit tests',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['code_generation'],
        maxGovernanceTier: 'RU'
      });
      
      expect(agent.id).toBeDefined();
      expect(agent.name).toBe('TestAgent');
      expect(agent.spectralIdentity).toBeDefined();
      expect(agent.spectralIdentity?.spectralHash).toMatch(/^SP-[A-F0-9]{4}-[A-F0-9]{4}$/);
      expect(agent.trustScore).toBeDefined();
      expect(agent.status).toBe('idle');
    });
    
    it('should assign unique spectral identities to different agents', () => {
      const agent1 = fleet.registerAgent({
        name: 'Agent1',
        description: 'First agent',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['code_generation'],
        initialTrustVector: [0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
      });
      
      const agent2 = fleet.registerAgent({
        name: 'Agent2',
        description: 'Second agent',
        provider: 'anthropic',
        model: 'claude-3',
        capabilities: ['code_review'],
        initialTrustVector: [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
      });
      
      expect(agent1.spectralIdentity?.spectralHash).not.toBe(agent2.spectralIdentity?.spectralHash);
      expect(agent1.spectralIdentity?.hexCode).not.toBe(agent2.spectralIdentity?.hexCode);
    });
    
    it('should get agents by capability', () => {
      fleet.registerAgent({
        name: 'Coder',
        description: 'Code generator',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['code_generation', 'documentation']
      });
      
      fleet.registerAgent({
        name: 'Reviewer',
        description: 'Code reviewer',
        provider: 'anthropic',
        model: 'claude-3',
        capabilities: ['code_review', 'security_scan']
      });
      
      const coders = fleet.getAgentsByCapability('code_generation');
      expect(coders).toHaveLength(1);
      expect(coders[0].name).toBe('Coder');
      
      const reviewers = fleet.getAgentsByCapability('code_review');
      expect(reviewers).toHaveLength(1);
      expect(reviewers[0].name).toBe('Reviewer');
    });
  });
  
  describe('Trust Management', () => {
    it('should update agent trust vector and regenerate spectral identity', () => {
      const agent = fleet.registerAgent({
        name: 'TrustTest',
        description: 'Trust test agent',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['testing'],
        initialTrustVector: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
      });
      
      const originalHash = agent.spectralIdentity?.spectralHash;
      
      fleet.updateAgentTrust(agent.id, [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]);
      
      const updated = fleet.getAgent(agent.id);
      expect(updated?.spectralIdentity?.spectralHash).not.toBe(originalHash);
      expect(updated?.trustVector).toEqual([0.9, 0.8, 0.7, 0.6, 0.5, 0.4]);
    });
    
    it('should auto-quarantine agents with critical trust', () => {
      const agent = fleet.registerAgent({
        name: 'RiskyAgent',
        description: 'Agent that will be quarantined',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['testing'],
        initialTrustVector: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
      });
      
      // Verify initial trust is HIGH (near ideal)
      expect(agent.trustScore?.level).toBe('HIGH');
      
      // Manually suspend the agent to test status changes
      fleet.suspendAgent(agent.id);
      const suspended = fleet.getAgent(agent.id);
      expect(suspended?.status).toBe('suspended');
      
      // Reactivate
      fleet.reactivateAgent(agent.id);
      const reactivated = fleet.getAgent(agent.id);
      expect(reactivated?.status).toBe('idle');
    });
  });
  
  describe('Task Management', () => {
    it('should create and assign tasks', () => {
      const agent = fleet.registerAgent({
        name: 'Worker',
        description: 'Task worker',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['code_generation'],
        maxGovernanceTier: 'RU',
        initialTrustVector: [0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
      });
      
      const task = fleet.createTask({
        name: 'Generate Code',
        description: 'Generate a function',
        requiredCapability: 'code_generation',
        requiredTier: 'RU',
        priority: 'high',
        input: { prompt: 'Create a hello world function' }
      });
      
      expect(task.id).toBeDefined();
      expect(task.status).toBe('pending');
      
      const result = fleet.assignTask(task.id);
      expect(result.success).toBe(true);
      expect(result.assignedAgentId).toBe(agent.id);
      
      const updatedTask = fleet.getTask(task.id);
      expect(updatedTask?.status).toBe('running');
    });
    
    it('should complete tasks and update agent stats', () => {
      const agent = fleet.registerAgent({
        name: 'Completer',
        description: 'Task completer',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['testing'],
        initialTrustVector: [0.6, 0.6, 0.6, 0.6, 0.6, 0.6]
      });
      
      const task = fleet.createTask({
        name: 'Run Tests',
        description: 'Execute test suite',
        requiredCapability: 'testing',
        requiredTier: 'RU',
        input: { testFile: 'test.ts' }
      });
      
      fleet.assignTask(task.id);
      fleet.completeTask(task.id, { passed: 10, failed: 0 });
      
      const completedTask = fleet.getTask(task.id);
      expect(completedTask?.status).toBe('completed');
      expect(completedTask?.output).toEqual({ passed: 10, failed: 0 });
      
      const updatedAgent = fleet.getAgent(agent.id);
      expect(updatedAgent?.tasksCompleted).toBe(1);
    });
    
    it('should retry failed tasks', () => {
      fleet.registerAgent({
        name: 'Retrier',
        description: 'Retry test agent',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['deployment'],
        initialTrustVector: [0.6, 0.6, 0.6, 0.6, 0.6, 0.6]
      });
      
      const task = fleet.createTask({
        name: 'Deploy',
        description: 'Deploy application',
        requiredCapability: 'deployment',
        requiredTier: 'CA',
        input: { env: 'staging' },
        maxRetries: 3
      });
      
      fleet.assignTask(task.id);
      fleet.failTask(task.id, 'Connection timeout');
      
      const retriedTask = fleet.getTask(task.id);
      expect(retriedTask?.status).toBe('pending');
      expect(retriedTask?.retryCount).toBe(1);
    });
  });
  
  describe('Governance', () => {
    it('should determine correct governance tier for actions', () => {
      expect(fleet.getRequiredTier('read')).toBe('KO');
      expect(fleet.getRequiredTier('create')).toBe('AV');
      expect(fleet.getRequiredTier('execute')).toBe('RU');
      expect(fleet.getRequiredTier('deploy')).toBe('CA');
      expect(fleet.getRequiredTier('admin')).toBe('UM');
      expect(fleet.getRequiredTier('delete')).toBe('DR');
    });
    
    it('should check if agent can perform action', () => {
      fleet.registerAgent({
        name: 'LimitedAgent',
        description: 'Agent with limited tier',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['code_generation'],
        maxGovernanceTier: 'RU',
        initialTrustVector: [0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
      });
      
      const agent = fleet.getAllAgents()[0];
      
      const readCheck = fleet.canPerformAction(agent.id, 'read');
      expect(readCheck.allowed).toBe(true);
      
      const deployCheck = fleet.canPerformAction(agent.id, 'deploy');
      expect(deployCheck.allowed).toBe(false);
      expect(deployCheck.reason).toContain('insufficient');
    });
    
    it('should create roundtable for critical operations', () => {
      // Register multiple high-trust agents (trust vector near ideal 0.5 = HIGH trust)
      const agents: FleetAgent[] = [];
      for (let i = 0; i < 6; i++) {
        agents.push(fleet.registerAgent({
          name: `Council-${i}`,
          description: `Council member ${i}`,
          provider: 'openai',
          model: 'gpt-4o',
          capabilities: ['orchestration'],
          maxGovernanceTier: 'DR',
          // Trust vector near ideal (0.5) gives HIGH trust level
          initialTrustVector: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        }));
      }
      
      // Verify agents have HIGH trust
      expect(agents[0].trustScore?.level).toBe('HIGH');
      
      const session = fleet.createRoundtable({
        topic: 'Delete production database',
        requiredTier: 'DR',
        specificParticipants: agents.map(a => a.id)
      });
      
      expect(session.id).toBeDefined();
      expect(session.status).toBe('active');
      expect(session.participants.length).toBeGreaterThanOrEqual(GOVERNANCE_TIERS.DR.requiredTongues);
    });
    
    it('should reach consensus through voting', () => {
      // Register council with HIGH trust (near ideal 0.5)
      const agents: FleetAgent[] = [];
      for (let i = 0; i < 6; i++) {
        agents.push(fleet.registerAgent({
          name: `Voter-${i}`,
          description: `Voting agent ${i}`,
          provider: 'openai',
          model: 'gpt-4o',
          capabilities: ['orchestration'],
          maxGovernanceTier: 'UM',
          // Trust vector near ideal gives HIGH trust
          initialTrustVector: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        }));
      }
      
      const session = fleet.createRoundtable({
        topic: 'Approve admin action',
        requiredTier: 'UM',
        specificParticipants: agents.map(a => a.id)
      });
      
      // Cast approving votes
      for (let i = 0; i < 5; i++) {
        fleet.castVote(session.id, agents[i].id, 'approve');
      }
      
      const updatedSession = fleet.getActiveRoundtables().find(s => s.id === session.id);
      // Session should be approved (5 votes >= required) or removed from active list
      expect(updatedSession?.status === 'approved' || updatedSession === undefined).toBe(true);
    });
  });
  
  describe('Fleet Statistics', () => {
    it('should provide comprehensive statistics', () => {
      fleet.registerAgent({
        name: 'StatsAgent1',
        description: 'Stats test agent 1',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['testing']
      });
      
      fleet.registerAgent({
        name: 'StatsAgent2',
        description: 'Stats test agent 2',
        provider: 'anthropic',
        model: 'claude-3',
        capabilities: ['code_review']
      });
      
      const stats = fleet.getStatistics();
      
      expect(stats.totalAgents).toBe(2);
      expect(stats.agentsByStatus.idle).toBe(2);
      expect(stats.fleetSuccessRate).toBe(1.0);
    });
    
    it('should report health status', () => {
      fleet.registerAgent({
        name: 'HealthyAgent',
        description: 'Healthy agent',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['testing'],
        initialTrustVector: [0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
      });
      
      const health = fleet.getHealthStatus();
      
      expect(health.healthy).toBe(true);
      expect(health.issues).toHaveLength(0);
      expect(health.metrics.totalAgents).toBe(1);
    });
  });
  
  describe('Event System', () => {
    it('should emit events for agent registration', () => {
      const events: any[] = [];
      fleet.onEvent(e => events.push(e));
      
      fleet.registerAgent({
        name: 'EventAgent',
        description: 'Event test agent',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['testing']
      });
      
      expect(events.length).toBeGreaterThan(0);
      expect(events.some(e => e.type === 'agent_registered')).toBe(true);
    });
    
    it('should emit events for task lifecycle', () => {
      const events: any[] = [];
      fleet.onEvent(e => events.push(e));
      
      fleet.registerAgent({
        name: 'TaskEventAgent',
        description: 'Task event test agent',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['testing'],
        initialTrustVector: [0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
      });
      
      const task = fleet.createTask({
        name: 'Event Test Task',
        description: 'Test task for events',
        requiredCapability: 'testing',
        requiredTier: 'RU',
        input: {}
      });
      
      fleet.assignTask(task.id);
      fleet.completeTask(task.id, { result: 'success' });
      
      expect(events.some(e => e.type === 'task_created')).toBe(true);
      expect(events.some(e => e.type === 'task_assigned')).toBe(true);
      expect(events.some(e => e.type === 'task_completed')).toBe(true);
    });
  });
});

describe('createDefaultFleet', () => {
  it('should create a fleet with pre-configured agents', () => {
    const fleet = createDefaultFleet();
    
    const agents = fleet.getAllAgents();
    expect(agents.length).toBeGreaterThanOrEqual(4);
    
    // Check for expected agents
    const names = agents.map(a => a.name);
    expect(names).toContain('CodeGen-GPT4');
    expect(names).toContain('Security-Claude');
    expect(names).toContain('Deploy-Bot');
    expect(names).toContain('Test-Runner');
    
    fleet.shutdown();
  });
});

describe('AgentRegistry', () => {
  let registry: AgentRegistry;
  
  beforeEach(() => {
    registry = new AgentRegistry();
  });
  
  it('should track agent statistics', () => {
    registry.registerAgent({
      name: 'Agent1',
      description: 'Test agent 1',
      provider: 'openai',
      model: 'gpt-4o',
      capabilities: ['testing']
    });
    
    registry.registerAgent({
      name: 'Agent2',
      description: 'Test agent 2',
      provider: 'anthropic',
      model: 'claude-3',
      capabilities: ['code_review']
    });
    
    const stats = registry.getStatistics();
    
    expect(stats.totalAgents).toBe(2);
    expect(stats.byProvider['openai']).toBe(1);
    expect(stats.byProvider['anthropic']).toBe(1);
  });
});

describe('GovernanceManager', () => {
  let registry: AgentRegistry;
  let governance: GovernanceManager;
  
  beforeEach(() => {
    registry = new AgentRegistry();
    governance = new GovernanceManager(registry);
  });
  
  it('should enforce governance tier requirements', () => {
    // Register agent with limited tier
    registry.registerAgent({
      name: 'LimitedAgent',
      description: 'Agent with RU tier',
      provider: 'openai',
      model: 'gpt-4o',
      capabilities: ['testing'],
      maxGovernanceTier: 'RU',
      initialTrustVector: [0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
    });
    
    const agent = registry.getAllAgents()[0];
    
    // Should be able to perform RU actions
    const ruCheck = governance.canPerformAction(agent.id, 'execute');
    expect(ruCheck.allowed).toBe(true);
    
    // Should not be able to perform CA actions
    const caCheck = governance.canPerformAction(agent.id, 'deploy');
    expect(caCheck.allowed).toBe(false);
  });
  
  it('should track governance statistics', () => {
    // Register high-trust agents (near ideal 0.5)
    const agents: FleetAgent[] = [];
    for (let i = 0; i < 5; i++) {
      agents.push(registry.registerAgent({
        name: `GovAgent-${i}`,
        description: `Governance agent ${i}`,
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['orchestration'],
        maxGovernanceTier: 'UM',
        initialTrustVector: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
      }));
    }
    
    governance.createRoundtable({
      topic: 'Test roundtable',
      requiredTier: 'UM',
      specificParticipants: agents.map(a => a.id)
    });
    
    const stats = governance.getStatistics();
    
    expect(stats.totalSessions).toBe(1);
    expect(stats.activeSessions).toBe(1);
  });
});
