/**
 * @file closed-network.ts
 * @module fleet/polly-pads/closed-network
 * @layer L13
 * @component Closed Network - Air-Gapped Communications
 * @version 1.0.0
 *
 * Air-gapped network for Mars/space/submarine operations.
 * Polly Pads can ONLY talk to verified peers in the same squad,
 * Earth (when available), and onboard sensors. NO internet access.
 */

/**
 * Allowed communication channels.
 */
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

import { createHmac, randomBytes } from 'crypto';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Allowed communication channels */
export type NetworkChannel =
  | 'local_squad_mesh'
  | 'earth_deep_space'
  | 'onboard_sensors'
  | 'emergency_beacon';

/**
 * Blocked network categories.
 */
export type BlockedCategory =
  | 'internet'
  | 'external_apis'
  | 'social_media'
  | 'unauthorized_devices';

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
export const DEFAULT_CLOSED_CONFIG: ClosedNetworkConfig = {
  mode: 'closed',
  allowedChannels: ['local_squad_mesh', 'earth_deep_space', 'onboard_sensors', 'emergency_beacon'],
  meshFrequency: '437.5MHz',
  maxMessageSize: 65536,
  earthContactAvailable: false,
  earthDelayMinutes: Infinity,
};

/**
 * All blocked categories with descriptions.
 */
export const BLOCKED_NETWORKS: Record<BlockedCategory, string> = {
  internet: 'No internet on Mars',
  external_apis: 'No cloud services',
  social_media: 'No social media',
  unauthorized_devices: 'Only verified hardware',
};

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
export class ClosedNetwork {
  private config: ClosedNetworkConfig;
  /** Verified pad IDs in the local mesh */
  private verifiedPads: Set<string> = new Set();
  /** Message log */
  private messageLog: NetworkMessage[] = [];
  /** Queued messages waiting for Earth contact */
  private earthQueue: NetworkMessage[] = [];

  constructor(config: Partial<ClosedNetworkConfig> = {}) {
    this.config = { ...DEFAULT_CLOSED_CONFIG, ...config };
  }

  // === Channel Management ===

  /**
   * Check if a channel is allowed.
   */
  canUseChannel(channel: string): boolean {
    // Check if it's a blocked category
    if (channel in BLOCKED_NETWORKS) {
      return false;
    }
    return this.config.allowedChannels.includes(channel as NetworkChannel);
  }

  /**
   * Get all allowed channels with status.
   */
  getChannelStatus(): Array<{ channel: NetworkChannel; available: boolean; reason?: string }> {
    return this.config.allowedChannels.map((ch) => {
      if (ch === 'earth_deep_space') {
        return {
          channel: ch,
          available: this.config.earthContactAvailable,
          reason: this.config.earthContactAvailable
            ? `${this.config.earthDelayMinutes}min delay`
            : 'No contact (behind planet or blackout)',
        };
      }
      return { channel: ch, available: true };
    });
  }

  // === Pad Verification ===

  /**
   * Register a verified pad in the mesh.
   */
  registerPad(padId: string): void {
    this.verifiedPads.add(padId);
  }

  /**
   * Remove a pad from the mesh.
   */
  deregisterPad(padId: string): void {
    this.verifiedPads.delete(padId);
  }

  /**
   * Check if a pad is verified.
   */
  isPadVerified(padId: string): boolean {
    return this.verifiedPads.has(padId);
  }

  /**
   * Get all verified pads.
   */
  getVerifiedPads(): string[] {
    return Array.from(this.verifiedPads);
  }

  // === Messaging ===

