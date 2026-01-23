/**
 * Spiralverse Protocol SDK - TypeScript Implementation
 * 
 * Implements RWP v2.1 with Roundtable multi-signature governance,
 * Six Sacred Tongues domain separation, and 6D vector navigation.
 * 
 * @version 2.1.0
 * @author Issac Davis
 * @license MIT
 */

import crypto from 'crypto';

// ========== TYPES ==========

/** Six Sacred Tongues as protocol domains */
export enum SacredTongue {
  KO = 'KO', // Kor'aelin: Control & Intent
  AV = 'AV', // Avali: I/O & Messaging
  RU = 'RU', // Runethic: Policy & Constraints
  CA = 'CA', // Cassisivadan: Logic & Computation
  UM = 'UM', // Umbroth: Security & Secrets
  DR = 'DR', // Draumric: Types & Schema
}

/** Message envelope with hybrid spelltext + payload structure */
export interface SpiralverseEnvelope {
  spelltext: string;           // Human-readable metadata
  payload: string;             // Base64URL encoded action data
  signatures: SignatureSet;    // Multi-domain signatures
  ts: string;                  // ISO 8601 timestamp
  nonce: string;               // Replay protection
}

/** Signature set for Roundtable governance */
export interface SignatureSet {
  [key: string]: string;       // e.g., { "KO": "a7f2...", "RU": "d4e1..." }
}

/** Action payload (before Base64URL encoding) */
export interface ActionPayload {
  action: string;
  params: Record<string, any>;
  metadata?: Record<string, any>;
}

/** 6D Position vector */
export interface Position6D {
  axiom: number;   // X: forward/back
  flow: number;    // Y: lateral
  glyph: number;   // Z: altitude
  oracle: number;  // V: velocity (0-100)
  charm: number;   // H: harmony (-1 to +1)
  ledger: number;  // S: security level (0-255)
}

// ========== CORE SDK CLASS ==========

export class SpiralverseProtocol {
  private secrets: Map<SacredTongue, string> = new Map();
  
  constructor(secrets: Record<SacredTongue, string>) {
    Object.entries(secrets).forEach(([tongue, secret]) => {
      this.secrets.set(tongue as SacredTongue, secret);
    });
  }

  /**
   * Create signed envelope with specified tongues
   * @param origin Primary tongue initiating the action
   * @param requiredTongues Additional tongues for Roundtable governance
   * @param action Action payload
   */
  public createEnvelope(
    origin: SacredTongue,
    requiredTongues: SacredTongue[],
    action: ActionPayload
  ): SpiralverseEnvelope {
    const ts = new Date().toISOString();
    const nonce = crypto.randomBytes(16).toString('hex');
    const seq = Math.floor(Math.random() * 1000000);

    // Construct spelltext with semantic metadata
    const spelltext = `AXIOM<origin>${origin}</origin><seq>${seq}</seq><ts>${ts}</ts>`;

    // Encode payload
    const payload = Buffer.from(JSON.stringify(action)).toString('base64url');

    // Create canonical signing string
    const canonical = this.canonicalString(spelltext, payload, ts, nonce);

    // Generate signatures for origin + required tongues
    const tongues = [origin, ...requiredTongues.filter(t => t !== origin)];
    const signatures: SignatureSet = {};
    tongues.forEach(tongue => {
      const secret = this.secrets.get(tongue);
      if (!secret) throw new Error(`Missing secret for tongue: ${tongue}`);
      signatures[tongue] = this.sign(canonical, secret, tongue);
    });

    return { spelltext, payload, signatures, ts, nonce };
  }

