/**
 * Kafka Integration for Agent Events
 *
 * Provides event publishing and subscription for agent coordination.
 * Uses topic naming convention: scbe.{tier}.{tongue}.{event_type}
 *
 * @module agent/kafka
 */

import { createHash } from 'crypto';
import { TongueCode, TONGUE_CODES } from '../tokenizer/ss1.js';
import { signWithTongueBinding } from '../tokenizer/quantum-lattice.js';
import {
  Agent,
  AgentEvent,
  AgentEventType,
  AgentHeartbeat,
  BFTVote,
  IPTier,
  PoincarePosition,
} from './types.js';

// ============================================================================
// Types
// ============================================================================

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

// ============================================================================
// Topic Naming
// ============================================================================

/**
 * Generate Kafka topic name following SCBE convention
 *
 * Format: scbe.{tier}.{tongue}.{event_type}
 */
export function getTopicName(tier: IPTier, tongue: TongueCode, eventType: AgentEventType): string {
  const eventSuffix = eventType.replace('agent.', '');
  return `scbe.${tier}.${tongue.toLowerCase()}.${eventSuffix}`;
}

/**
 * Generate wildcard topic pattern for tier
 */
export function getTierTopicPattern(tier: IPTier): string {
  return `scbe.${tier}.*`;
}

/**
 * Generate all topics for an agent
 */
export function getAgentTopics(tongue: TongueCode, tier: IPTier): string[] {
  const eventTypes: AgentEventType[] = [
    'agent.joined',
    'agent.heartbeat',
    'agent.leaving',
    'agent.offline',
    'agent.degraded',
    'agent.quarantine',
    'agent.recovered',
  ];

  return eventTypes.map((e) => getTopicName(tier, tongue, e));
}

/**
 * Parse topic name to extract components
 */
export function parseTopicName(topic: string): {
  tier: IPTier;
  tongue: TongueCode;
  eventType: AgentEventType;
} | null {
  const parts = topic.split('.');
  if (parts.length !== 4 || parts[0] !== 'scbe') {
    return null;
  }

  const tier = parts[1] as IPTier;
  const tongue = parts[2].toUpperCase() as TongueCode;
  const eventType = `agent.${parts[3]}` as AgentEventType;

  if (!['public', 'private', 'hidden'].includes(tier)) {
    return null;
  }

  if (!TONGUE_CODES.includes(tongue)) {
    return null;
  }

  return { tier, tongue, eventType };
}

// ============================================================================
// Mock Kafka Client (for testing)
// ============================================================================

/**
 * In-memory Kafka mock for testing
 */
export class MockKafkaClient {
  private messages: Map<string, KafkaMessage[]> = new Map();
  private handlers: Map<string, ((msg: KafkaMessage) => Promise<void>)[]> = new Map();
  private subscriptions: Set<string> = new Set();

  /**
   * Create a producer
   */
  createProducer(): KafkaProducer {
    return {
      send: async (message: KafkaMessage) => {
        const existing = this.messages.get(message.topic) || [];
        existing.push(message);
        this.messages.set(message.topic, existing);

        // Notify subscribers
        for (const [pattern, handlers] of this.handlers) {
          if (this.topicMatches(message.topic, pattern)) {
            for (const handler of handlers) {
              await handler(message);
            }
          }
        }
      },
      sendBatch: async (messages: KafkaMessage[]) => {
        for (const msg of messages) {
          await this.createProducer().send(msg);
        }
      },
      disconnect: async () => {},
    };
  }

  /**
   * Create a consumer
   */
  createConsumer(): KafkaConsumer {
    const handlers: ((msg: KafkaMessage) => Promise<void>)[] = [];

    return {
      subscribe: async (topics: string[]) => {
        for (const topic of topics) {
          this.subscriptions.add(topic);
          if (!this.handlers.has(topic)) {
            this.handlers.set(topic, []);
          }
          this.handlers.get(topic)!.push(...handlers);
        }
      },
      onMessage: <T>(handler: (msg: KafkaMessage<T>) => Promise<void>) => {
        handlers.push(handler as (msg: KafkaMessage) => Promise<void>);

        // Register with existing subscriptions
        for (const topic of this.subscriptions) {
          if (!this.handlers.has(topic)) {
            this.handlers.set(topic, []);
          }
          this.handlers.get(topic)!.push(handler as (msg: KafkaMessage) => Promise<void>);
        }
      },
      disconnect: async () => {
        handlers.length = 0;
      },
    };
  }

  /**
   * Get messages for a topic (for testing)
   */
  getMessages(topic: string): KafkaMessage[] {
    return this.messages.get(topic) || [];
  }

  /**
   * Clear all messages (for testing)
   */
  clear(): void {
    this.messages.clear();
  }

  private topicMatches(topic: string, pattern: string): boolean {
    if (pattern.endsWith('*')) {
      return topic.startsWith(pattern.slice(0, -1));
    }
    return topic === pattern;
  }
}

// ============================================================================
// Event Publishing
// ============================================================================

/**
 * Agent event publisher
 */
export class AgentEventPublisher {
  private producer: KafkaProducer;
  private agent: Agent;

  constructor(producer: KafkaProducer, agent: Agent) {
    this.producer = producer;
    this.agent = agent;
  }

