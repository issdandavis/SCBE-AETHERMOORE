/**
 * @file handoff-packet.ts
 * @module agent-bus/handoff-packet
 * @layer Fleet coordination
 * @component HandoffPacket — governance-stamped agent dispatch envelope
 *
 * Models task handoffs as a physics juggling system:
 *   balls  = HandoffPackets (tasks in flight)
 *   hands  = agents (holders/catchers)
 *   throws = handoffs between agents
 *   arcs   = deadline windows
 *   drops  = failures
 *
 * Every state transition returns a new immutable packet; no mutation in place.
 * The receipt chain records who touched the packet and when at each hop.
 */

export type HandoffFlightState =
  | 'HELD' // created, not yet dispatched
  | 'THROWN' // dispatched to a target, awaiting catch
  | 'CAUGHT' // target agent acknowledged receipt
  | 'VALIDATING' // target agent is verifying the payload
  | 'DONE' // delivered; task complete
  | 'DROPPED'; // failure; task not delivered

export type HandoffAuthority =
  | 'auto' // system-generated, no human in loop
  | 'keeper' // keeper agent authorized
  | 'operator' // human operator authorized
  | 'governance'; // governance gate required and passed

export type HandoffPriority = 'routine' | 'elevated' | 'urgent' | 'critical';

export interface HandoffMission {
  task: string;
  zone_id?: string;
  station_id?: string;
  target_lane?: string;
  payload?: Record<string, unknown>;
}

export interface HandoffReceipt {
  from_state: HandoffFlightState;
  to_state: HandoffFlightState;
  agent_id?: string;
  stamped_at: string;
  note?: string;
}

export interface HandoffPacket {
  readonly schema_version: 'scbe_handoff_v1';
  readonly packet_id: string;
  readonly created_at: string;
  readonly mission: HandoffMission;
  readonly state: HandoffFlightState;
  readonly priority: HandoffPriority;
  readonly authority: HandoffAuthority;
  readonly issuer_id: string;
  readonly holder_id?: string;
  readonly target_id?: string;
  readonly deadline_at?: string;
  readonly receipts: HandoffReceipt[];
  readonly result?: unknown;
  readonly drop_reason?: string;
}

export interface HandoffOptions {
  now?: string;
  packetId?: string;
  priority?: HandoffPriority;
  authority?: HandoffAuthority;
  deadlineAt?: string;
}

export interface HandoffValidation {
  valid: boolean;
  expired: boolean;
  state: HandoffFlightState;
  ms_until_deadline?: number;
  errors: string[];
}

export interface HandoffSummary {
  packet_id: string;
  state: HandoffFlightState;
  priority: HandoffPriority;
  authority: HandoffAuthority;
  issuer_id: string;
  holder_id?: string;
  target_id?: string;
  task: string;
  hop_count: number;
  created_at: string;
  last_receipt_at?: string;
  deadline_at?: string;
  expired: boolean;
  drop_reason?: string;
}

let _counter = 0;

function nextId(prefix: string, now: string): string {
  _counter = (_counter + 1) % 100_000;
  const ts = now.replace(/[-:.TZ]/g, '').slice(0, 14);
  return `${prefix}-${ts}-${String(_counter).padStart(5, '0')}`;
}

function stamp(
  packet: HandoffPacket,
  toState: HandoffFlightState,
  agentId: string | undefined,
  now: string,
  note?: string
): HandoffPacket {
  const receipt: HandoffReceipt = {
    from_state: packet.state,
    to_state: toState,
    stamped_at: now,
    ...(agentId !== undefined ? { agent_id: agentId } : {}),
    ...(note !== undefined ? { note } : {}),
  };
  return { ...packet, state: toState, receipts: [...packet.receipts, receipt] };
}

function isExpiredAt(packet: HandoffPacket, now: string): boolean {
  if (!packet.deadline_at) return false;
  return now >= packet.deadline_at;
}

// ─── Public API ──────────────────────────────────────────────────────────────

export function createHandoff(
  issuerId: string,
  mission: HandoffMission,
  opts: HandoffOptions = {}
): HandoffPacket {
  const now = opts.now ?? new Date().toISOString();
  const packetId = opts.packetId ?? nextId('hp', now);
  const receipt: HandoffReceipt = {
    from_state: 'HELD',
    to_state: 'HELD',
    agent_id: issuerId,
    stamped_at: now,
    note: 'created',
  };
  return {
    schema_version: 'scbe_handoff_v1',
    packet_id: packetId,
    created_at: now,
    mission,
    state: 'HELD',
    priority: opts.priority ?? 'routine',
    authority: opts.authority ?? 'auto',
    issuer_id: issuerId,
    holder_id: issuerId,
    target_id: undefined,
    deadline_at: opts.deadlineAt,
    receipts: [receipt],
    result: undefined,
    drop_reason: undefined,
  };
}

