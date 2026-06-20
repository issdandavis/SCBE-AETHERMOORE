/**
 * @file sacredTonguesFlight.ts
 * @module fleet/drone-fleet/sacredTonguesFlight
 * @layer Layer 3, Layer 4, Layer 9
 * @component Sacred Tongues Flight Dynamics Mapping
 *
 * Maps specific flight behaviors to the Six Sacred Tongues, turning
 * command syntax into movement physics. Single-byte commands encode
 * complex multi-dimensional maneuvers.
 *
 * | Tongue | Phase  | Behavior         | Weight |
 * |--------|--------|------------------|--------|
 * | KO     | 0°     | Flow/Travel      | 1.00   |
 * | AV     | 60°    | Swarm Sync       | 1.38   |
 * | RU     | 120°   | Hold Position    | 2.62   |
 * | CA     | 180°   | Execute/Engage   | 6.18   |
 * | UM     | 240°   | Stealth Mode     | 4.24   |
 * | DR     | 300°   | Formation Lock   | 11.09  |
 *
 * Bandwidth: 1024 → 16 bytes (64x reduction)
 *
 * A5: Composition — pipeline integrity maintained through tongue encoding
 */

/** Sacred Tongue code */
export type TongueCode = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Flight behavior mapped to each tongue */
export type FlightBehavior =
  | 'FLOW_TRAVEL'
  | 'SWARM_SYNC'
  | 'HOLD_POSITION'
  | 'EXECUTE_ENGAGE'
  | 'STEALTH_MODE'
  | 'FORMATION_LOCK';

/** Tongue-to-flight mapping definition */
export interface TongueFlightMapping {
  /** Tongue code */
  tongue: TongueCode;
  /** Phase angle in degrees */
  phaseDeg: number;
  /** Phase angle in radians */
  phaseRad: number;
  /** Mapped flight behavior */
  behavior: FlightBehavior;
  /** Priority/energy weight (golden ratio scaling) */
  weight: number;
  /** Human-readable tongue name */
  name: string;
}

/** Encoded flight command (compact wire format) */
export interface FlightCommand {
  /** Tongue code (3 bits) */
  tongue: TongueCode;
  /** Sub-command within the tongue's behavior space (5 bits) */
  subCommand: number;
  /** Intensity/magnitude [0, 1] (8 bits quantized) */
  intensity: number;
  /** Target drone index (optional, broadcast if omitted) */
  targetDrone?: number;
}

/** Decoded flight instruction */
export interface FlightInstruction {
  /** The flight behavior to execute */
  behavior: FlightBehavior;
  /** Priority weight */
  weight: number;
  /** Phase angle for coordination (radians) */
  phase: number;
  /** Intensity/magnitude */
  intensity: number;
  /** Whether this is a broadcast command */
  isBroadcast: boolean;
  /** Raw tongue code for logging */
  tongue: TongueCode;
}

/** Flight dynamics state resulting from instruction */
export interface FlightDynamicsState {
  /** Current behavior mode */
  mode: FlightBehavior;
  /** Velocity multiplier based on tongue weight */
  velocityMultiplier: number;
  /** Heading adjustment (radians) */
  headingDelta: number;
  /** Energy allocation fraction */
  energyAllocation: number;
  /** Whether drone is in stealth */
  isStealth: boolean;
  /** Whether position is locked */
  isPositionLocked: boolean;
}

// ── Tongue-Flight Mapping Table ──────────────────────────────────

export const TONGUE_FLIGHT_MAP: Record<TongueCode, TongueFlightMapping> = {
  KO: {
    tongue: 'KO',
    phaseDeg: 0,
    phaseRad: 0,
    behavior: 'FLOW_TRAVEL',
    weight: 1.0,
    name: "Kor'aelin",
  },
  AV: {
    tongue: 'AV',
    phaseDeg: 60,
    phaseRad: Math.PI / 3,
    behavior: 'SWARM_SYNC',
    weight: 1.38,
    name: 'Avali',
  },
  RU: {
    tongue: 'RU',
    phaseDeg: 120,
    phaseRad: (2 * Math.PI) / 3,
    behavior: 'HOLD_POSITION',
    weight: 2.62,
    name: 'Runethic',
  },
  CA: {
    tongue: 'CA',
    phaseDeg: 180,
    phaseRad: Math.PI,
    behavior: 'EXECUTE_ENGAGE',
    weight: 6.18,
    name: 'Cassisivadan',
  },
  UM: {
    tongue: 'UM',
    phaseDeg: 240,
    phaseRad: (4 * Math.PI) / 3,
    behavior: 'STEALTH_MODE',
    weight: 4.24,
    name: 'Umbroth',
  },
  DR: {
    tongue: 'DR',
    phaseDeg: 300,
    phaseRad: (5 * Math.PI) / 3,
    behavior: 'FORMATION_LOCK',
    weight: 11.09,
    name: 'Draumric',
  },
};

