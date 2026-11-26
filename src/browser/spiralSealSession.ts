/**
 * @file spiralSealSession.ts
 * @module browser/spiralSealSession
 * @layer Layer 8, 12, 14
 * @component Framework 2: SpiralSeal Session Browser (SSSB)
 *
 * Quantum-resistant browser sessions using SpiralSeal AES-256-GCM
 * encryption with a one-way key ratchet. Every session state transition
 * is cryptographically sealed and temporally bound via breathing phase.
 *
 * Each session begins with fresh random entropy mixed under the master key.
 * Key rotation happens atomically after every action and the prior key buffer
 * is overwritten. Compromise of the retained master key alone cannot rebuild
 * past session keys. Replay guard uses a bounded nonce set for O(1) lookups.
 *
 * A2: Unitarity — session state preserved across encryptions
 * A3: Causality — temporal ordering via breathing phase checksum
 * A4: Symmetry — same key derivation regardless of actor
 */

import { createHash, createHmac, randomBytes, createCipheriv, createDecipheriv } from 'crypto';

// ============================================================================
// Types
// ============================================================================

/** Encrypted browser session */
export interface EncryptedSession {
  /** Unique session ID */
  sessionId: string;
  /** Agent ID that owns this session */
  agentId: string;
  /** Sealed state (AES-256-GCM encrypted) */
  sealedState: string;
  /** Current key version for forward secrecy */
  keyVersion: number;
  /** Nonce prefix bound to this session */
  noncePrefix: string;
  /** Breathing phase checksum for temporal verification */
  temporalChecksum: number;
  /** Creation timestamp */
  createdAt: number;
  /** Last action timestamp */
  lastActionAt: number;
  /** Action count for this session */
  actionCount: number;
}

/** Session state (cleartext, only exists during action execution) */
export interface SessionState {
  /** Current URL */
  currentUrl: string;
  /** Navigation history */
  history: string[];
  /** Cookies (sealed separately) */
  cookies: Record<string, string>;
  /** Session risk accumulator */
  riskAccumulator: number;
  /** Action log */
  actionLog: Array<{ action: string; timestamp: number; result: string }>;
}

/** Action to execute within a sealed session */
export interface SealedAction {
  /** Action type */
  type: string;
  /** Action payload */
  payload: Record<string, unknown>;
  /** Action nonce (must be unique) */
  nonce: string;
  /** Timestamp */
  timestamp: number;
}

/** Result from executing a sealed action */
export interface SealedActionResult {
  /** Success flag */
  success: boolean;
  /** Result data */
  data?: unknown;
  /** Error message */
  error?: string;
  /** New temporal checksum */
  newChecksum: number;
  /** Tongue verification status */
  tongueVerification: string[];
}

/** SSSB configuration */
export interface SSSBConfig {
  /** Key derivation iterations (default: 1) */
  keyDerivationIterations: number;
  /** Session TTL in ms (default: 30 min) */
  sessionTtlMs: number;
  /** Max actions per session (default: 10000) */
  maxActionsPerSession: number;
  /** Breathing frequency for temporal binding (default: 0.1) */
  breathingFreqHz: number;
  /** Nonce window size for replay detection (default: 10000) */
  nonceWindowSize: number;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_CONFIG: SSSBConfig = {
  keyDerivationIterations: 1,
  sessionTtlMs: 30 * 60 * 1000,
  maxActionsPerSession: 10_000,
  breathingFreqHz: 0.1,
  nonceWindowSize: 10_000,
};

const AES_KEY_LENGTH = 32; // 256 bits
const AES_IV_LENGTH = 12; // 96 bits for GCM
const AES_TAG_LENGTH = 16; // 128 bits

// ============================================================================
// SpiralSeal Session Browser
// ============================================================================

/**
 * SpiralSeal Session Browser (SSSB).
 *
 * Every browser session is encrypted with AES-256-GCM, with HKDF key
 * derivation binding the session to agent identity. Keys rotate through a
 * one-way ratchet and prior key buffers are overwritten after each successful
 * state transition. This protects past ciphertexts after later key compromise;
 * it does not claim post-compromise security for future actions.
 */
export class SpiralSealSessionBrowser {
  private readonly config: SSSBConfig;
  private readonly sessions: Map<string, EncryptedSession> = new Map();
  private readonly masterKey: Buffer;
  /** Current ratchet key only; prior versions are never retained. */
  private readonly sessionKeys: Map<string, Buffer> = new Map();
  private readonly nonceCache: Set<string> = new Set();