  /**
   * Verify envelope signatures against required tongues
   * @param envelope Message to verify
   * @param requiredTongues Tongues that must have signed
   */
  public verifyEnvelope(
    envelope: SpiralverseEnvelope,
    requiredTongues: SacredTongue[]
  ): boolean {
    const canonical = this.canonicalString(
      envelope.spelltext,
      envelope.payload,
      envelope.ts,
      envelope.nonce
    );

    // Check all required tongues have valid signatures
    for (const tongue of requiredTongues) {
      const sig = envelope.signatures[tongue];
      if (!sig) {
        console.error(`Missing signature for required tongue: ${tongue}`);
        return false;
      }

      const secret = this.secrets.get(tongue);
      if (!secret) {
        console.error(`Missing secret for tongue: ${tongue}`);
        return false;
      }

      const expected = this.sign(canonical, secret, tongue);
      if (sig !== expected) {
        console.error(`Invalid signature for tongue: ${tongue}`);
        return false;
      }
    }

    // Check timestamp freshness (5 minute window)
    const age = Date.now() - new Date(envelope.ts).getTime();
    if (age > 5 * 60 * 1000) {
      console.error('Envelope expired');
      return false;
    }

    return true;
  }

  /**
   * Decode payload from envelope
   */
  public decodePayload(envelope: SpiralverseEnvelope): ActionPayload {
    const json = Buffer.from(envelope.payload, 'base64url').toString('utf-8');
    return JSON.parse(json);
  }

  // ========== INTERNAL HELPERS ==========

  private canonicalString(
    spelltext: string,
    payload: string,
    ts: string,
    nonce: string
  ): string {
    return `${spelltext}\n${payload}\n${ts}\n${nonce}`;
  }

  private sign(data: string, secret: string, tongue: SacredTongue): string {
    // Domain-separated HMAC
    const domain = `spiralverse:v2.1:${tongue}`;
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(domain);
    hmac.update(data);
    return hmac.digest('hex');
  }
}

// ========== GOVERNANCE POLICIES ==========

export enum SecurityTier {
  TIER1_LOW = 1,      // Single tongue (KO)
  TIER2_MEDIUM = 2,   // Dual tongues (KO + RU)
  TIER3_HIGH = 3,     // Triple tongues (KO + RU + UM)
  TIER4_CRITICAL = 4, // Quad+ tongues
}

/**
 * Get required tongues for a given security tier
 */
export function getRequiredTongues(tier: SecurityTier): SacredTongue[] {
  switch (tier) {
    case SecurityTier.TIER1_LOW:
      return [SacredTongue.KO];
    case SecurityTier.TIER2_MEDIUM:
      return [SacredTongue.KO, SacredTongue.RU];
    case SecurityTier.TIER3_HIGH:
      return [SacredTongue.KO, SacredTongue.RU, SacredTongue.UM];
    case SecurityTier.TIER4_CRITICAL:
      return [SacredTongue.KO, SacredTongue.RU, SacredTongue.UM, SacredTongue.DR];
    default:
      throw new Error(`Unknown tier: ${tier}`);
  }
}

/**
 * Classify action by security tier
 */
export function classifyAction(action: string): SecurityTier {
  const criticalActions = ['deploy', 'delete', 'rotate_key', 'grant_access'];
  const highActions = ['modify_state', 'execute_command', 'send_signal'];
  const mediumActions = ['query_state', 'log_event', 'update_metadata'];

  if (criticalActions.includes(action)) return SecurityTier.TIER4_CRITICAL;
  if (highActions.includes(action)) return SecurityTier.TIER3_HIGH;
  if (mediumActions.includes(action)) return SecurityTier.TIER2_MEDIUM;
  return SecurityTier.TIER1_LOW;
}

// ========== EXAMPLE USAGE ==========

/*
const sdk = new SpiralverseProtocol({
  [SacredTongue.KO]: 'secret_ko_key',
  [SacredTongue.RU]: 'secret_ru_key',
  [SacredTongue.UM]: 'secret_um_key',
  [SacredTongue.AV]: 'secret_av_key',
  [SacredTongue.CA]: 'secret_ca_key',
  [SacredTongue.DR]: 'secret_dr_key',
});

const action: ActionPayload = {
  action: 'move_arm',
  params: { x: 10, y: 20, z: 5 },
};

const tier = classifyAction(action.action);
const requiredTongues = getRequiredTongues(tier);

const envelope = sdk.createEnvelope(
  SacredTongue.KO,
  requiredTongues,
  action
);

const isValid = sdk.verifyEnvelope(envelope, requiredTongues);
console.log('Valid:', isValid);

if (isValid) {
  const decoded = sdk.decodePayload(envelope);
  console.log('Action:', decoded);
}
*/