export function throwHandoff(
  packet: HandoffPacket,
  targetId: string,
  opts: { now?: string; note?: string } = {}
): HandoffPacket {
  if (packet.state !== 'HELD') {
    throw new Error(`throwHandoff: packet must be HELD, got ${packet.state}`);
  }
  const now = opts.now ?? new Date().toISOString();
  return stamp(
    { ...packet, target_id: targetId },
    'THROWN',
    packet.holder_id,
    now,
    opts.note ?? `thrown to ${targetId}`
  );
}

export function catchHandoff(
  packet: HandoffPacket,
  agentId: string,
  opts: { now?: string; note?: string } = {}
): HandoffPacket {
  if (packet.state !== 'THROWN') {
    throw new Error(`catchHandoff: packet must be THROWN, got ${packet.state}`);
  }
  const now = opts.now ?? new Date().toISOString();
  return stamp(
    { ...packet, holder_id: agentId },
    'CAUGHT',
    agentId,
    now,
    opts.note ?? `caught by ${agentId}`
  );
}

export function validateHandoff(
  packet: HandoffPacket,
  opts: { now?: string; note?: string } = {}
): { packet: HandoffPacket; validation: HandoffValidation } {
  if (packet.state !== 'CAUGHT') {
    throw new Error(`validateHandoff: packet must be CAUGHT, got ${packet.state}`);
  }
  const now = opts.now ?? new Date().toISOString();
  const expired = isExpiredAt(packet, now);
  const errors: string[] = [];
  if (expired) errors.push('deadline exceeded');
  if (!packet.mission.task.trim()) errors.push('empty task');

  const msUntilDeadline =
    packet.deadline_at && !expired
      ? new Date(packet.deadline_at).getTime() - new Date(now).getTime()
      : undefined;

  const validation: HandoffValidation = {
    valid: errors.length === 0,
    expired,
    state: 'VALIDATING',
    errors,
    ...(msUntilDeadline !== undefined ? { ms_until_deadline: msUntilDeadline } : {}),
  };

  const next = stamp(packet, 'VALIDATING', packet.holder_id, now, opts.note);
  return { packet: next, validation };
}

export function completeHandoff(
  packet: HandoffPacket,
  result: unknown,
  opts: { now?: string; note?: string } = {}
): HandoffPacket {
  if (packet.state !== 'VALIDATING') {
    throw new Error(`completeHandoff: packet must be VALIDATING, got ${packet.state}`);
  }
  const now = opts.now ?? new Date().toISOString();
  return stamp({ ...packet, result }, 'DONE', packet.holder_id, now, opts.note ?? 'task complete');
}

export function dropHandoff(
  packet: HandoffPacket,
  reason: string,
  opts: { now?: string } = {}
): HandoffPacket {
  const terminal: HandoffFlightState[] = ['DONE', 'DROPPED'];
  if (terminal.includes(packet.state)) {
    throw new Error(`dropHandoff: packet already terminal (${packet.state})`);
  }
  const now = opts.now ?? new Date().toISOString();
  return stamp({ ...packet, drop_reason: reason }, 'DROPPED', packet.holder_id, now, reason);
}

export function isHandoffExpired(packet: HandoffPacket, opts: { now?: string } = {}): boolean {
  const now = opts.now ?? new Date().toISOString();
  return isExpiredAt(packet, now);
}

export function getReceipts(packet: HandoffPacket): HandoffReceipt[] {
  return packet.receipts;
}

export function summarizeHandoff(
  packet: HandoffPacket,
  opts: { now?: string } = {}
): HandoffSummary {
  const now = opts.now ?? new Date().toISOString();
  const lastReceipt = packet.receipts[packet.receipts.length - 1];
  return {
    packet_id: packet.packet_id,
    state: packet.state,
    priority: packet.priority,
    authority: packet.authority,
    issuer_id: packet.issuer_id,
    holder_id: packet.holder_id,
    target_id: packet.target_id,
    task: packet.mission.task,
    hop_count: packet.receipts.length - 1, // exclude creation receipt
    created_at: packet.created_at,
    last_receipt_at: lastReceipt?.stamped_at,
    deadline_at: packet.deadline_at,
    expired: isExpiredAt(packet, now),
    drop_reason: packet.drop_reason,
  };
}