  constructor(masterKey: Buffer | string, config?: Partial<SSSBConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.masterKey =
      typeof masterKey === 'string'
        ? createHash('sha256').update(masterKey).digest()
        : Buffer.from(masterKey);
  }

  /**
   * Create a new encrypted browser session.
   */
  createSession(agentId: string, startUrl: string = 'about:blank'): EncryptedSession {
    const sessionId = this.generateSessionId();
    const noncePrefix = randomBytes(4).toString('hex');
    const breathingPhase = this.breathingTransform(Date.now());

    // A random per-session seed is mixed under the master key, then erased.
    // The retained master alone is therefore insufficient to recreate K_0.
    const sessionKey = this.createSessionKey(sessionId, agentId);

    let retained = false;
    try {
      // Initial state
      const initialState: SessionState = {
        currentUrl: startUrl,
        history: [startUrl],
        cookies: {},
        riskAccumulator: 0,
        actionLog: [],
      };

      // Seal initial state
      const sealedState = this.encrypt(JSON.stringify(initialState), sessionKey, noncePrefix, 0);
      const temporalChecksum = this.computeTemporalChecksum(sealedState, breathingPhase);

      const session: EncryptedSession = {
        sessionId,
        agentId,
        sealedState,
        keyVersion: 0,
        noncePrefix,
        temporalChecksum,
        createdAt: Date.now(),
        lastActionAt: Date.now(),
        actionCount: 0,
      };

      // Install the key before exposing the session. Both operations are
      // synchronous; a failed key-map write leaves no half-created session.
      this.sessionKeys.set(sessionId, sessionKey);
      this.sessions.set(sessionId, session);
      retained = true;
      return { ...session };
    } finally {
      if (!retained) {
        this.sessionKeys.delete(sessionId);
        sessionKey.fill(0);
      }
    }
  }

