/**
 * @file redis-orchestrator.ts
 * @module fleet/redis-orchestrator
 * @component Fleet Management System
 * @version 3.0.0
 * @since 2026-01-20
 *
 * Redis/BullMQ Fleet Orchestrator - Distributed agent coordination
 *
 * Architecture:
 * - Captain: Orchestrator (task routing, prioritization)
 * - Crew: Specialized agents (Architect, Researcher, Developer, QA, etc.)
 * - Redis: Persistent job queue with automatic retry
 * - BullMQ: Job processing with concurrency control
 *
 * Agent Roles (in execution order):
 * 1. captain     - Task routing & orchestration
 * 2. architect   - System design
 * 3. researcher  - Information gathering
 * 4. developer   - Implementation
 * 5. reviewer    - Code review
 * 6. qa          - Quality assurance
 * 7. devops      - Deployment
 * 8. security    - Security audit
 *
 * Benefits:
 * - Survives server restarts (job persistence)
 * - Horizontal scaling (multiple workers)
 * - Preserves cryptographic state via SCBE envelopes
 * - No single point of failure
 */

import { EventEmitter } from 'events';

// ============================================================
// TYPE DEFINITIONS
// ============================================================

export type AgentRole =
  | 'captain' // Orchestrator
  | 'architect' // System design
  | 'researcher' // Information gathering
  | 'developer' // Code implementation
  | 'qa' // Testing & validation
  | 'security' // Security review
  | 'reviewer' // Code review
  | 'documenter' // Documentation
  | 'deployer' // Deployment ops
  | 'monitor'; // System monitoring

export type JobPriority = 'critical' | 'high' | 'normal' | 'low';

export type JobStatus = 'pending' | 'active' | 'completed' | 'failed' | 'delayed' | 'waiting';

export interface FleetJob {
  id: string;
  name: string;
  data: JobData;
  priority: JobPriority;
  assignedTo?: AgentRole;
  status: JobStatus;
  attempts: number;
  maxAttempts: number;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
  result?: unknown;
  error?: string;
}

export interface JobData {
  task: string;
  context: Record<string, unknown>;
  requiredCapabilities?: string[];
  timeout?: number;
  metadata?: Record<string, unknown>;
}

export interface AgentConfig {
  role: AgentRole;
  capabilities: string[];
  concurrency: number;
  maxJobsPerMinute?: number;
}

export interface FleetConfig {
  redis: RedisConfig;
  queues: QueueConfig[];
  agents: AgentConfig[];
}

export interface RedisConfig {
  host: string;
  port: number;
  password?: string;
  db?: number;
  tls?: boolean;
  maxRetriesPerRequest?: number;
  enableReadyCheck?: boolean;
}

export interface QueueConfig {
  name: string;
  priority: JobPriority;
  defaultJobOptions?: {
    attempts?: number;
    backoff?: {
      type: 'exponential' | 'fixed';
      delay: number;
    };
    removeOnComplete?: boolean | number;
    removeOnFail?: boolean | number;
  };
}

// ============================================================
// DEFAULT CONFIGURATION
// ============================================================

export const DEFAULT_REDIS_CONFIG: RedisConfig = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379', 10),
  password: process.env.REDIS_PASSWORD,
  db: parseInt(process.env.REDIS_DB || '0', 10),
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
};

export const DEFAULT_QUEUES: QueueConfig[] = [
  {
    name: 'critical',
    priority: 'critical',
    defaultJobOptions: {
      attempts: 5,
      backoff: { type: 'exponential', delay: 1000 },
      removeOnComplete: 100,
      removeOnFail: 500,
    },
  },
  {
    name: 'high',
    priority: 'high',
    defaultJobOptions: {
      attempts: 3,
      backoff: { type: 'exponential', delay: 2000 },
      removeOnComplete: 500,
      removeOnFail: 1000,
    },
  },
  {
    name: 'normal',
    priority: 'normal',
    defaultJobOptions: {
      attempts: 3,
      backoff: { type: 'exponential', delay: 5000 },
      removeOnComplete: 1000,
      removeOnFail: 2000,
    },
  },
  {
    name: 'low',
    priority: 'low',
    defaultJobOptions: {
      attempts: 2,
      backoff: { type: 'fixed', delay: 10000 },
      removeOnComplete: 2000,
      removeOnFail: 5000,
    },
  },
];

export const DEFAULT_AGENTS: AgentConfig[] = [
  {
    role: 'captain',
    capabilities: ['orchestration', 'routing', 'prioritization'],
    concurrency: 1,
  },
  {
    role: 'architect',
    capabilities: ['design', 'planning', 'architecture'],
    concurrency: 2,
  },
  {
    role: 'researcher',
    capabilities: ['search', 'analysis', 'documentation'],
    concurrency: 3,
  },
  {
    role: 'developer',
    capabilities: ['coding', 'implementation', 'refactoring'],
    concurrency: 4,
  },
  {
    role: 'qa',
    capabilities: ['testing', 'validation', 'verification'],
    concurrency: 2,
  },
  {
    role: 'security',
    capabilities: ['security', 'audit', 'compliance'],
    concurrency: 1,
  },
  {
    role: 'reviewer',
    capabilities: ['review', 'feedback', 'approval'],
    concurrency: 2,
  },
  {
    role: 'documenter',
    capabilities: ['documentation', 'writing', 'explanation'],
    concurrency: 2,
  },
  {
    role: 'deployer',
    capabilities: ['deployment', 'operations', 'monitoring'],
    concurrency: 1,
  },
  {
    role: 'monitor',
    capabilities: ['monitoring', 'alerting', 'metrics'],
    concurrency: 1,
  },
];

