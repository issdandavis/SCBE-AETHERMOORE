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
export type BlockedCategory = 'internet' | 'external_apis' | 'social_media' | 'unauthorized_devices';
export interface NetworkMessage {
    id: string;
    from: string;
    to: string;
    channel: NetworkChannel;
    payload: Record<string, unknown>;
    timestamp: number;
    delivered: boolean;
    error?: string;
}
/** Backward-compatible v2 message shape used by older Polly Pads tests. */
export interface LegacyNetworkMessage extends NetworkMessage {
    fromPadId: string;
    toPadId: string;
    signature: string;
}
export interface ClosedNetworkConfig {
    mode: 'closed' | 'restricted';
    allowedChannels: NetworkChannel[];
    meshFrequency: string;
    maxMessageSize: number;
    earthContactAvailable: boolean;
    earthDelayMinutes: number;
}
export declare const DEFAULT_CLOSED_CONFIG: ClosedNetworkConfig;
export declare const BLOCKED_NETWORKS: Record<BlockedCategory, string>;
export declare class ClosedNetwork {
    private config;
    private verifiedPads;
    private messageLog;
    private earthQueue;
    private inboxes;
    private outboundQueues;
    private disabledChannels;
    constructor(config?: Partial<ClosedNetworkConfig>);
    canUseChannel(channel: string): boolean;
    getChannelStatus(): Array<{
        channel: NetworkChannel;
        available: boolean;
        reason?: string;
    }>;
    registerPad(padId: string): void;
    deregisterPad(padId: string): void;
    isPadVerified(padId: string): boolean;
    getVerifiedPads(): string[];
    sendMessage(from: string, to: string, channel: NetworkChannel, payload: Record<string, unknown>): NetworkMessage;
    send(fromPadId: string, toPadId: string, channel: NetworkChannel, payload: Record<string, unknown>): LegacyNetworkMessage | null;
    receive(padId: string): LegacyNetworkMessage[];
    verifyMessage(message: LegacyNetworkMessage): boolean;
    setChannelEnabled(channel: NetworkChannel, enabled: boolean): void;
    broadcast(from: string, payload: Record<string, unknown>): NetworkMessage;
    setEarthContact(available: boolean, delayMinutes?: number): void;
    getEarthQueue(): NetworkMessage[];
    getStatus(padId: string): {
        totalSent: number;
        totalReceived: number;
        outboundQueueSize: number;
    };
    getStats(): {
        verifiedPads: number;
        totalMessages: number;
        deliveredMessages: number;
        failedMessages: number;
        queuedEarthMessages: number;
        earthContact: boolean;
    };
    getMessageLog(limit?: number): NetworkMessage[];
}
//# sourceMappingURL=closed-network.d.ts.map