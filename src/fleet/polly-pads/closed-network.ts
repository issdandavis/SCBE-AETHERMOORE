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
  }
}