  /**
   * Publish an agent event
   */
  async publish<T>(event: AgentEvent<T>): Promise<void> {
    const topic = getTopicName(this.agent.ipTier, this.agent.tongue, event.type);

    // Sign event if we have private key
    let signedEvent = event;
    if (this.agent.keys.privateKey) {
      const { signature, tongueBinding } = signWithTongueBinding(
        Buffer.from(JSON.stringify(event.payload)),
        this.agent.tongue,
        this.agent.keys.privateKey
      );
      signedEvent = { ...event, signature, tongueBinding };
    }

    const message: KafkaMessage<AgentEvent<T>> = {
      topic,
      key: this.agent.id,
      value: signedEvent,
      headers: {
        'x-agent-id': this.agent.id,
        'x-tongue': this.agent.tongue,
        'x-ip-tier': this.agent.ipTier,
        'x-event-type': event.type,
      },
      timestamp: event.timestamp,
    };

    await this.producer.send(message);
  }

  /**
   * Publish heartbeat
   */
  async publishHeartbeat(): Promise<void> {
    const heartbeat: AgentHeartbeat = {
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      position: this.agent.position,
      coherence: this.agent.coherence,
      status: this.agent.status,
      timestamp: Date.now(),
    };

    await this.publish({
      type: 'agent.heartbeat',
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      timestamp: heartbeat.timestamp,
      payload: heartbeat,
    });
  }

  /**
   * Publish join event
   */
  async publishJoined(): Promise<void> {
    await this.publish({
      type: 'agent.joined',
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      timestamp: Date.now(),
      payload: {
        position: this.agent.position,
        phase: this.agent.phase,
        weight: this.agent.weight,
        ipTier: this.agent.ipTier,
        publicKey: this.agent.keys.publicKey.toString('hex'),
      },
    });
  }

  /**
   * Publish leaving event
   */
  async publishLeaving(reason = 'graceful_shutdown'): Promise<void> {
    await this.publish({
      type: 'agent.leaving',
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      timestamp: Date.now(),
      payload: {
        reason,
        uptimeMs: Date.now() - this.agent.createdAt,
      },
    });
  }

  /**
   * Publish vote for BFT consensus
   */
  async publishVote(vote: BFTVote): Promise<void> {
    // Use special consensus topic
    const topic = `scbe.consensus.${this.agent.ipTier}.votes`;

    const message: KafkaMessage<BFTVote> = {
      topic,
      key: `${vote.agentId}:${vote.timestamp}`,
      value: vote,
      headers: {
        'x-agent-id': this.agent.id,
        'x-tongue': this.agent.tongue,
        'x-decision': vote.decision,
      },
      timestamp: vote.timestamp,
    };

    await this.producer.send(message);
  }
}

// ============================================================================
// Event Subscription
// ============================================================================

/** Event handler type */
export type AgentEventHandler<T = unknown> = (event: AgentEvent<T>) => Promise<void>;

/**
 * Agent event subscriber
 */
export class AgentEventSubscriber {
  private consumer: KafkaConsumer;
  private handlers: Map<AgentEventType, AgentEventHandler[]> = new Map();
  private globalHandlers: AgentEventHandler[] = [];

  constructor(consumer: KafkaConsumer) {
    this.consumer = consumer;

    // Set up message handler
    this.consumer.onMessage(async (message: KafkaMessage<AgentEvent>) => {
      const event = message.value;

      // Call type-specific handlers
      const typeHandlers = this.handlers.get(event.type) || [];
      for (const handler of typeHandlers) {
        await handler(event);
      }

      // Call global handlers
      for (const handler of this.globalHandlers) {
        await handler(event);
      }
    });
  }

  /**
   * Subscribe to topics for a tier
   */
  async subscribeToTier(tier: IPTier, tongues?: TongueCode[]): Promise<void> {
    const targetTongues = tongues || TONGUE_CODES;
    const topics: string[] = [];

    for (const tongue of targetTongues) {
      topics.push(...getAgentTopics(tongue, tier));
    }

    await this.consumer.subscribe(topics);
  }

  /**
   * Subscribe to all events for an agent
   */
  async subscribeToAgent(tongue: TongueCode, tier: IPTier): Promise<void> {
    const topics = getAgentTopics(tongue, tier);
    await this.consumer.subscribe(topics);
  }

  /**
   * Add handler for specific event type
   */
  on<T>(eventType: AgentEventType, handler: AgentEventHandler<T>): void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler as AgentEventHandler);
  }

  /**
   * Add global handler for all events
   */
  onAny(handler: AgentEventHandler): void {
    this.globalHandlers.push(handler);
  }

  /**
   * Disconnect consumer
   */
  async disconnect(): Promise<void> {
    await this.consumer.disconnect();
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a Kafka client (mock for now, replace with real implementation)
 */
export function createKafkaClient(_config?: KafkaConfig): MockKafkaClient {
  return new MockKafkaClient();
}

/**
 * Create an event publisher for an agent
 */
export function createEventPublisher(kafka: MockKafkaClient, agent: Agent): AgentEventPublisher {
  const producer = kafka.createProducer();
  return new AgentEventPublisher(producer, agent);
}

/**
 * Create an event subscriber
 */
export function createEventSubscriber(kafka: MockKafkaClient): AgentEventSubscriber {
  const consumer = kafka.createConsumer();
  return new AgentEventSubscriber(consumer);
}