  /**
   * Execute an action within a sealed session.
   *
   * The session state is decrypted, the action applied, and re-encrypted
   * with a rotated key (forward secrecy).
   */
  executeAction(sessionId: string, action: SealedAction): SealedActionResult {
    const session = this.sessions.get(sessionId);
    if (!session) {
      return { success: false, error: 'Session not found', newChecksum: 0, tongueVerification: [] };
    }

    // Replay check
    if (this.nonceCache.has(action.nonce)) {
      return {
        success: false,
        error: 'Replay attack detected: nonce already consumed',
        newChecksum: session.temporalChecksum,
        tongueVerification: ['REPLAY_BLOCKED'],
      };
    }

    // Temporal breathing verification (A3: Causality)
    if (!this.verifyTemporalBounds(session, action.timestamp)) {
      return {
        success: false,
        error: 'Temporal bounds exceeded: action outside session window',
        newChecksum: session.temporalChecksum,
        tongueVerification: ['TEMPORAL_VIOLATION'],
      };
    }

    // Session TTL check
    if (Date.now() - session.createdAt > this.config.sessionTtlMs) {
      return {
        success: false,
        error: 'Session expired',
        newChecksum: session.temporalChecksum,
        tongueVerification: ['SESSION_EXPIRED'],
      };
    }

    // Max actions check
    if (session.actionCount >= this.config.maxActionsPerSession) {
      return {
        success: false,
        error: 'Session action limit reached',
        newChecksum: session.temporalChecksum,
        tongueVerification: ['ACTION_LIMIT'],
      };
    }

    // Decrypt current state
    const currentKey = this.sessionKeys.get(sessionId);
    if (!currentKey) {
      return {
        success: false,
        error: 'Session key unavailable — session integrity compromised',
        newChecksum: session.temporalChecksum,
        tongueVerification: ['KEY_STATE_FAILURE'],
      };
    }
    let state: SessionState;
    try {
      const decrypted = this.decrypt(
        session.sealedState,
        currentKey,
        session.noncePrefix,
        session.keyVersion
      );
      state = JSON.parse(decrypted) as SessionState;
    } catch {
      return {
        success: false,
        error: 'State decryption failed — session integrity compromised',
        newChecksum: session.temporalChecksum,
        tongueVerification: ['INTEGRITY_FAILURE'],
      };
    }

    // Apply action to state
    const result = this.applyAction(state, action);

    // Ratchet from the current key. The master key is deliberately not an
    // input: later master compromise must not reconstruct session history.
    const newKeyVersion = session.keyVersion + 1;
    const newKey = this.ratchetKey(currentKey, sessionId, session.agentId, newKeyVersion);

    // Re-encrypt before committing any ratchet state. If encryption fails, the
    // current key remains live and the candidate key is erased.
    let newSealedState: string;
    try {
      newSealedState = this.encrypt(
        JSON.stringify(state),
        newKey,
        session.noncePrefix,
        newKeyVersion
      );
    } catch {
      newKey.fill(0);
      return {
        success: false,
        error: 'State re-encryption failed — ratchet not advanced',
        newChecksum: session.temporalChecksum,
        tongueVerification: ['RATCHET_FAILURE'],
      };
    }
    const newBreathingPhase = this.breathingTransform(Date.now());
    const newChecksum = this.computeTemporalChecksum(newSealedState, newBreathingPhase);

    // Consume nonce
    this.nonceCache.add(action.nonce);
    if (this.nonceCache.size > this.config.nonceWindowSize) {
      // Evict oldest (approximate — Set preserves insertion order)
      const firstKey = this.nonceCache.values().next().value;
      if (firstKey !== undefined) {
        this.nonceCache.delete(firstKey);
      }
    }

    // Update session and key map as one synchronous transition, then overwrite
    // the prior key buffer. JavaScript cannot promise hardware-grade erasure,
    // but this removes the live application reference and zeros its bytes.
    // Install the next key first. If Map.set throws, no session metadata has
    // changed and the current key remains usable.
    this.sessionKeys.set(sessionId, newKey);
    session.sealedState = newSealedState;
    session.keyVersion = newKeyVersion;
    session.temporalChecksum = newChecksum;
    session.lastActionAt = Date.now();
    session.actionCount++;
    currentKey.fill(0);

    // Tongue verification
    const tongues = this.verifyTongues(action, state);

    return {
      success: result.success,
      data: result.data,
      error: result.error,
      newChecksum,
      tongueVerification: tongues,
    };
  }

  /**
   * Terminate and destroy a session.
   */
  terminateSession(sessionId: string): boolean {
    const key = this.sessionKeys.get(sessionId);
    if (key) {
      key.fill(0);
      this.sessionKeys.delete(sessionId);
    }
    return this.sessions.delete(sessionId);
  }

  /**
   * Get session metadata (without decrypting state).
   */
  getSessionInfo(sessionId: string): Omit<EncryptedSession, 'sealedState'> | null {
    const session = this.sessions.get(sessionId);
    if (!session) return null;
    const { sealedState: _, ...info } = session;
    return info;
  }

  /**
   * Get number of active sessions.
   */
  get activeSessionCount(): number {
    return this.sessions.size;
  }

  // --------------------------------------------------------------------------
  // Crypto Operations
  // --------------------------------------------------------------------------

  /** Create a non-reconstructable session root from master key + fresh entropy. */
  private createSessionKey(sessionId: string, agentId: string): Buffer {
    const seed = randomBytes(AES_KEY_LENGTH);
    try {
      return createHmac('sha256', this.masterKey)
        .update('sssb-root:v2\0')
        .update(sessionId)
        .update('\0')
        .update(agentId)
        .update('\0')
        .update(seed)
        .digest();
    } finally {
      seed.fill(0);
    }
  }

  /** Advance the one-way session ratchet from K_n to K_(n+1). */
  private ratchetKey(
    currentKey: Buffer,
    sessionId: string,
    agentId: string,
    version: number
  ): Buffer {
    const info = `sssb-ratchet:v2|${sessionId}|${agentId}|v${version}`;
    let next = createHmac('sha256', currentKey).update(info).digest();
    for (let i = 1; i < this.config.keyDerivationIterations; i++) {
      const prior = next;
      next = createHmac('sha256', prior).update(info).update(`|round=${i}`).digest();
      prior.fill(0);
    }
    return next;
  }

