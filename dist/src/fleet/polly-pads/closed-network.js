"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ClosedNetwork = exports.BLOCKED_NETWORKS = exports.DEFAULT_CLOSED_CONFIG = void 0;
const crypto_1 = require("crypto");
exports.DEFAULT_CLOSED_CONFIG = {
    mode: 'closed',
    allowedChannels: ['local_squad_mesh', 'earth_deep_space', 'onboard_sensors', 'emergency_beacon'],
    meshFrequency: '437.5MHz',
    maxMessageSize: 65536,
    earthContactAvailable: false,
    earthDelayMinutes: Infinity,
};
exports.BLOCKED_NETWORKS = {
    internet: 'No internet on Mars',
    external_apis: 'No cloud services',
    social_media: 'No social media',
    unauthorized_devices: 'Only verified hardware',
};
class ClosedNetwork {
    config;
    verifiedPads = new Set();
    messageLog = [];
    earthQueue = [];
    // v2 compatibility state
    inboxes = new Map();
    outboundQueues = new Map();
    disabledChannels = new Set();
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_CLOSED_CONFIG, ...config };
    }
    canUseChannel(channel) {
        if (channel in exports.BLOCKED_NETWORKS)
            return false;
        if (this.disabledChannels.has(channel))
            return false;
        return this.config.allowedChannels.includes(channel);
    }
    getChannelStatus() {
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
    registerPad(padId) {
        this.verifiedPads.add(padId);
        if (!this.inboxes.has(padId))
            this.inboxes.set(padId, []);
        if (!this.outboundQueues.has(padId))
            this.outboundQueues.set(padId, []);
    }
    deregisterPad(padId) {
        this.verifiedPads.delete(padId);
        this.inboxes.delete(padId);
        this.outboundQueues.delete(padId);
    }
    isPadVerified(padId) {
        return this.verifiedPads.has(padId);
    }
    getVerifiedPads() {
        return Array.from(this.verifiedPads);
    }
    sendMessage(from, to, channel, payload) {
        const message = {
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
        }
        else if (channel === 'earth_deep_space') {
            if (!this.config.earthContactAvailable) {
                this.earthQueue.push(message);
                message.error = 'No Earth contact — message queued';
                this.messageLog.push(message);
                return message;
            }
            message.delivered = true;
        }
        else {
            message.delivered = true;
        }
        const payloadSize = JSON.stringify(payload).length;
        if (payloadSize > this.config.maxMessageSize) {
            message.delivered = false;
            message.error = `Message too large: ${payloadSize} > ${this.config.maxMessageSize}`;
        }
        this.messageLog.push(message);
        if (this.messageLog.length > 5000)
            this.messageLog = this.messageLog.slice(-2500);
        return message;
    }
    // v2 compatibility send API
    send(fromPadId, toPadId, channel, payload) {
        const sent = this.sendMessage(fromPadId, toPadId, channel, payload);
        if (sent.error && channel !== 'earth_deep_space')
            return null;
        const signature = (0, crypto_1.createHmac)('sha256', 'scbe-closed-network-v2')
            .update(JSON.stringify({ fromPadId, toPadId, channel, payload, timestamp: sent.timestamp }))
            .digest('hex');
        const legacy = {
            ...sent,
            fromPadId,
            toPadId,
            signature,
        };
        if (channel === 'local_squad_mesh') {
            if (toPadId === 'broadcast') {
                for (const pad of this.verifiedPads) {
                    if (pad === fromPadId)
                        continue;
                    this.inboxes.get(pad)?.push(legacy);
                }
            }
            else {
                this.inboxes.get(toPadId)?.push(legacy);
            }
        }
        if (channel === 'earth_deep_space') {
            if (!this.config.earthContactAvailable) {
                this.outboundQueues.get(fromPadId)?.push(legacy);
            }
            else {
                this.inboxes.get(toPadId)?.push(legacy);
            }
        }
        return legacy;
    }
    receive(padId) {
        const messages = this.inboxes.get(padId) ?? [];
        this.inboxes.set(padId, []);
        return messages;
    }
    verifyMessage(message) {
        const expected = (0, crypto_1.createHmac)('sha256', 'scbe-closed-network-v2')
            .update(JSON.stringify({
            fromPadId: message.fromPadId,
            toPadId: message.toPadId,
            channel: message.channel,
            payload: message.payload,
            timestamp: message.timestamp,
        }))
            .digest('hex');
        return message.signature === expected;
    }
    setChannelEnabled(channel, enabled) {
        if (enabled)
            this.disabledChannels.delete(channel);
        else
            this.disabledChannels.add(channel);
    }
    broadcast(from, payload) {
        return this.sendMessage(from, 'broadcast', 'local_squad_mesh', payload);
    }
    setEarthContact(available, delayMinutes) {
        this.config.earthContactAvailable = available;
        if (delayMinutes !== undefined)
            this.config.earthDelayMinutes = delayMinutes;
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
    getEarthQueue() {
        return [...this.earthQueue];
    }
    getStatus(padId) {
        const totalSent = this.messageLog.filter((m) => m.from === padId).length;
        const totalReceived = this.messageLog.filter((m) => m.to === padId || (m.to === 'broadcast' && m.from !== padId)).length;
        const outboundQueueSize = (this.outboundQueues.get(padId) ?? []).length;
        return { totalSent, totalReceived, outboundQueueSize };
    }
    getStats() {
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
    getMessageLog(limit = 50) {
        return this.messageLog.slice(-limit);
    }
}
exports.ClosedNetwork = ClosedNetwork;
//# sourceMappingURL=closed-network.js.map