/**
 * @layer Layer 13, Layer 14
 * @component Polly Pads — Closed Network (Air-Gapped)
 * @version 1.0.0
 *
 * Air-gapped network layer for autonomous operations (Mars, submarine,
 * disaster response). Polly Pads communicate ONLY through explicitly
 * allowed channels — no internet, no cloud APIs.
 *
 * Allowed channels:
 *   local_squad_mesh   — UHF radio to other verified pads
 *   earth_deep_space   — When contact available (8-20 min delay)
 *   onboard_sensors    — Direct wired rover instruments
 *   emergency_beacon   — SOS signal
 *
 * All external access goes through SCBE governance.
 */
/** Allowed communication channels */
export type NetworkChannel = 'local_squad_mesh' | 'earth_deep_space' | 'onboard_sensors' | 'emergency_beacon';
/**
 * Blocked network categories.
 */
export type BlockedCategory = 'internet' | 'external_apis' | 'social_media' | 'unauthorized_devices';
/**
 * Network message exchanged between pads.
 */
export interface NetworkMessage {
    /** Unique message ID */
    id: string;
    /** Sender pad ID */
    from: string;
    /** Recipient pad ID or 'broadcast' */
    to: string;
    /** Communication channel used */
    channel: NetworkChannel;
    /** Message payload */
    payload: Record<string, unknown>;
    /** Timestamp */
    timestamp: number;
    /** Whether the message was delivered */
    delivered: boolean;
    /** Delivery error if any */
    error?: string;
}
/**
 * Network configuration.
 */
export interface ClosedNetworkConfig {
    /** Network mode */
    mode: 'closed' | 'restricted';
    /** Allowed channels */
    allowedChannels: NetworkChannel[];
    /** UHF mesh frequency */
    meshFrequency: string;
    /** Maximum message size in bytes */
    maxMessageSize: number;
    /** Whether Earth contact is currently available */
    earthContactAvailable: boolean;
    /** Communication delay to Earth in minutes */
    earthDelayMinutes: number;
}
/**
 * Default closed network configuration (Mars scenario).
 */
export declare const DEFAULT_CLOSED_CONFIG: ClosedNetworkConfig;
/**
 * All blocked categories with descriptions.
 */
export declare const BLOCKED_NETWORKS: Record<BlockedCategory, string>;
/**
 * ClosedNetwork — Air-gapped network for autonomous operations.
 *
 * Implements network isolation where Polly Pads can only communicate through:
 * 1. Local squad mesh (UHF radio to other verified pads)
 * 2. Earth deep-space link (when available, 8-20 min delay)
 * 3. Onboard sensors (direct wired connection)
 * 4. Emergency beacon (SOS to Earth)
 *
 * @example
 * ```typescript
 * const network = new ClosedNetwork();
 *
 * // Check if a channel is available
 * network.canUseChannel('local_squad_mesh'); // true
 * network.canUseChannel('internet');          // false — blocked
 *
 * // Send a message to another pad in the squad
 * network.sendMessage('ALPHA-001', 'BETA-001', 'local_squad_mesh', {
 *   type: 'crisis_alert',
 *   component: 'wheel_motor_2',
 * });
 * ```
 */
export declare class ClosedNetwork {
    private config;
    /** Verified pad IDs in the local mesh */
    private verifiedPads;
    /** Message log */
    private messageLog;
    /** Queued messages waiting for Earth contact */
    private earthQueue;
    constructor(config?: Partial<ClosedNetworkConfig>);
    /**
     * Check if a channel is allowed.
     */
    canUseChannel(channel: string): boolean;
    /**
     * Get all allowed channels with status.
     */
    getChannelStatus(): Array<{
        channel: NetworkChannel;
        available: boolean;
        reason?: string;
    }>;
    /**
     * Register a verified pad in the mesh.
     */
    registerPad(padId: string): void;
    /**
     * Remove a pad from the mesh.
     */
    deregisterPad(padId: string): void;
    /**
     * Check if a pad is verified.
     */
    isPadVerified(padId: string): boolean;
    /**
     * Get all verified pads.
     */
    getVerifiedPads(): string[];
    /**
     * Send a message through the closed network.
     *
     * Validates channel availability, pad verification, and message size.
     */
    sendMessage(from: string, to: string, channel: NetworkChannel, payload: Record<string, unknown>): NetworkMessage;
    /**
     * Broadcast a message to all verified pads in the squad.
     */
    broadcast(from: string, payload: Record<string, unknown>): NetworkMessage;
    /**
     * Set Earth contact availability.
     */
    setEarthContact(available: boolean, delayMinutes?: number): void;
    /**
     * Get queued Earth messages.
     */
    getEarthQueue(): NetworkMessage[];
    /**
     * Get network statistics.
     */
    getStats(): {
        verifiedPads: number;
        totalMessages: number;
        deliveredMessages: number;
        failedMessages: number;
        queuedEarthMessages: number;
        earthContact: boolean;
    };
    /**
     * Get recent message log.
     */
    getMessageLog(limit?: number): NetworkMessage[];
}
//# sourceMappingURL=closed-network.d.ts.map