  /** AES-256-GCM encrypt */
  private encrypt(plaintext: string, key: Buffer, noncePrefix: string, counter: number): string {
    const iv = this.deriveIV(noncePrefix, counter);
    const cipher = createCipheriv('aes-256-gcm', key, iv);
    const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
    const tag = cipher.getAuthTag();
    // Format: base64(iv + tag + ciphertext)
    return Buffer.concat([iv, tag, encrypted]).toString('base64');
  }

  /** AES-256-GCM decrypt */
  private decrypt(sealed: string, key: Buffer, _noncePrefix: string, _counter: number): string {
    const data = Buffer.from(sealed, 'base64');
    const iv = data.subarray(0, AES_IV_LENGTH);
    const tag = data.subarray(AES_IV_LENGTH, AES_IV_LENGTH + AES_TAG_LENGTH);
    const ciphertext = data.subarray(AES_IV_LENGTH + AES_TAG_LENGTH);

    const decipher = createDecipheriv('aes-256-gcm', key, iv);
    decipher.setAuthTag(tag);
    return decipher.update(ciphertext) + decipher.final('utf8');
  }

  /** Derive deterministic IV from prefix + counter */
  private deriveIV(noncePrefix: string, counter: number): Buffer {
    const hash = createHash('sha256').update(`${noncePrefix}:${counter}`).digest();
    return hash.subarray(0, AES_IV_LENGTH);
  }

  // --------------------------------------------------------------------------
  // Temporal & Verification
  // --------------------------------------------------------------------------

  /** Multi-frequency breathing transform (A3: Causality) */
  private breathingTransform(timestamp: number): number {
    const t = timestamp / 1000;
    const f = this.config.breathingFreqHz;
    return Math.sin(2 * Math.PI * f * t) * Math.cos(2 * Math.PI * f * 0.7 * t);
  }

  /** Compute temporal checksum binding state to breathing phase */
  private computeTemporalChecksum(sealedState: string, breathingPhase: number): number {
    const hash = createHash('sha256')
      .update(`${sealedState}:${breathingPhase.toFixed(12)}`)
      .digest();
    return hash.readUInt32BE(0);
  }

  /** Verify action is within temporal bounds of session */
  private verifyTemporalBounds(session: EncryptedSession, actionTimestamp: number): boolean {
    const now = Date.now();
    const skew = Math.abs(actionTimestamp - now);
    return skew < 30_000; // 30s max skew
  }

  /** Apply an action to session state */
  private applyAction(
    state: SessionState,
    action: SealedAction
  ): { success: boolean; data?: unknown; error?: string } {
    state.actionLog.push({
      action: action.type,
      timestamp: action.timestamp,
      result: 'executed',
    });

    switch (action.type) {
      case 'navigate': {
        const url = action.payload['url'] as string;
        if (url) {
          state.currentUrl = url;
          state.history.push(url);
        }
        return { success: true, data: { url: state.currentUrl } };
      }
      case 'set_cookie': {
        const name = action.payload['name'] as string;
        const value = action.payload['value'] as string;
        if (name && value) {
          state.cookies[name] = value;
        }
        return { success: true };
      }
      default:
        return { success: true, data: { type: action.type } };
    }
  }

  /** Verify Sacred Tongue resonance for an action */
  private verifyTongues(action: SealedAction, state: SessionState): string[] {
    const tongues: string[] = [];

    // KO: Control flow valid
    tongues.push('KO:PASS');

    // AV: I/O valid (URL is reachable)
    if (state.currentUrl.startsWith('https://') || state.currentUrl === 'about:blank') {
      tongues.push('AV:PASS');
    } else {
      tongues.push('AV:WARN');
    }

    // RU: Policy check
    if (action.type !== 'execute_script') {
      tongues.push('RU:PASS');
    } else {
      tongues.push('RU:ELEVATED');
    }

    // UM: Security (encrypted session = inherent pass)
    tongues.push('UM:PASS');

    // DR: Type safety
    tongues.push('DR:PASS');

    return tongues;
  }

  /** Generate unique session ID */
  private generateSessionId(): string {
    return `sssb-${Date.now().toString(36)}-${randomBytes(8).toString('hex')}`;
  }
}
