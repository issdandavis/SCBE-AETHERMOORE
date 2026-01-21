/**
 * Agentic Coder Platform Tests
 * 
 * @module tests/agentic
 */

import { beforeEach, describe, expect, it } from 'vitest';
import {
    AgentRole,
    AgenticCoderPlatform,
    BuiltInAgent,
    CollaborationEngine,
    ROLE_TONGUE_MAP,
    TASK_AGENT_RECOMMENDATIONS,
    TaskGroupManager,
    createAgenticPlatform,
    createBuiltInAgents
} from '../../src/agentic';

describe('AgenticCoderPlatform', () => {
  let platform: AgenticCoderPlatform;
  
  beforeEach(() => {
    platform = new AgenticCoderPlatform();
  });
  
  describe('Built-in Agents', () => {
    it('should have 6 built-in agents', () => {
      const agents = platform.getAgents();
      expect(agents).toHaveLength(6);
    });
    
    it('should have all required roles', () => {
      const roles: AgentRole[] = ['architect', 'coder', 'reviewer', 'tester', 'security', 'deployer'];
      
      for (const role of roles) {
        const agent = platform.getAgentByRole(role);
        expect(agent).toBeDefined();
        expect(agent?.role).toBe(role);
      }
    });
    
    it('should have unique spectral identities', () => {
      const agents = platform.getAgents();
      const hashes = new Set(agents.map(a => a.spectralIdentity?.spectralHash));
      expect(hashes.size).toBe(6);
    });
    
    it('should have Sacred Tongue aligned trust vectors', () => {
      const agents = platform.getAgents();
      
      for (const agent of agents) {
        expect(agent.trustVector).toHaveLength(6);
        
        // Each agent should have highest trust in their aligned dimension
        const tongue = ROLE_TONGUE_MAP[agent.role];
        const tongueIndex = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'].indexOf(tongue);
        
        // The aligned dimension should be high (>= 0.8)
        expect(agent.trustVector[tongueIndex]).toBeGreaterThanOrEqual(0.8);
      }
    });
    
    it('should have system prompts for each agent', () => {
      const agents = platform.getAgents();
      
      for (const agent of agents) {
        expect(agent.systemPrompt).toBeDefined();
        expect(agent.systemPrompt.length).toBeGreaterThan(100);
      }
    });
  });
  
  describe('Task Creation', () => {
    it('should create a coding task', () => {
      const task = platform.createTask({
        type: 'implement',
        title: 'Create User API',
        description: 'Implement a REST API for user management',
        language: 'typescript'
      });
      
      expect(task.id).toBeDefined();
      expect(task.type).toBe('implement');
      expect(task.status).toBe('pending');
      expect(task.language).toBe('typescript');
    });
    
    it('should infer complexity from description length', () => {
      const simpleTask = platform.createTask({
        type: 'implement',
        title: 'Simple',
        description: 'Short task'
      });
      expect(simpleTask.complexity).toBe('simple');
      
      const complexTask = platform.createTask({
        type: 'implement',
        title: 'Complex',
        description: 'A'.repeat(600),
        constraints: ['Must be fast', 'Must be secure']
      });
      expect(complexTask.complexity).toBe('complex');
    });
    
    it('should set expected output based on task type', () => {
      const implementTask = platform.createTask({
        type: 'implement',
        title: 'Code',
        description: 'Write code'
      });
      expect(implementTask.expectedOutput).toBe('code');
      
      const reviewTask = platform.createTask({
        type: 'review',
        title: 'Review',
        description: 'Review code'
      });
      expect(reviewTask.expectedOutput).toBe('review');
      
      const testTask = platform.createTask({
        type: 'test',
        title: 'Test',
        description: 'Write tests'
      });
      expect(testTask.expectedOutput).toBe('tests');
    });
  });
  
  describe('Group Management', () => {
    it('should create a group for a task', () => {
      const task = platform.createTask({
        type: 'implement',
        title: 'Test Task',
        description: 'Test description'
      });
      
      const group = platform.createGroupForTask(task.id);
      
      expect(group.id).toBeDefined();
      expect(group.agents.length).toBeGreaterThanOrEqual(1);
      expect(group.agents.length).toBeLessThanOrEqual(3);
      expect(group.currentTask).toBe(task.id);
    });
    
    it('should create custom group with specific agents', () => {
      const group = platform.createCustomGroup(['architect', 'coder']);
      
      expect(group.agents).toHaveLength(2);
      expect(group.mode).toBe('pair');
    });
    
    it('should limit group size to 3 agents', () => {
      expect(() => {
        platform.createCustomGroup(['architect', 'coder', 'reviewer', 'tester']);
      }).toThrow();
    });
    
    it('should mark agents as busy when in a group', () => {
      const group = platform.createCustomGroup(['architect']);
      const architect = platform.getAgentByRole('architect');
      
      expect(architect?.status).toBe('busy');
      expect(architect?.currentGroup).toBe(group.id);
    });
    
    it('should release agents when group is dissolved', () => {
      const group = platform.createCustomGroup(['architect']);
      platform.dissolveGroup(group.id);
      
      const architect = platform.getAgentByRole('architect');
      expect(architect?.status).toBe('available');
      expect(architect?.currentGroup).toBeUndefined();
    });
  });
  
  describe('Task Recommendations', () => {
    it('should recommend appropriate agents for task types', () => {
      expect(TASK_AGENT_RECOMMENDATIONS.design).toContain('architect');
      expect(TASK_AGENT_RECOMMENDATIONS.implement).toContain('coder');
      expect(TASK_AGENT_RECOMMENDATIONS.review).toContain('reviewer');
      expect(TASK_AGENT_RECOMMENDATIONS.test).toContain('tester');
      expect(TASK_AGENT_RECOMMENDATIONS.security_audit).toContain('security');
      expect(TASK_AGENT_RECOMMENDATIONS.deploy).toContain('deployer');
    });
    
    it('should get recommended agents via platform', () => {
      const recommended = platform.getRecommendedAgents('implement');
      expect(recommended).toContain('coder');
      expect(recommended).toContain('architect');
    });
  });
  
  describe('Task Execution', () => {
    it('should execute a task with default executor', async () => {
      const task = platform.createTask({
        type: 'implement',
        title: 'Hello World',
        description: 'Create a hello world function',
        complexity: 'moderate'  // Use moderate to get multiple agents
      });
      
      const result = await platform.executeTask(task.id);
      
      expect(result.success).toBe(true);
      expect(result.output).toBeDefined();
      expect(result.contributions.length).toBeGreaterThan(0);
      
      const updatedTask = platform.getTask(task.id);
      expect(updatedTask?.status).toBe('completed');
    });
    
    it('should execute with custom executor', async () => {
      const task = platform.createTask({
        type: 'review',
        title: 'Code Review',
        description: 'Review this code',
        code: 'function hello() { return "world"; }',
        complexity: 'simple'
      });
      
      const customExecutor = async (agent: BuiltInAgent, action: string, context: string) => ({
        output: `Custom output from ${agent.name} for ${action}`,
        confidence: 0.95,
        tokens: 100
      });
      
      const result = await platform.executeTask(task.id, undefined, customExecutor);
      
      expect(result.success).toBe(true);
      expect(result.output).toContain('Custom output');
    });
    
    it('should update agent stats after task completion', async () => {
      const task = platform.createTask({
        type: 'implement',
        title: 'Stats Test',
        description: 'Test agent stats',
        complexity: 'moderate'  // Use moderate to get multiple agents
      });
      
      await platform.executeTask(task.id);
      
      // At least one agent should have updated stats
      const agents = platform.getAgents();
      const updatedAgent = agents.find(a => a.stats.tasksCompleted > 0);
      expect(updatedAgent).toBeDefined();
    });
  });
  
  describe('Statistics', () => {
    it('should provide platform statistics', () => {
      const stats = platform.getStatistics();
      
      expect(stats.totalAgents).toBe(6);
      expect(stats.availableAgents).toBe(6);
      expect(stats.totalTasks).toBe(0);
      expect(stats.completedTasks).toBe(0);
      expect(stats.activeGroups).toBe(0);
    });
    
    it('should update statistics after task execution', async () => {
      const task = platform.createTask({
        type: 'implement',
        title: 'Stats Task',
        description: 'Test statistics',
        complexity: 'moderate'  // Use moderate to get multiple agents
      });
      
      await platform.executeTask(task.id);
      
      const stats = platform.getStatistics();
      expect(stats.totalTasks).toBe(1);
      expect(stats.completedTasks).toBe(1);
    });
  });
  
  describe('Events', () => {
    it('should emit events for task lifecycle', async () => {
      const events: any[] = [];
      platform.onEvent(e => events.push(e));
      
      const task = platform.createTask({
        type: 'implement',
        title: 'Event Test',
        description: 'Test events',
        complexity: 'moderate'  // Use moderate to get multiple agents
      });
      
      await platform.executeTask(task.id);
      
      expect(events.some(e => e.type === 'task_created')).toBe(true);
      expect(events.some(e => e.type === 'group_created')).toBe(true);
      expect(events.some(e => e.type === 'task_started')).toBe(true);
      expect(events.some(e => e.type === 'task_completed')).toBe(true);
    });
  });
});

