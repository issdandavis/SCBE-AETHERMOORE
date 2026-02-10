"use strict";
/**
 * @file communications.ts
 * @module fleet/polly-pads/modes/communications
 * @layer L13
 * @component Communications Mode - Liaison & Reporting
 * @version 1.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.CommunicationsMode = void 0;
const base_mode_1 = require("./base-mode");
/**
 * Communications specialist mode.
 *
 * Handles Earth sync, squad messaging, and status reporting.
 * Critical for maintaining contact and reporting decisions.
 */
class CommunicationsMode extends base_mode_1.BaseMode {
    constructor() {
        super('communications');
    }
    onActivate() {
        if (!this.stateData.messageQueue) {
            this.stateData.messageQueue = [];
        }
        if (!this.stateData.sentMessages) {
            this.stateData.sentMessages = [];
        }
    }
    onDeactivate() {
        // Persist message queue
    }
    doExecuteAction(action, params) {
        switch (action) {
            case 'queue_message':
                return this.queueMessage(params);
            case 'send_status':
                return this.sendStatus(params);
            case 'check_earth_contact':
                return this.checkEarthContact(params);
            case 'broadcast_squad':
                return this.broadcastSquad(params);
            default:
                return {
                    success: false,
                    action,
                    data: {},
                    timestamp: Date.now(),
                    confidence: 0,
                    error: `Unknown communications action: ${action}`,
                };
        }
    }
    queueMessage(params) {
        const queue = this.stateData.messageQueue;
        const message = {
            id: `MSG-${Date.now().toString(36).toUpperCase()}`,
            recipient: params.recipient || 'earth',
            content: params.content || '',
            priority: params.priority || 'normal',
            queuedAt: Date.now(),
            status: 'queued',
        };
        queue.push(message);
        return {
            success: true,
            action: 'queue_message',
            data: message,
            timestamp: Date.now(),
            confidence: 1.0,
        };
    }
    sendStatus(params) {
        const report = {
            type: 'status_report',
            missionPhase: params.missionPhase || 'active',
            crewStatus: params.crewStatus || 'nominal',
            systemsStatus: params.systemsStatus || 'operational',
            generatedAt: Date.now(),
        };
        return {
            success: true,
            action: 'send_status',
            data: report,
            timestamp: Date.now(),
            confidence: 0.95,
        };
    }
    checkEarthContact(params) {
        const earthContact = this.stateData.earthContactAvailable ?? false;
        const delayMinutes = earthContact ? 12 : Infinity;
        return {
            success: true,
            action: 'check_earth_contact',
            data: {
                available: earthContact,
                delayMinutes,
                nextWindowEstimate: earthContact ? 'now' : 'unknown',
                queuedMessages: this.stateData.messageQueue?.length || 0,
            },
            timestamp: Date.now(),
            confidence: earthContact ? 0.9 : 0.6,
        };
    }
    broadcastSquad(params) {
        const message = params.message || '';
        return {
            success: true,
            action: 'broadcast_squad',
            data: {
                message,
                channel: 'local_squad_mesh',
                frequency: '437.5MHz',
                broadcastAt: Date.now(),
            },
            timestamp: Date.now(),
            confidence: 0.98,
        };
    }
}
exports.CommunicationsMode = CommunicationsMode;
//# sourceMappingURL=communications.js.map