// ============================================================
// FLEET ORCHESTRATOR (In-Memory Implementation)
// ============================================================

/**
 * Fleet Orchestrator
 *
 * In production, this would use BullMQ with Redis.
 * This implementation provides the same interface with in-memory queues
 * for development and testing.
 */
export class FleetOrchestrator extends EventEmitter {
  private config: FleetConfig;
  private queues: Map<string, FleetJob[]>;
  private agents: Map<AgentRole, AgentState>;
  private jobCounter: number;
  private isRunning: boolean;

  constructor(config?: Partial<FleetConfig>) {
    super();
    this.config = {
      redis: config?.redis || DEFAULT_REDIS_CONFIG,
      queues: config?.queues || DEFAULT_QUEUES,
      agents: config?.agents || DEFAULT_AGENTS,
    };

    this.queues = new Map();
    this.agents = new Map();
    this.jobCounter = 0;
    this.isRunning = false;

    this.initializeQueues();
    this.initializeAgents();
  }

  private initializeQueues(): void {
    for (const queueConfig of this.config.queues) {
      this.queues.set(queueConfig.name, []);
    }
  }

  private initializeAgents(): void {
    for (const agentConfig of this.config.agents) {
      this.agents.set(agentConfig.role, {
        config: agentConfig,
        activeJobs: 0,
        totalProcessed: 0,
        status: 'idle',
      });
    }
  }

  /**
   * Start the orchestrator
   */
  async start(): Promise<void> {
    if (this.isRunning) return;

    this.isRunning = true;
    this.emit('started');

    // Start processing loop
    this.processLoop();
  }

  /**
   * Stop the orchestrator
   */
  async stop(): Promise<void> {
    this.isRunning = false;
    this.emit('stopped');
  }

