/**
 * Redis/BullMQ Fleet Orchestrator
 * ================================
 * Distributed agent orchestration replacing in-memory queue
 *
 * Architecture:
 * - Captain: Orchestrator (task routing, prioritization)
 * - Crew: Specialized agents (Architect, Researcher, Developer, QA, etc.)
 * - Redis: Persistent job queue with automatic retry
 * - BullMQ: Job processing with concurrency control
 *
 * Benefits:
 * - Survives server restarts (job persistence)
 * - Horizontal scaling (multiple workers)
 * - Preserves cryptographic state
 * - No single point of failure
 *
 * @module fleet/redis-orchestrator
 * @version 1.0.0
 */
import { EventEmitter } from 'events';
export type AgentRole = 'captain' | 'architect' | 'researcher' | 'developer' | 'qa' | 'security' | 'reviewer' | 'documenter' | 'deployer' | 'monitor';
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
export declare const DEFAULT_REDIS_CONFIG: RedisConfig;
export declare const DEFAULT_QUEUES: QueueConfig[];
export declare const DEFAULT_AGENTS: AgentConfig[];
/**
 * Fleet Orchestrator
 *
 * In production, this would use BullMQ with Redis.
 * This implementation provides the same interface with in-memory queues
 * for development and testing.
 */
export declare class FleetOrchestrator extends EventEmitter {
    private config;
    private queues;
    private agents;
    private jobCounter;
    private isRunning;
    constructor(config?: Partial<FleetConfig>);
    private initializeQueues;
    private initializeAgents;
    /**
     * Start the orchestrator
     */
    start(): Promise<void>;
    /**
     * Stop the orchestrator
     */
    stop(): Promise<void>;
    /**
     * Add a job to the queue
     */
    addJob(name: string, data: JobData, options?: {
        priority?: JobPriority;
        assignTo?: AgentRole;
        delay?: number;
    }): Promise<FleetJob>;
    /**
     * Get job by ID
     */
    getJob(jobId: string): Promise<FleetJob | null>;
    /**
     * Get queue statistics
     */
    getStats(): Promise<FleetStats>;
    /**
     * Process a job (called by agent workers)
     */
    processJob(job: FleetJob, processor: (job: FleetJob) => Promise<unknown>): Promise<void>;
    /**
     * Get next available job for an agent
     */
    getNextJob(role: AgentRole): Promise<FleetJob | null>;
    /**
     * Route a task to the appropriate agent
     */
    routeTask(task: string, context: Record<string, unknown>): Promise<FleetJob>;
    private determineAgent;
    private determinePriority;
    private getMaxAttempts;
    private processLoop;
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
/**
 * Production BullMQ Orchestrator
 *
 * This class would be used in production with actual Redis/BullMQ.
 * Requires: npm install bullmq ioredis
 */
export declare class BullMQOrchestrator {
    static create(config: FleetConfig): Promise<FleetOrchestrator>;
}
export declare const fleet: {
    FleetOrchestrator: typeof FleetOrchestrator;
    BullMQOrchestrator: typeof BullMQOrchestrator;
    DEFAULT_REDIS_CONFIG: RedisConfig;
    DEFAULT_QUEUES: QueueConfig[];
    DEFAULT_AGENTS: AgentConfig[];
};
export default fleet;
//# sourceMappingURL=redis-orchestrator.d.ts.map