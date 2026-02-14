import { createHmac } from 'crypto';
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


// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Allowed communication channels */
export type NetworkChannel =
  | 'local_squad_mesh'
  | 'earth_deep_space'
  | 'onboard_sensors'
  | 'emergency_beacon';

export type BlockedCategory =
  | 'internet'
  | 'external_apis'
  | 'social_media'
  | 'unauthorized_devices';

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

export const DEFAULT_CLOSED_CONFIG: ClosedNetworkConfig = {
  mode: 'closed',
  allowedChannels: ['local_squad_mesh', 'earth_deep_space', 'onboard_sensors', 'emergency_beacon'],
  meshFrequency: '437.5MHz',
  maxMessageSize: 65536,
  earthContactAvailable: false,
  earthDelayMinutes: Infinity,
};

export const BLOCKED_NETWORKS: Record<BlockedCategory, string> = {
  internet: 'No internet on Mars',
  external_apis: 'No cloud services',
  social_media: 'No social media',
  unauthorized_devices: 'Only verified hardware',
};

export class ClosedNetwork {
  private config: ClosedNetworkConfig;
  private verifiedPads: Set<string> = new Set();
  private messageLog: NetworkMessage[] = [];
  private earthQueue: NetworkMessage[] = [];

  // v2 compatibility state
  private inboxes: Map<string, LegacyNetworkMessage[]> = new Map();
  private outboundQueues: Map<string, LegacyNetworkMessage[]> = new Map();
  private disabledChannels: Set<NetworkChannel> = new Set();

  constructor(config: Partial<ClosedNetworkConfig> = {}) {
    this.config = { ...DEFAULT_CLOSED_CONFIG, ...config };
  }

  canUseChannel(channel: string): boolean {
    if (channel in BLOCKED_NETWORKS) return false;
    if (this.disabledChannels.has(channel as NetworkChannel)) return false;
    return this.config.allowedChannels.includes(channel as NetworkChannel);
  }

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
      return { channel: ch, available: !this.disabledChannels.has(ch) };
    });
  }

  registerPad(padId: string): void {
    this.verifiedPads.add(padId);
    if (!this.inboxes.has(padId)) this.inboxes.set(padId, []);
    if (!this.outboundQueues.has(padId)) this.outboundQueues.set(padId, []);
  }

  deregisterPad(padId: string): void {
    this.verifiedPads.delete(padId);
    this.inboxes.delete(padId);
    this.outboundQueues.delete(padId);
  }

  isPadVerified(padId: string): boolean {
    return this.verifiedPads.has(padId);
  }

  getVerifiedPads(): string[] {
    return Array.from(this.verifiedPads);
  }

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

    if (!this.canUseChannel(channel)) {
      message.error = `Channel ${channel} is not available`;
      this.messageLog.push(message);
      return message;
    }

    if (!this.verifiedPads.has(from)) {
      message.error = `Sender ${from} is not a verified pad`;
      this.messageLog.push(message);
      return message;
    }

    if (channel === 'local_squad_mesh') {
      if (to !== 'broadcast' && !this.verifiedPads.has(to)) {
        message.error = `Recipient ${to} is not a verified pad`;
        this.messageLog.push(message);
        return message;
      }
      message.delivered = true;
    } else if (channel === 'earth_deep_space') {
      if (!this.config.earthContactAvailable) {
        this.earthQueue.push(message);
        message.error = 'No Earth contact — message queued';
        this.messageLog.push(message);
        return message;
      }
      message.delivered = true;
    } else {
      message.delivered = true;
    }

    const payloadSize = JSON.stringify(payload).length;
    if (payloadSize > this.config.maxMessageSize) {
      message.delivered = false;
      message.error = `Message too large: ${payloadSize} > ${this.config.maxMessageSize}`;
    }

    this.messageLog.push(message);
    if (this.messageLog.length > 5000) this.messageLog = this.messageLog.slice(-2500);
    return message;
  }

  // v2 compatibility send API
  send(
    fromPadId: string,
    toPadId: string,
    channel: NetworkChannel,
    payload: Record<string, unknown>
  ): LegacyNetworkMessage | null {
    const sent = this.sendMessage(fromPadId, toPadId, channel, payload);
    if (sent.error && channel !== 'earth_deep_space') return null;

    const signature = createHmac('sha256', 'scbe-closed-network-v2')
      .update(JSON.stringify({ fromPadId, toPadId, channel, payload, timestamp: sent.timestamp }))
      .digest('hex');

    const legacy: LegacyNetworkMessage = {
      ...sent,
      fromPadId,
      toPadId,
      signature,
    };

    if (channel === 'local_squad_mesh') {
      if (toPadId === 'broadcast') {
        for (const pad of this.verifiedPads) {
          if (pad === fromPadId) continue;
          this.inboxes.get(pad)?.push(legacy);
        }
      } else {
        this.inboxes.get(toPadId)?.push(legacy);
      }
    }

    if (channel === 'earth_deep_space') {
      if (!this.config.earthContactAvailable) {
        this.outboundQueues.get(fromPadId)?.push(legacy);
      } else {
        this.inboxes.get(toPadId)?.push(legacy);
      }
    }

    return legacy;
  }

  receive(padId: string): LegacyNetworkMessage[] {
    const messages = this.inboxes.get(padId) ?? [];
    this.inboxes.set(padId, []);
    return messages;
  }

  verifyMessage(message: LegacyNetworkMessage): boolean {
    const expected = createHmac('sha256', 'scbe-closed-network-v2')
      .update(
        JSON.stringify({
          fromPadId: message.fromPadId,
          toPadId: message.toPadId,
          channel: message.channel,
          payload: message.payload,
          timestamp: message.timestamp,
        })
      )
      .digest('hex');
    return message.signature === expected;
  }

  setChannelEnabled(channel: NetworkChannel, enabled: boolean): void {
    if (enabled) this.disabledChannels.delete(channel);
    else this.disabledChannels.add(channel);
  }

  broadcast(from: string, payload: Record<string, unknown>): NetworkMessage {
    return this.sendMessage(from, 'broadcast', 'local_squad_mesh', payload);
  }

  setEarthContact(available: boolean, delayMinutes?: number): void {
    this.config.earthContactAvailable = available;
    if (delayMinutes !== undefined) this.config.earthDelayMinutes = delayMinutes;

    if (available && this.earthQueue.length > 0) {
      for (const msg of this.earthQueue) {
        msg.delivered = true;
        msg.error = undefined;
      }
      this.earthQueue = [];

      for (const [sender, queued] of this.outboundQueues.entries()) {
        for (const msg of queued) {
          if (msg.toPadId !== 'broadcast') {
            this.inboxes.get(msg.toPadId)?.push(msg);
          }
        }
        this.outboundQueues.set(sender, []);
      }
    }
  }

  getEarthQueue(): NetworkMessage[] {
    return [...this.earthQueue];
  }

  getStatus(padId: string): { totalSent: number; totalReceived: number; outboundQueueSize: number } {
    const totalSent = this.messageLog.filter((m) => m.from === padId).length;
    const totalReceived = this.messageLog.filter(
      (m) => m.to === padId || (m.to === 'broadcast' && m.from !== padId)
    ).length;
    const outboundQueueSize = (this.outboundQueues.get(padId) ?? []).length;
    return { totalSent, totalReceived, outboundQueueSize };
  }

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

  getMessageLog(limit = 50): NetworkMessage[] {
    return this.messageLog.slice(-limit);
  }
}