const TONGUE_CODES: TongueCode[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

/**
 * Encode a flight command into a compact 2-byte representation.
 *
 * Byte 0: [tongue_index:3][sub_command:5]
 * Byte 1: [intensity_quantized:8]
 *
 * @param command - Flight command to encode
 * @returns 2-byte array
 */
export function encodeCommand(command: FlightCommand): [number, number] {
  const tongueIndex = TONGUE_CODES.indexOf(command.tongue);
  const byte0 = ((tongueIndex & 0x07) << 5) | (command.subCommand & 0x1f);
  const byte1 = Math.round(command.intensity * 255) & 0xff;
  return [byte0, byte1];
}

/**
 * Decode a 2-byte compact command back to a FlightCommand.
 *
 * @param bytes - 2-byte encoded command
 * @returns Decoded FlightCommand
 */
export function decodeCommand(bytes: [number, number]): FlightCommand {
  const tongueIndex = (bytes[0] >> 5) & 0x07;
  const subCommand = bytes[0] & 0x1f;
  const intensity = bytes[1] / 255;
  const tongue = TONGUE_CODES[tongueIndex] ?? 'KO';

  return { tongue, subCommand, intensity };
}

/**
 * Convert a flight command to a full flight instruction with
 * all dynamics parameters resolved.
 *
 * @param command - Encoded flight command
 * @returns Full flight instruction
 */
export function resolveInstruction(command: FlightCommand): FlightInstruction {
  const mapping = TONGUE_FLIGHT_MAP[command.tongue];
  return {
    behavior: mapping.behavior,
    weight: mapping.weight,
    phase: mapping.phaseRad,
    intensity: command.intensity,
    isBroadcast: command.targetDrone === undefined,
    tongue: command.tongue,
  };
}

/**
 * Compute flight dynamics state from an instruction.
 *
 * @param instruction - Resolved flight instruction
 * @returns Flight dynamics state
 */
export function computeDynamics(instruction: FlightInstruction): FlightDynamicsState {
  const totalWeight = Object.values(TONGUE_FLIGHT_MAP).reduce((s, m) => s + m.weight, 0);
  const energyAllocation = instruction.weight / totalWeight;

  return {
    mode: instruction.behavior,
    velocityMultiplier: instruction.behavior === 'HOLD_POSITION' ? 0 : instruction.intensity,
    headingDelta: instruction.phase * instruction.intensity,
    energyAllocation,
    isStealth: instruction.behavior === 'STEALTH_MODE',
    isPositionLocked:
      instruction.behavior === 'HOLD_POSITION' || instruction.behavior === 'FORMATION_LOCK',
  };
}

/**
 * Parse a tongue command string like "ru:khar'ak" into a FlightCommand.
 *
 * Format: tongue_code:sub_command_name
 *
 * @param commandStr - Command string
 * @param intensity - Intensity [0, 1] (default 1.0)
 * @returns FlightCommand or null if invalid
 */
export function parseCommandString(
  commandStr: string,
  intensity: number = 1.0
): FlightCommand | null {
  const parts = commandStr.toLowerCase().split(':');
  if (parts.length < 1) return null;

  const tongueStr = parts[0].toUpperCase();
  if (!TONGUE_CODES.includes(tongueStr as TongueCode)) return null;

  return {
    tongue: tongueStr as TongueCode,
    subCommand: 0,
    intensity: Math.max(0, Math.min(1, intensity)),
  };
}

/**
 * Compute bandwidth savings for tongue-encoded commands vs raw.
 *
 * @param rawCommandBytes - Size of raw command in bytes
 * @returns Compression ratio and savings
 */
export function bandwidthSavings(rawCommandBytes: number): {
  encodedBytes: number;
  ratio: number;
  savingsPercent: number;
} {
  const encodedBytes = 2; // Tongue commands are always 2 bytes
  const ratio = rawCommandBytes / encodedBytes;
  const savingsPercent = ((rawCommandBytes - encodedBytes) / rawCommandBytes) * 100;
  return { encodedBytes, ratio, savingsPercent };
}
