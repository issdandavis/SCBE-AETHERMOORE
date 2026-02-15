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
/** Message channels for crawl coordination */
export type CrawlChannel = 'discovery' | 'status' | 'findings' | 'governance' | 'sentinel';
/** Crawl-specific event types */
export type CrawlEventType = 'url_found' | 'url_claimed' | 'url_completed' | 'url_failed' | 'heartbeat' | 'progress' | 'idle' | 'busy' | 'data_extracted' | 'page_analyzed' | 'link_graph_updated' | 'role_switch_request' | 'role_switch_approved' | 'role_switch_denied' | 'consensus_request' | 'consensus_vote' | 'safety_alert' | 'quarantine_notice' | 'anomaly_detected' | 'domain_blocked';
/** Priority for message ordering */
export type MessagePriority = 'critical' | 'high' | 'normal' | 'low';
/** A message on the crawl bus */
export interface CrawlMessage<T = unknown> {
    /** Unique message ID */
    readonly id: string;
    /** Kafka-style topic: scbe.crawl.{channel}.{event} */
    readonly topic: string;
    /** Parsed channel */
    readonly channel: CrawlChannel;
    /** Parsed event type */
    readonly event: CrawlEventType;
    /** Sending agent ID */
    readonly fromAgent: string;
    /** Target agent ID (undefined = broadcast) */
    readonly toAgent?: string;
    /** Message payload */
    readonly payload: T;
    /** Priority */
    readonly priority: MessagePriority;
    /** Monotonic sequence number per agent (replay protection) */
    readonly sequence: number;
    /** Unix timestamp */
    readonly timestamp: number;
    /** Optional correlation ID for request-response patterns */
    readonly correlationId?: string;
}
/** Subscription handle */
export interface Subscription {
    /** Unique subscription ID */
    readonly id: string;
    /** Topic pattern (supports * wildcard) */
    readonly pattern: string;
    /** Subscriber agent ID */
    readonly subscriberId: string;
    /** Unsubscribe */
    unsubscribe(): void;
}
/** Message handler callback */
export type MessageHandler<T = unknown> = (message: CrawlMessage<T>) => void;
/** Bus statistics */
export interface BusStats {
    /** Total messages published */
    totalPublished: number;
    /** Total messages delivered */
    totalDelivered: number;
    /** Messages per channel */
    channelCounts: Record<CrawlChannel, number>;
    /** Active subscriptions */
    activeSubscriptions: number;
    /** Connected agents */
    connectedAgents: number;
}
/** Build a Kafka-style topic string */
export declare function buildTopic(channel: CrawlChannel, event: CrawlEventType): string;
/** Parse a topic string into channel and event */
export declare function parseTopic(topic: string): {
    channel: CrawlChannel;
    event: CrawlEventType;
} | null;
/** Check if a topic matches a pattern (supports * wildcard) */
export declare function topicMatches(topic: string, pattern: string): boolean;
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
export declare class CrawlMessageBus {
    private subscriptions;
    private agentSequences;
    private messageLog;
    private maxLogSize;
    private stats;
    constructor(maxLogSize?: number);
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
    publish<T>(fromAgent: string, channel: CrawlChannel, event: CrawlEventType, payload: T, options?: {
        toAgent?: string;
        priority?: MessagePriority;
        correlationId?: string;
    }): CrawlMessage<T>;
    /**
     * Subscribe to messages matching a topic pattern.
     *
     * @param subscriberId - Agent ID of subscriber
     * @param pattern - Topic pattern (e.g., 'scbe.crawl.discovery.*' or '*')
     * @param handler - Callback for matching messages
     * @returns Subscription handle with unsubscribe()
     */
    subscribe<T = unknown>(subscriberId: string, pattern: string, handler: MessageHandler<T>): Subscription;
    /**
     * Get messages for a specific agent (direct + broadcast).
     */
    getMessagesForAgent(agentId: string, limit?: number): CrawlMessage[];
    /**
     * Get messages by channel.
     */
    getMessagesByChannel(channel: CrawlChannel, limit?: number): CrawlMessage[];
    /**
     * Get the current sequence number for an agent.
     */
    getAgentSequence(agentId: string): number;
    /**
     * Get bus statistics.
     */
    getStats(): BusStats;
    /**
     * Reset the bus (for testing).
     */
    reset(): void;
    private updateStats;
}
//# sourceMappingURL=crawl-message-bus.d.ts.map