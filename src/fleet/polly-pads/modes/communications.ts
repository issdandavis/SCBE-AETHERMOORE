/**
 * @file communications.ts
 * @module fleet/polly-pads/modes/communications
 * @layer L13
 * @component Communications Mode - Liaison & Reporting
 * @version 1.0.0
 */

import { BaseMode } from './base-mode';
import { ModeActionResult } from './types';

/**
 * Communications specialist mode.
 *
 * Handles Earth sync, squad messaging, and status reporting.
 * Critical for maintaining contact and reporting decisions.
 */
export class CommunicationsMode extends BaseMode {
  constructor() {
    super('communications');
  }

  protected onActivate(): void {
    if (!this.stateData.messageQueue) {
      this.stateData.messageQueue = [];
    }
    if (!this.stateData.sentMessages) {
      this.stateData.sentMessages = [];
    }
  }

  protected onDeactivate(): void {
    // Persist message queue
  }

  protected doExecuteAction(
    action: string,
    params: Record<string, unknown>
  ): ModeActionResult {
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

  private queueMessage(params: Record<string, unknown>): ModeActionResult {
    const queue = this.stateData.messageQueue as Array<Record<string, unknown>>;
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

  private sendStatus(params: Record<string, unknown>): ModeActionResult {
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

  private checkEarthContact(params: Record<string, unknown>): ModeActionResult {
    const earthContact = (this.stateData.earthContactAvailable as boolean) ?? false;
    const delayMinutes = earthContact ? 12 : Infinity;

    return {
      success: true,
      action: 'check_earth_contact',
      data: {
        available: earthContact,
        delayMinutes,
        nextWindowEstimate: earthContact ? 'now' : 'unknown',
        queuedMessages: (this.stateData.messageQueue as Array<unknown>)?.length || 0,
      },
      timestamp: Date.now(),
      confidence: earthContact ? 0.9 : 0.6,
    };
  }

  private broadcastSquad(params: Record<string, unknown>): ModeActionResult {
    const message = params.message as string || '';

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
