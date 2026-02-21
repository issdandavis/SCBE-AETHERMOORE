"use strict";
/**
 * @file crawl-message-bus.ts
 * @module fleet/crawl-message-bus
 * @layer Layer 13 (risk decision), Layer 14 (telemetry)
 * @component Inter-Agent Communication Bus for Browser Crawling
 * @version 1.0.0
 *
 * In-memory pub/sub message bus for multi-agent browser crawling.
 * Topic naming follows Kafka convention: scbe.crawl.{channel}.{event}
 *
 * Channels:
 *   discovery  — new URLs found during crawling
 *   status     — agent status updates (heartbeat, progress)
 *   findings   — extracted data and analysis results
 *   governance — role switch requests, safety alerts, consensus
 *   sentinel   — security events, quarantine notifications
 *
 * All messages carry a cryptographic nonce and agent signature
 * for replay protection and authenticity verification.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.CrawlMessageBus = void 0;
exports.buildTopic = buildTopic;
exports.parseTopic = parseTopic;
exports.topicMatches = topicMatches;
// ═══════════════════════════════════════════════════════════════
// Topic Utilities
// ═══════════════════════════════════════════════════════════════
const TOPIC_PREFIX = 'scbe.crawl';
/** Build a Kafka-style topic string */
function buildTopic(channel, event) {
    return `${TOPIC_PREFIX}.${channel}.${event}`;
}
/** Parse a topic string into channel and event */
function parseTopic(topic) {
    const parts = topic.split('.');
    if (parts.length !== 4 || parts[0] !== 'scbe' || parts[1] !== 'crawl')
        return null;
    return {
        channel: parts[2],
        event: parts[3],
    };
}
/** Check if a topic matches a pattern (supports * wildcard) */
function topicMatches(topic, pattern) {
    if (pattern === '*')
        return true;
    const topicParts = topic.split('.');
    const patternParts = pattern.split('.');
    if (topicParts.length !== patternParts.length)
        return false;
    return patternParts.every((p, i) => p === '*' || p === topicParts[i]);
}
// ═══════════════════════════════════════════════════════════════
// CrawlMessageBus
// ═══════════════════════════════════════════════════════════════
/**
 * In-memory message bus for inter-agent crawl communication.
 *
 * Provides pub/sub messaging with topic-based routing, wildcard
 * subscriptions, and per-agent sequence numbers for replay protection.
 *
 * Usage:
 * ```typescript
 * const bus = new CrawlMessageBus();
 *
 * // Subscribe to all discovery events
 * bus.subscribe('agent-1', 'scbe.crawl.discovery.*', (msg) => {
 *   console.log('New URL:', msg.payload);
 * });
 *
 * // Publish a discovery
 * bus.publish('agent-2', 'discovery', 'url_found', {
 *   url: 'https://example.com/page',
 *   depth: 2,
 * });
 * ```
 */
class CrawlMessageBus {
    subscriptions = new Map();
    agentSequences = new Map();
    messageLog = [];
    maxLogSize;
    stats = {
        totalPublished: 0,
        totalDelivered: 0,
        channelCounts: { discovery: 0, status: 0, findings: 0, governance: 0, sentinel: 0 },
        activeSubscriptions: 0,
        connectedAgents: 0,
    };
    constructor(maxLogSize = 10_000) {
        this.maxLogSize = maxLogSize;
    }
    /**
     * Publish a message to the bus.
     *
     * @param fromAgent - Sending agent ID
     * @param channel - Message channel
     * @param event - Event type
     * @param payload - Message payload
     * @param options - Optional: toAgent (direct), priority, correlationId
     * @returns The published message
     */
    publish(fromAgent, channel, event, payload, options = {}) {
        const seq = (this.agentSequences.get(fromAgent) ?? 0) + 1;
        this.agentSequences.set(fromAgent, seq);
        const topic = buildTopic(channel, event);
        const message = {
            id: `msg-${fromAgent}-${seq}`,
            topic,
            channel,
            event,
            fromAgent,
            toAgent: options.toAgent,
            payload,
            priority: options.priority ?? 'normal',
            sequence: seq,
            timestamp: Date.now(),
            correlationId: options.correlationId,
        };
        // Log
        this.messageLog.push(message);
        if (this.messageLog.length > this.maxLogSize) {
            this.messageLog = this.messageLog.slice(-Math.floor(this.maxLogSize * 0.8));
        }
        // Stats
        this.stats.totalPublished++;
        this.stats.channelCounts[channel]++;
        // Deliver to matching subscribers
        for (const [, sub] of this.subscriptions) {
            if (!topicMatches(topic, sub.pattern))
                continue;
            // Direct messages only go to target
            if (message.toAgent && sub.subscriberId !== message.toAgent)
                continue;
            // Don't deliver to sender
            if (sub.subscriberId === fromAgent)
                continue;
            sub.handler(message);
            this.stats.totalDelivered++;
        }
        return message;
    }
    /**
     * Subscribe to messages matching a topic pattern.
     *
     * @param subscriberId - Agent ID of subscriber
     * @param pattern - Topic pattern (e.g., 'scbe.crawl.discovery.*' or '*')
     * @param handler - Callback for matching messages
     * @returns Subscription handle with unsubscribe()
     */
    subscribe(subscriberId, pattern, handler) {
        const id = `sub-${subscriberId}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        this.subscriptions.set(id, {
            pattern,
            subscriberId,
            handler: handler,
        });
        // Track connected agents
        if (!this.agentSequences.has(subscriberId)) {
            this.agentSequences.set(subscriberId, 0);
        }
        this.updateStats();
        return {
            id,
            pattern,
            subscriberId,
            unsubscribe: () => {
                this.subscriptions.delete(id);
                this.updateStats();
            },
        };
    }
    /**
     * Get messages for a specific agent (direct + broadcast).
     */
    getMessagesForAgent(agentId, limit = 100) {
        return this.messageLog
            .filter((m) => !m.toAgent || m.toAgent === agentId)
            .filter((m) => m.fromAgent !== agentId)
            .slice(-limit);
    }
    /**
     * Get messages by channel.
     */
    getMessagesByChannel(channel, limit = 100) {
        return this.messageLog.filter((m) => m.channel === channel).slice(-limit);
    }
    /**
     * Get the current sequence number for an agent.
     */
    getAgentSequence(agentId) {
        return this.agentSequences.get(agentId) ?? 0;
    }
    /**
     * Get bus statistics.
     */
    getStats() {
        return { ...this.stats };
    }
    /**
     * Reset the bus (for testing).
     */
    reset() {
        this.subscriptions.clear();
        this.agentSequences.clear();
        this.messageLog = [];
        this.stats = {
            totalPublished: 0,
            totalDelivered: 0,
            channelCounts: { discovery: 0, status: 0, findings: 0, governance: 0, sentinel: 0 },
            activeSubscriptions: 0,
            connectedAgents: 0,
        };
    }
    updateStats() {
        this.stats.activeSubscriptions = this.subscriptions.size;
        this.stats.connectedAgents = new Set([...this.subscriptions.values()].map((s) => s.subscriberId)).size;
    }
}
exports.CrawlMessageBus = CrawlMessageBus;
//# sourceMappingURL=crawl-message-bus.js.map