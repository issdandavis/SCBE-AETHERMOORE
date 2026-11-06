import crypto from 'node:crypto';
import type { AgentBusEvent, AgentBusResult } from './index.js';
import { decompose, scoreDialogue } from './semantic-bridge.js';

export interface LocalEventResultOptions {
  eventIndex?: number;
  seriesId?: string;
  startedAt?: string;
}

function sha256(value: string): string {
  return crypto.createHash('sha256').update(value, 'utf8').digest('hex');
}

export function createEventReceiptId(
  event: AgentBusEvent,
  eventIndex: number,
  startedAt: string
): string {
  const seed = JSON.stringify([
    eventIndex,
    startedAt,
    String(event.seriesId || ''),
    String(event.task || ''),
  ]);
  return `evt_${sha256(seed).slice(0, 24)}`;
}

/**
 * Produce the package-native event receipt used when no registered tool was
 * requested. This deliberately records intake without pretending that a model
 * or shell command ran. Raw operationCommand values are hashed and refused;
 * executable work must name a registered tool.
 */
export function createLocalEventResult(
  event: AgentBusEvent,
  options: LocalEventResultOptions = {}
): AgentBusResult {
  const eventIndex = options.eventIndex || 1;
  const startedAt = options.startedAt || new Date().toISOString();
  const finishedAt = new Date().toISOString();
  const task = String(event.task || '').trim();
  const operationCommand = String(event.operationCommand || '').trim();
  const seriesId = String(event.seriesId || options.seriesId || `node-event-${eventIndex}`);
  const receiptId = createEventReceiptId({ ...event, task, seriesId }, eventIndex, startedAt);
  const taskHash = sha256(task);
  const decomposition = decompose(task);
  const common = {
    schema_version: 'scbe-agentbus-node-result-v1' as const,
    event_index: eventIndex,
    started_at: startedAt,
    finished_at: finishedAt,
    receipt_id: receiptId,
    event: {
      task_sha256: taskHash,
      task_chars: task.length,
      series_id: seriesId,
      operation_command_chars: operationCommand.length,
    },
    ...(decomposition.tokenCount > 0 ? { semantic: decomposition } : {}),
    ...(decomposition.discourseProfile
      ? { discourse_profile: decomposition.discourseProfile }
      : {}),
    ...(decomposition.discourseProfile ? { dialogue_score: scoreDialogue(task) } : {}),
  };

  if (operationCommand) {
    const reason = 'operation_command_requires_registered_tool';
    return {
      ...common,
      ok: false,
      exit_code: 403,
      stderr_tail:
        'Raw operationCommand execution is disabled; register a governed CLI tool and set event.tool.',
      reason,
      result: {
        schema_version: 'scbe_agentbus_local_receipt_v1',
        receipt_id: receiptId,
        status: 'refused',
        reason,
        operation_command_sha256: sha256(operationCommand),
      },
    };
  }

  const reason = 'accepted_local_receipt';
  return {
    ...common,
    ok: true,
    exit_code: 0,
    stderr_tail: '',
    reason,
    result: {
      schema_version: 'scbe_agentbus_local_receipt_v1',
      receipt_id: receiptId,
      status: 'accepted',
      mode: 'local_receipt',
      task_type: String(event.taskType || 'general'),
      privacy: String(event.privacy || 'local_only'),
      dispatch: {
        requested: event.dispatch !== false,
        provider: String(event.dispatchProvider || 'offline'),
        performed: false,
      },
      next_action:
        'Route the accepted event through a registered tool or a connected conversational runtime.',
    },
  };
}