describe('createBuiltInAgents', () => {
  it('should create agents with specified provider', () => {
    const agents = createBuiltInAgents('anthropic');
    
    for (const agent of agents) {
      expect(agent.provider).toBe('anthropic');
      expect(agent.model).toContain('claude');
    }
  });
});

describe('TaskGroupManager', () => {
  let agents: BuiltInAgent[];
  let manager: TaskGroupManager;
  
  beforeEach(() => {
    agents = createBuiltInAgents();
    manager = new TaskGroupManager(agents);
  });
  
  it('should recommend group composition', () => {
    const recommendation = manager.recommendGroup('implement', 'moderate');
    
    expect(recommendation).toContain('coder');
    expect(recommendation.length).toBe(2); // pair for moderate
  });
  
  it('should get group agents', () => {
    const group = manager.createCustomGroup(['architect', 'coder']);
    const groupAgents = manager.getGroupAgents(group.id);
    
    expect(groupAgents).toHaveLength(2);
    expect(groupAgents.map(a => a.role)).toContain('architect');
    expect(groupAgents.map(a => a.role)).toContain('coder');
  });
  
  it('should get lead agent', () => {
    const group = manager.createCustomGroup(['architect', 'coder']);
    const lead = manager.getLeadAgent(group.id);
    
    expect(lead).toBeDefined();
    expect(lead?.role).toBe('architect');
  });
});