  /**
   * Send a message through the closed network.
   *
   * Validates channel availability, pad verification, and message size.
   */
  sendMessage(
    from: string,
    to: string,
    channel: NetworkChannel,
    payload: Record<string, unknown>
  ): NetworkMessage {
    const message: NetworkMessage = {
      id: `msg-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      from,
      to,
      channel,
      payload,
      timestamp: Date.now(),
      delivered: false,
    };

    // Validate channel
    if (!this.canUseChannel(channel)) {
      message.error = `Channel ${channel} is not available`;
      this.messageLog.push(message);
      return message;
    }

    // Validate sender is verified
    if (!this.verifiedPads.has(from)) {
      message.error = `Sender ${from} is not a verified pad`;
      this.messageLog.push(message);
      return message;
    }

    // Channel-specific validation
    if (channel === 'local_squad_mesh') {
      if (to !== 'broadcast' && !this.verifiedPads.has(to)) {
        message.error = `Recipient ${to} is not a verified pad`;
        this.messageLog.push(message);
        return message;
      }
      message.delivered = true;
    } else if (channel === 'earth_deep_space') {
      if (!this.config.earthContactAvailable) {
        // Queue for later
        this.earthQueue.push(message);
        message.error = 'No Earth contact — message queued';
        this.messageLog.push(message);
        return message;
      }
      message.delivered = true;
    } else if (channel === 'onboard_sensors') {
      message.delivered = true;
    } else if (channel === 'emergency_beacon') {
      // Emergency beacons always "send" (may not be received)
      message.delivered = true;
    }

    // Check message size
    const payloadSize = JSON.stringify(payload).length;
    if (payloadSize > this.config.maxMessageSize) {
      message.delivered = false;
      message.error = `Message too large: ${payloadSize} > ${this.config.maxMessageSize}`;
    }

    this.messageLog.push(message);

    // Keep log bounded
    if (this.messageLog.length > 5000) {
      this.messageLog = this.messageLog.slice(-2500);
    }

    return message;
  }

  /**
   * Broadcast a message to all verified pads in the squad.
   */
  broadcast(
    from: string,
    payload: Record<string, unknown>
  ): NetworkMessage {
    return this.sendMessage(from, 'broadcast', 'local_squad_mesh', payload);
  }

  // === Earth Contact ===

  /**
   * Set Earth contact availability.
   */
  setEarthContact(available: boolean, delayMinutes?: number): void {
    this.config.earthContactAvailable = available;
    if (delayMinutes !== undefined) {
      this.config.earthDelayMinutes = delayMinutes;
    }

    // Flush queued messages when contact restored
    if (available && this.earthQueue.length > 0) {
      for (const msg of this.earthQueue) {
        msg.delivered = true;
        msg.error = undefined;
      }
      this.earthQueue = [];
    }
  }

  /**
   * Get queued Earth messages.
   */
  getEarthQueue(): NetworkMessage[] {
    return [...this.earthQueue];
  }

  // === Stats ===

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
  } {
    const delivered = this.messageLog.filter((m) => m.delivered).length;
    return {
      verifiedPads: this.verifiedPads.size,
      totalMessages: this.messageLog.length,
      deliveredMessages: delivered,
      failedMessages: this.messageLog.length - delivered,
      queuedEarthMessages: this.earthQueue.length,
      earthContact: this.config.earthContactAvailable,
    };
  }

  /**
   * Get recent message log.
   */
  getMessageLog(limit: number = 50): NetworkMessage[] {
    return this.messageLog.slice(-limit);
/** Blocked channel categories */
export type BlockedChannel = 'internet' | 'external_apis' | 'social_media' | 'unauthorized_devices';

/** Network message between pads */
export interface NetworkMessage {
  id: string;
  fromPadId: string;
  toPadId: string | 'broadcast';
  channel: NetworkChannel;
  payload: unknown;
  /** HMAC-SHA256 of payload for integrity */
  hmac: string;
  timestamp: number;
  /** Estimated one-way latency in ms */
  latencyMs: number;
}

/** Channel configuration */
export interface ChannelConfig {
  channel: NetworkChannel;
  enabled: boolean;
  /** Simulated latency range [min, max] in ms */
  latencyRange: [number, number];
  /** Max payload size in bytes */
  maxPayloadBytes: number;
  /** Whether channel requires governance approval */
  requiresApproval: boolean;
}

/** Network status for a pad */
export interface NetworkStatus {
  padId: string;
  channels: Record<NetworkChannel, boolean>;
  /** Whether Earth contact is currently available */
  earthContactAvailable: boolean;
  /** Messages queued for sending */
  outboundQueueSize: number;
  /** Messages received and unprocessed */
  inboundQueueSize: number;
  /** Total messages sent */
  totalSent: number;
  /** Total messages received */
  totalReceived: number;
}

// ═══════════════════════════════════════════════════════════════
// Default Channel Configurations
// ═══════════════════════════════════════════════════════════════

export const DEFAULT_CHANNELS: Record<NetworkChannel, ChannelConfig> = {
  local_squad_mesh: {
    channel: 'local_squad_mesh',
    enabled: true,
    latencyRange: [10, 100],          // 10-100ms local UHF
    maxPayloadBytes: 64 * 1024,       // 64KB
    requiresApproval: false,
  },
  earth_deep_space: {
    channel: 'earth_deep_space',
    enabled: true,
    latencyRange: [480_000, 1_200_000], // 8-20 minutes Mars delay
    maxPayloadBytes: 1024 * 1024,       // 1MB
    requiresApproval: true,             // Needs governance to use limited bandwidth
  },
  onboard_sensors: {
    channel: 'onboard_sensors',
    enabled: true,
    latencyRange: [1, 10],             // 1-10ms wired
    maxPayloadBytes: 10 * 1024 * 1024, // 10MB (images, spectrometer data)
    requiresApproval: false,
  },
  emergency_beacon: {
    channel: 'emergency_beacon',
    enabled: true,
    latencyRange: [480_000, 1_200_000], // Same as deep space
    maxPayloadBytes: 256,               // Tiny SOS packet
    requiresApproval: true,             // DR-level only
  },
};

// ═══════════════════════════════════════════════════════════════
// Closed Network
// ═══════════════════════════════════════════════════════════════

/**
 * ClosedNetwork — Air-gapped communication layer for Polly Pad squads.
 *
 * Enforces channel restrictions, simulates latency, and provides
 * integrity verification for all inter-pad messages.
 */
export class ClosedNetwork {
  private channels: Map<NetworkChannel, ChannelConfig>;
  private outboundQueue: Map<string, NetworkMessage[]> = new Map(); // padId -> messages
  private inboundQueue: Map<string, NetworkMessage[]> = new Map();
  private registeredPads: Set<string> = new Set();
  private hmacKey: Buffer;
  private _earthContactAvailable: boolean = false;
  private stats: Map<string, { sent: number; received: number }> = new Map();

  constructor(channelConfigs?: Partial<Record<NetworkChannel, Partial<ChannelConfig>>>) {
    // Initialize channels with defaults
    this.channels = new Map();
    for (const [ch, config] of Object.entries(DEFAULT_CHANNELS)) {
      const override = channelConfigs?.[ch as NetworkChannel];
      this.channels.set(ch as NetworkChannel, { ...config, ...override });
    }
    // Shared HMAC key for message integrity within the squad
    this.hmacKey = randomBytes(32);
  }

  /** Register a pad on the network */
  registerPad(padId: string): void {
    this.registeredPads.add(padId);
    this.outboundQueue.set(padId, []);
    this.inboundQueue.set(padId, []);
    this.stats.set(padId, { sent: 0, received: 0 });
  }

  /** Unregister a pad from the network */
  unregisterPad(padId: string): void {
    this.registeredPads.delete(padId);
    this.outboundQueue.delete(padId);
    this.inboundQueue.delete(padId);
    this.stats.delete(padId);
  }

  /** Set Earth contact availability */
  setEarthContact(available: boolean): void {
    this._earthContactAvailable = available;
  }

  /** Whether Earth contact is up */
  get earthContactAvailable(): boolean {
    return this._earthContactAvailable;
  }

  /**
   * Send a message from one pad to another (or broadcast).
   *
   * Returns the message if sent successfully, null if blocked.
   */
  send(
    fromPadId: string,
    toPadId: string | 'broadcast',
    channel: NetworkChannel,
    payload: unknown
  ): NetworkMessage | null {
    // Verify sender is registered
    if (!this.registeredPads.has(fromPadId)) {
      return null;
    }

    // Check channel is enabled
    const config = this.channels.get(channel);
    if (!config?.enabled) {
      return null;
    }

    // Check Earth contact for deep space / beacon
    if (
      (channel === 'earth_deep_space' || channel === 'emergency_beacon') &&
      !this._earthContactAvailable
    ) {
      // Queue for later
      const msg = this.createMessage(fromPadId, toPadId, channel, payload, config);
      const queue = this.outboundQueue.get(fromPadId) ?? [];
      queue.push(msg);
      this.outboundQueue.set(fromPadId, queue);
      return msg;
    }

    // Verify recipient is registered (unless broadcast)
    if (toPadId !== 'broadcast' && !this.registeredPads.has(toPadId)) {
      return null;
    }

    const msg = this.createMessage(fromPadId, toPadId, channel, payload, config);

    // Deliver
    if (toPadId === 'broadcast') {
      for (const padId of this.registeredPads) {
        if (padId !== fromPadId) {
          const queue = this.inboundQueue.get(padId) ?? [];
          queue.push(msg);
          this.inboundQueue.set(padId, queue);
          this.updateStats(padId, 'received');
        }
      }
    } else {
      const queue = this.inboundQueue.get(toPadId) ?? [];
      queue.push(msg);
      this.inboundQueue.set(toPadId, queue);
      this.updateStats(toPadId, 'received');
    }

    this.updateStats(fromPadId, 'sent');
    return msg;
  }

  /** Receive all pending messages for a pad */
  receive(padId: string): NetworkMessage[] {
    const queue = this.inboundQueue.get(padId) ?? [];
    this.inboundQueue.set(padId, []);
    return queue;
  }

  /** Drain outbound queue (when contact is restored) */
  drainOutbound(padId: string): NetworkMessage[] {
    const queue = this.outboundQueue.get(padId) ?? [];
    this.outboundQueue.set(padId, []);
    return queue;
  }

  /** Verify message integrity via HMAC */
  verifyMessage(msg: NetworkMessage): boolean {
    const expected = this.computeHmac(msg.fromPadId, msg.toPadId, msg.payload, msg.timestamp);
    return expected === msg.hmac;
  }

  /** Get network status for a pad */
  getStatus(padId: string): NetworkStatus {
    const padStats = this.stats.get(padId) ?? { sent: 0, received: 0 };
    const channels: Record<NetworkChannel, boolean> = {} as Record<NetworkChannel, boolean>;
    for (const [ch, config] of this.channels) {
      channels[ch] = config.enabled;
    }
    return {
      padId,
      channels,
      earthContactAvailable: this._earthContactAvailable,
      outboundQueueSize: (this.outboundQueue.get(padId) ?? []).length,
      inboundQueueSize: (this.inboundQueue.get(padId) ?? []).length,
      totalSent: padStats.sent,
      totalReceived: padStats.received,
    };
  }

  /** Enable/disable a channel */
  setChannelEnabled(channel: NetworkChannel, enabled: boolean): void {
    const config = this.channels.get(channel);
    if (config) config.enabled = enabled;
  }

  /** Get all registered pad IDs */
  getRegisteredPads(): string[] {
    return Array.from(this.registeredPads);
  }

  // ─── Internal ───

  private createMessage(
    fromPadId: string,
    toPadId: string | 'broadcast',
    channel: NetworkChannel,
    payload: unknown,
    config: ChannelConfig
  ): NetworkMessage {
    const [minLat, maxLat] = config.latencyRange;
    const latencyMs = minLat + Math.random() * (maxLat - minLat);
    const timestamp = Date.now();
    return {
      id: `msg-${Date.now().toString(36)}-${randomBytes(4).toString('hex')}`,
      fromPadId,
      toPadId,
      channel,
      payload,
      hmac: this.computeHmac(fromPadId, toPadId, payload, timestamp),
      timestamp,
      latencyMs: Math.round(latencyMs),
    };
  }

  private computeHmac(
    from: string,
    to: string | 'broadcast',
    payload: unknown,
    ts: number
  ): string {
    const data = `${from}:${to}:${JSON.stringify(payload)}:${ts}`;
    return createHmac('sha256', this.hmacKey).update(data).digest('hex');
  }

  private updateStats(padId: string, type: 'sent' | 'received'): void {
    const s = this.stats.get(padId);
    if (s) s[type]++;
  }
}