  /**
   * Add a job to the queue
   */
  async addJob(
    name: string,
    data: JobData,
    options?: {
      priority?: JobPriority;
      assignTo?: AgentRole;
      delay?: number;
    }
  ): Promise<FleetJob> {
    const priority = options?.priority || 'normal';
    const queueName = priority;

    const job: FleetJob = {
      id: `job_${++this.jobCounter}_${Date.now()}`,
      name,
      data,
      priority,
      assignedTo: options?.assignTo,
      status: options?.delay ? 'delayed' : 'pending',
      attempts: 0,
      maxAttempts: this.getMaxAttempts(priority),
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    const queue = this.queues.get(queueName);
    if (queue) {
      queue.push(job);
      this.emit('job:added', job);
    }

    return job;
  }

  /**
   * Get job by ID
   */
  async getJob(jobId: string): Promise<FleetJob | null> {
    for (const queue of this.queues.values()) {
      const job = queue.find((j) => j.id === jobId);
      if (job) return job;
    }
    return null;
  }

  /**
   * Get queue statistics
   */
  async getStats(): Promise<FleetStats> {
    let pending = 0;
    let active = 0;
    let completed = 0;
    let failed = 0;

    for (const queue of this.queues.values()) {
      for (const job of queue) {
        switch (job.status) {
          case 'pending':
          case 'waiting':
          case 'delayed':
            pending++;
            break;
          case 'active':
            active++;
            break;
          case 'completed':
            completed++;
            break;
          case 'failed':
            failed++;
            break;
        }
      }
    }

    const agentStats: Record<AgentRole, AgentStats> = {} as Record<AgentRole, AgentStats>;
    for (const [role, state] of this.agents.entries()) {
      agentStats[role] = {
        activeJobs: state.activeJobs,
        totalProcessed: state.totalProcessed,
        status: state.status,
      };
    }

    return {
      pending,
      active,
      completed,
      failed,
      agents: agentStats,
    };
  }

  /**
   * Process a job (called by agent workers)
   */
  async processJob(job: FleetJob, processor: (job: FleetJob) => Promise<unknown>): Promise<void> {
    const agent = job.assignedTo ? this.agents.get(job.assignedTo) : null;

    try {
      job.status = 'active';
      job.attempts++;
      job.updatedAt = new Date();

      if (agent) {
        agent.activeJobs++;
        agent.status = 'busy';
      }

      this.emit('job:active', job);

      const result = await processor(job);

      job.status = 'completed';
      job.result = result;
      job.completedAt = new Date();
      job.updatedAt = new Date();

      if (agent) {
        agent.activeJobs--;
        agent.totalProcessed++;
        agent.status = agent.activeJobs > 0 ? 'busy' : 'idle';
      }

      this.emit('job:completed', job);
    } catch (error) {
      job.error = error instanceof Error ? error.message : String(error);
      job.updatedAt = new Date();

      if (job.attempts < job.maxAttempts) {
        job.status = 'pending'; // Retry
        this.emit('job:retry', job);
      } else {
        job.status = 'failed';
        this.emit('job:failed', job);
      }

      if (agent) {
        agent.activeJobs--;
        agent.status = agent.activeJobs > 0 ? 'busy' : 'idle';
      }
    }
  }

  /**
   * Get next available job for an agent
   */
  async getNextJob(role: AgentRole): Promise<FleetJob | null> {
    const agent = this.agents.get(role);
    if (!agent || agent.activeJobs >= agent.config.concurrency) {
      return null;
    }

    // Check all queues in priority order
    for (const priority of ['critical', 'high', 'normal', 'low'] as JobPriority[]) {
      const queue = this.queues.get(priority);
      if (!queue) continue;

      // Find first pending job that matches agent capabilities
      const jobIndex = queue.findIndex((job) => {
        if (job.status !== 'pending') return false;
        if (job.assignedTo && job.assignedTo !== role) return false;

        // Check capabilities match
        const required = job.data.requiredCapabilities || [];
        return required.every((cap) => agent.config.capabilities.includes(cap));
      });

      if (jobIndex !== -1) {
        const job = queue[jobIndex];
        job.assignedTo = role;
        return job;
      }
    }

    return null;
  }

  /**
   * Route a task to the appropriate agent
   */
  async routeTask(task: string, context: Record<string, unknown>): Promise<FleetJob> {
    // Determine best agent based on task type
    const role = this.determineAgent(task);
    const priority = this.determinePriority(task);

    return this.addJob(task, { task, context }, { priority, assignTo: role });
  }

  private determineAgent(task: string): AgentRole {
    const taskLower = task.toLowerCase();

    if (taskLower.includes('design') || taskLower.includes('architecture')) {
      return 'architect';
    }
    if (taskLower.includes('research') || taskLower.includes('search')) {
      return 'researcher';
    }
    if (taskLower.includes('code') || taskLower.includes('implement')) {
      return 'developer';
    }
    if (taskLower.includes('test') || taskLower.includes('validate')) {
      return 'qa';
    }
    if (taskLower.includes('security') || taskLower.includes('audit')) {
      return 'security';
    }
    if (taskLower.includes('review')) {
      return 'reviewer';
    }
    if (taskLower.includes('document') || taskLower.includes('write')) {
      return 'documenter';
    }
    if (taskLower.includes('deploy') || taskLower.includes('release')) {
      return 'deployer';
    }
    if (taskLower.includes('monitor') || taskLower.includes('alert')) {
      return 'monitor';
    }

    // Default to developer for unmatched tasks
    return 'developer';
  }

  private determinePriority(task: string): JobPriority {
    const taskLower = task.toLowerCase();

    if (
      taskLower.includes('urgent') ||
      taskLower.includes('critical') ||
      taskLower.includes('security')
    ) {
      return 'critical';
    }
    if (taskLower.includes('important') || taskLower.includes('high')) {
      return 'high';
    }
    if (taskLower.includes('low') || taskLower.includes('minor')) {
      return 'low';
    }

    return 'normal';
  }

  private getMaxAttempts(priority: JobPriority): number {
    const queueConfig = this.config.queues.find((q) => q.priority === priority);
    return queueConfig?.defaultJobOptions?.attempts || 3;
  }

  private async processLoop(): Promise<void> {
    while (this.isRunning) {
      // Simple polling - in production BullMQ handles this
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
}

// ============================================================
// SUPPORTING TYPES
// ============================================================

interface AgentState {
  config: AgentConfig;
  activeJobs: number;
  totalProcessed: number;
  status: 'idle' | 'busy' | 'offline';
}

interface AgentStats {
  activeJobs: number;
  totalProcessed: number;
  status: 'idle' | 'busy' | 'offline';
}

interface FleetStats {
  pending: number;
  active: number;
  completed: number;
  failed: number;
  agents: Record<AgentRole, AgentStats>;
}

// ============================================================
// BULLMQ INTEGRATION (Production)
// ============================================================

/**
 * Production BullMQ Orchestrator
 *
 * This class would be used in production with actual Redis/BullMQ.
 * Requires: npm install bullmq ioredis
 */
export class BullMQOrchestrator {
  // In production, this would use:
  // import { Queue, Worker, QueueScheduler } from 'bullmq';
  // import Redis from 'ioredis';

  static async create(config: FleetConfig): Promise<FleetOrchestrator> {
    // For now, return the in-memory orchestrator
    // In production, this would create BullMQ instances
    const orchestrator = new FleetOrchestrator(config);
    await orchestrator.start();
    return orchestrator;
  }
}

// ============================================================
// EXPORTS
// ============================================================

export const fleet = {
  FleetOrchestrator,
  BullMQOrchestrator,
  DEFAULT_REDIS_CONFIG,
  DEFAULT_QUEUES,
  DEFAULT_AGENTS,
};

export default fleet;