describe('CollaborationEngine', () => {
  let engine: CollaborationEngine;
  
  beforeEach(() => {
    engine = new CollaborationEngine();
  });
  
  it('should merge contributions', () => {
    const contributions = [
      { agentId: 'a1', role: 'architect' as AgentRole, action: 'design', output: 'Design output', confidence: 0.9, timestamp: 1 },
      { agentId: 'a2', role: 'coder' as AgentRole, action: 'implement', output: 'Code output', confidence: 0.85, timestamp: 2 }
    ];
    
    const merged = engine.mergeContributions(contributions);
    
    expect(merged).toContain('ARCHITECT');
    expect(merged).toContain('CODER');
    expect(merged).toContain('Design output');
    expect(merged).toContain('Code output');
  });
  
  it('should calculate group confidence', () => {
    const contributions = [
      { agentId: 'a1', role: 'architect' as AgentRole, action: 'design', output: '', confidence: 0.9, timestamp: 1 },
      { agentId: 'a2', role: 'coder' as AgentRole, action: 'implement', output: '', confidence: 0.8, timestamp: 2 }
    ];
    
    const confidence = engine.calculateGroupConfidence(contributions);
    
    expect(confidence).toBeCloseTo(0.85, 10);
  });
});

describe('createAgenticPlatform', () => {
  it('should create a platform with default provider', () => {
    const platform = createAgenticPlatform();
    const agents = platform.getAgents();
    
    expect(agents[0].provider).toBe('openai');
  });
  
  it('should create a platform with custom provider', () => {
    const platform = createAgenticPlatform('anthropic');
    const agents = platform.getAgents();
    
    expect(agents[0].provider).toBe('anthropic');
  });
});
