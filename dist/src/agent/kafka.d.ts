/**
 * Kafka Integration for Agent Events
 *
 * Provides event publishing and subscription for agent coordination.
 * Uses topic naming convention: scbe.{tier}.{tongue}.{event_type}
 *
 * @module agent/kafka
 */
import { TongueCode } from '../tokenizer/ss1.js';
import { Agent, AgentEvent, AgentEventType, BFTVote, IPTier } from './types.js';
/** Kafka message format */
export interface KafkaMessage<T = unknown> {
    topic: string;
    key: string;
    value: T;
    headers?: Record<string, string>;
    timestamp: number;
}
/** Kafka producer interface */
export interface KafkaProducer {
    send(message: KafkaMessage): Promise<void>;
    sendBatch(messages: KafkaMessage[]): Promise<void>;
    disconnect(): Promise<void>;
}
/** Kafka consumer interface */
export interface KafkaConsumer {
    subscribe(topics: string[]): Promise<void>;
    onMessage<T>(handler: (message: KafkaMessage<T>) => Promise<void>): void;
    disconnect(): Promise<void>;
}
/** Kafka client configuration */
export interface KafkaConfig {
    brokers: string[];
    clientId: string;
    sasl?: {
        mechanism: 'plain' | 'scram-sha-256' | 'scram-sha-512';
        username: string;
        password: string;
    };
    ssl?: boolean;
}
/**
 * Generate Kafka topic name following SCBE convention
 *
 * Format: scbe.{tier}.{tongue}.{event_type}
 */
export declare function getTopicName(tier: IPTier, tongue: TongueCode, eventType: AgentEventType): string;
/**
 * Generate wildcard topic pattern for tier
 */
export declare function getTierTopicPattern(tier: IPTier): string;
/**
 * Generate all topics for an agent
 */
export declare function getAgentTopics(tongue: TongueCode, tier: IPTier): string[];
/**
 * Parse topic name to extract components
 */
export declare function parseTopicName(topic: string): {
    tier: IPTier;
    tongue: TongueCode;
    eventType: AgentEventType;
} | null;
/**
 * In-memory Kafka mock for testing
 */
export declare class MockKafkaClient {
    private messages;
    private handlers;
    private subscriptions;
    /**
     * Create a producer
     */
    createProducer(): KafkaProducer;
    /**
     * Create a consumer
     */
    createConsumer(): KafkaConsumer;
    /**
     * Get messages for a topic (for testing)
     */
    getMessages(topic: string): KafkaMessage[];
    /**
     * Clear all messages (for testing)
     */
    clear(): void;
    private topicMatches;
}
/**
 * Agent event publisher
 */
export declare class AgentEventPublisher {
    private producer;
    private agent;
    constructor(producer: KafkaProducer, agent: Agent);
    /**
     * Publish an agent event
     */
    publish<T>(event: AgentEvent<T>): Promise<void>;
    /**
     * Publish heartbeat
     */
    publishHeartbeat(): Promise<void>;
    /**
     * Publish join event
     */
    publishJoined(): Promise<void>;
    /**
     * Publish leaving event
     */
    publishLeaving(reason?: string): Promise<void>;
    /**
     * Publish vote for BFT consensus
     */
    publishVote(vote: BFTVote): Promise<void>;
}
/** Event handler type */
export type AgentEventHandler<T = unknown> = (event: AgentEvent<T>) => Promise<void>;
/**
 * Agent event subscriber
 */
export declare class AgentEventSubscriber {
    private consumer;
    private handlers;
    private globalHandlers;
    constructor(consumer: KafkaConsumer);
    /**
     * Subscribe to topics for a tier
     */
    subscribeToTier(tier: IPTier, tongues?: TongueCode[]): Promise<void>;
    /**
     * Subscribe to all events for an agent
     */
    subscribeToAgent(tongue: TongueCode, tier: IPTier): Promise<void>;
    /**
     * Add handler for specific event type
     */
    on<T>(eventType: AgentEventType, handler: AgentEventHandler<T>): void;
    /**
     * Add global handler for all events
     */
    onAny(handler: AgentEventHandler): void;
    /**
     * Disconnect consumer
     */
    disconnect(): Promise<void>;
}
/**
 * Create a Kafka client (mock for now, replace with real implementation)
 */
export declare function createKafkaClient(_config?: KafkaConfig): MockKafkaClient;
/**
 * Create an event publisher for an agent
 */
export declare function createEventPublisher(kafka: MockKafkaClient, agent: Agent): AgentEventPublisher;
/**
 * Create an event subscriber
 */
export declare function createEventSubscriber(kafka: MockKafkaClient): AgentEventSubscriber;
//# sourceMappingURL=kafka.d.ts.map