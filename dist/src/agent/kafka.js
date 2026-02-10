"use strict";
/**
 * Kafka Integration for Agent Events
 *
 * Provides event publishing and subscription for agent coordination.
 * Uses topic naming convention: scbe.{tier}.{tongue}.{event_type}
 *
 * @module agent/kafka
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentEventSubscriber = exports.AgentEventPublisher = exports.MockKafkaClient = void 0;
exports.getTopicName = getTopicName;
exports.getTierTopicPattern = getTierTopicPattern;
exports.getAgentTopics = getAgentTopics;
exports.parseTopicName = parseTopicName;
exports.createKafkaClient = createKafkaClient;
exports.createEventPublisher = createEventPublisher;
exports.createEventSubscriber = createEventSubscriber;
const ss1_js_1 = require("../tokenizer/ss1.js");
const quantum_lattice_js_1 = require("../tokenizer/quantum-lattice.js");
// ============================================================================
// Topic Naming
// ============================================================================
/**
 * Generate Kafka topic name following SCBE convention
 *
 * Format: scbe.{tier}.{tongue}.{event_type}
 */
function getTopicName(tier, tongue, eventType) {
    const eventSuffix = eventType.replace('agent.', '');
    return `scbe.${tier}.${tongue.toLowerCase()}.${eventSuffix}`;
}
/**
 * Generate wildcard topic pattern for tier
 */
function getTierTopicPattern(tier) {
    return `scbe.${tier}.*`;
}
/**
 * Generate all topics for an agent
 */
function getAgentTopics(tongue, tier) {
    const eventTypes = [
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
function parseTopicName(topic) {
    const parts = topic.split('.');
    if (parts.length !== 4 || parts[0] !== 'scbe') {
        return null;
    }
    const tier = parts[1];
    const tongue = parts[2].toUpperCase();
    const eventType = `agent.${parts[3]}`;
    if (!['public', 'private', 'hidden'].includes(tier)) {
        return null;
    }
    if (!ss1_js_1.TONGUE_CODES.includes(tongue)) {
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
class MockKafkaClient {
    messages = new Map();
    handlers = new Map();
    subscriptions = new Set();
    /**
     * Create a producer
     */
    createProducer() {
        return {
            send: async (message) => {
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
            sendBatch: async (messages) => {
                for (const msg of messages) {
                    await this.createProducer().send(msg);
                }
            },
            disconnect: async () => { },
        };
    }
    /**
     * Create a consumer
     */
    createConsumer() {
        const handlers = [];
        return {
            subscribe: async (topics) => {
                for (const topic of topics) {
                    this.subscriptions.add(topic);
                    if (!this.handlers.has(topic)) {
                        this.handlers.set(topic, []);
                    }
                    this.handlers.get(topic).push(...handlers);
                }
            },
            onMessage: (handler) => {
                handlers.push(handler);
                // Register with existing subscriptions
                for (const topic of this.subscriptions) {
                    if (!this.handlers.has(topic)) {
                        this.handlers.set(topic, []);
                    }
                    this.handlers.get(topic).push(handler);
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
    getMessages(topic) {
        return this.messages.get(topic) || [];
    }
    /**
     * Clear all messages (for testing)
     */
    clear() {
        this.messages.clear();
    }
    topicMatches(topic, pattern) {
        if (pattern.endsWith('*')) {
            return topic.startsWith(pattern.slice(0, -1));
        }
        return topic === pattern;
    }
}
exports.MockKafkaClient = MockKafkaClient;
// ============================================================================
// Event Publishing
// ============================================================================
/**
 * Agent event publisher
 */
class AgentEventPublisher {
    producer;
    agent;
    constructor(producer, agent) {
        this.producer = producer;
        this.agent = agent;
    }
    /**
     * Publish an agent event
     */
    async publish(event) {
        const topic = getTopicName(this.agent.ipTier, this.agent.tongue, event.type);
        // Sign event if we have private key
        let signedEvent = event;
        if (this.agent.keys.privateKey) {
            const { signature, tongueBinding } = (0, quantum_lattice_js_1.signWithTongueBinding)(Buffer.from(JSON.stringify(event.payload)), this.agent.tongue, this.agent.keys.privateKey);
            signedEvent = { ...event, signature, tongueBinding };
        }
        const message = {
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
    async publishHeartbeat() {
        const heartbeat = {
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
    async publishJoined() {
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
    async publishLeaving(reason = 'graceful_shutdown') {
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
    async publishVote(vote) {
        // Use special consensus topic
        const topic = `scbe.consensus.${this.agent.ipTier}.votes`;
        const message = {
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
exports.AgentEventPublisher = AgentEventPublisher;
/**
 * Agent event subscriber
 */
class AgentEventSubscriber {
    consumer;
    handlers = new Map();
    globalHandlers = [];
    constructor(consumer) {
        this.consumer = consumer;
        // Set up message handler
        this.consumer.onMessage(async (message) => {
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
    async subscribeToTier(tier, tongues) {
        const targetTongues = tongues || ss1_js_1.TONGUE_CODES;
        const topics = [];
        for (const tongue of targetTongues) {
            topics.push(...getAgentTopics(tongue, tier));
        }
        await this.consumer.subscribe(topics);
    }
    /**
     * Subscribe to all events for an agent
     */
    async subscribeToAgent(tongue, tier) {
        const topics = getAgentTopics(tongue, tier);
        await this.consumer.subscribe(topics);
    }
    /**
     * Add handler for specific event type
     */
    on(eventType, handler) {
        if (!this.handlers.has(eventType)) {
            this.handlers.set(eventType, []);
        }
        this.handlers.get(eventType).push(handler);
    }
    /**
     * Add global handler for all events
     */
    onAny(handler) {
        this.globalHandlers.push(handler);
    }
    /**
     * Disconnect consumer
     */
    async disconnect() {
        await this.consumer.disconnect();
    }
}
exports.AgentEventSubscriber = AgentEventSubscriber;
// ============================================================================
// Factory Functions
// ============================================================================
/**
 * Create a Kafka client (mock for now, replace with real implementation)
 */
function createKafkaClient(_config) {
    return new MockKafkaClient();
}
/**
 * Create an event publisher for an agent
 */
function createEventPublisher(kafka, agent) {
    const producer = kafka.createProducer();
    return new AgentEventPublisher(producer, agent);
}
/**
 * Create an event subscriber
 */
function createEventSubscriber(kafka) {
    const consumer = kafka.createConsumer();
    return new AgentEventSubscriber(consumer);
}
//# sourceMappingURL=kafka.js.map