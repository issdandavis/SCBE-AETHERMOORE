/**
 * Sacred Tongue Tokenizer - SS1 Spell-Text Encoding
 * ==================================================
 * Deterministic byte-to-token encoder/decoder for the Six Sacred Tongues.
 * Each byte (0-255) maps to exactly one unique token per tongue.
 *
 * Token format: prefix'suffix (apostrophe as morpheme seam)
 * Example: 0x2A → vel'an (in Kor'aelin)
 *
 * Section-to-tongue mapping (SS1 canonical):
 * - aad/header → Avali (AV) - diplomacy/context
 * - salt → Runethic (RU) - binding
 * - nonce → Kor'aelin (KO) - flow/intent
 * - ciphertext → Cassisivadan (CA) - bitcraft/maths
 * - auth tag → Draumric (DR) - structure stands
 * - redaction → Umbroth (UM) - veil
 *
 * @version 2.0.0 (Visual System Edition)
 */

// ============================================================
// TONGUE SPECIFICATIONS
// ============================================================

export interface TongueSpec {
  code: TongueCode;
  name: string;
  prefixes: readonly string[];
  suffixes: readonly string[];
  domain: string;
  harmonicFrequency: number;
  weight: number; // Governance weight for cross-tokenization
  phase: number;  // Phase angle in degrees
}

export type TongueCode = 'ko' | 'av' | 'ru' | 'ca' | 'um' | 'dr';
export type SS1Section = 'aad' | 'salt' | 'nonce' | 'ct' | 'tag' | 'redact';

// ============================================================
// THE SIX SACRED TONGUES
// ============================================================

export const KOR_AELIN: TongueSpec = {
  code: 'ko',
  name: "Kor'aelin",
  prefixes: [
    'sil', 'kor', 'vel', 'zar', 'keth', 'thul', 'nav', 'ael',
    'ra', 'med', 'gal', 'lan', 'joy', 'good', 'nex', 'vara'
  ],
  suffixes: [
    'a', 'ae', 'ei', 'ia', 'oa', 'uu', 'eth', 'ar',
    'or', 'il', 'an', 'en', 'un', 'ir', 'oth', 'esh'
  ],
  domain: 'nonce/flow/intent',
  harmonicFrequency: 440.0,
  weight: 1.0,
  phase: 0
};

export const AVALI: TongueSpec = {
  code: 'av',
  name: 'Avali',
  prefixes: [
    'saina', 'talan', 'vessa', 'maren', 'oriel', 'serin', 'nurel', 'lirea',
    'kiva', 'lumen', 'calma', 'ponte', 'verin', 'nava', 'sela', 'tide'
  ],
  suffixes: [
    'a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
    'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'
  ],
  domain: 'aad/header/metadata',
  harmonicFrequency: 523.25,
  weight: 1.62,
  phase: 60
};

export const RUNETHIC: TongueSpec = {
  code: 'ru',
  name: 'Runethic',
  prefixes: [
    'khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak', 'tharn',
    'groth', 'basalt', 'rune', 'sear', 'oath', 'gnarl', 'rift', 'iron'
  ],
  suffixes: [
    'ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
    'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'
  ],
  domain: 'salt/binding',
  harmonicFrequency: 329.63,
  weight: 2.62,
  phase: 120
};

export const CASSISIVADAN: TongueSpec = {
  code: 'ca',
  name: 'Cassisivadan',
  prefixes: [
    'bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa', 'spira',
    'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip', 'mix', 'chass'
  ],
  suffixes: [
    'a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
    'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'
  ],
  domain: 'ciphertext/bitcraft',
  harmonicFrequency: 659.25,
  weight: 4.24,
  phase: 180
};

export const UMBROTH: TongueSpec = {
  code: 'um',
  name: 'Umbroth',
  prefixes: [
    'veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush', 'thorn',
    'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache', 'null', 'shade'
  ],
  suffixes: [
    'a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
    'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'
  ],
  domain: 'redaction/veil',
  harmonicFrequency: 293.66,
  weight: 6.87,
  phase: 240
};

export const DRAUMRIC: TongueSpec = {
  code: 'dr',
  name: 'Draumric',
  prefixes: [
    'anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal', 'temper', 'forge',
    'stone', 'steam', 'oath', 'seal', 'frame', 'pillar', 'rivet', 'ember'
  ],
  suffixes: [
    'a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
    'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'
  ],
  domain: 'tag/structure',
  harmonicFrequency: 392.0,
  weight: 11.09,
  phase: 300
};

export const TONGUES: Record<TongueCode, TongueSpec> = {
  ko: KOR_AELIN,
  av: AVALI,
  ru: RUNETHIC,
  ca: CASSISIVADAN,
  um: UMBROTH,
  dr: DRAUMRIC
};

export const SECTION_TONGUES: Record<SS1Section, TongueCode> = {
  aad: 'av',
  salt: 'ru',
  nonce: 'ko',
  ct: 'ca',
  tag: 'dr',
  redact: 'um'
};

// ============================================================
// TOKENIZER CLASS
// ============================================================

export interface CrossTokenResult {
  tokens: string[];
  attestation: {
    fromTongue: TongueCode;
    toTongue: TongueCode;
    phaseDelta: number;
    weightRatio: number;
    timestamp: number;
  };
}

export interface SS1Blob {
  version: 'SS1';
  kid?: string;
  aad?: string;
  salt?: string;
  nonce?: string;
  ct?: string;
  tag?: string;
}

export class SacredTongueTokenizer {
  private byteToToken: Map<TongueCode, string[]> = new Map();
  private tokenToByte: Map<TongueCode, Map<string, number>> = new Map();

  constructor() {
    this.buildTables();
    this.validateSecurity();
  }

  private buildTables(): void {
    for (const [code, spec] of Object.entries(TONGUES)) {
      const tongueCode = code as TongueCode;
      const b2t: string[] = new Array(256);
      const t2b = new Map<string, number>();

      for (let b = 0; b < 256; b++) {
        const hi = (b >> 4) & 0x0f; // High nibble → prefix index
        const lo = b & 0x0f;        // Low nibble → suffix index
        const token = `${spec.prefixes[hi]}'${spec.suffixes[lo]}`;
        b2t[b] = token;
        t2b.set(token, b);
      }

      this.byteToToken.set(tongueCode, b2t);
      this.tokenToByte.set(tongueCode, t2b);
    }
  }

  private validateSecurity(): void {
    for (const [code, tokens] of this.byteToToken.entries()) {
      const uniqueTokens = new Set(tokens);
      if (uniqueTokens.size !== 256) {
        throw new Error(`Tongue ${code} has ${uniqueTokens.size} unique tokens (expected 256)`);
      }
    }
  }

  // ==================== Core API ====================

  /**
   * Encode bytes to Sacred Tongue tokens
   */
  encodeBytes(tongueCode: TongueCode, data: Uint8Array | number[]): string[] {
    const table = this.byteToToken.get(tongueCode);
    if (!table) throw new Error(`Unknown tongue: ${tongueCode}`);
    return Array.from(data).map(b => table[b]);
  }

  /**
   * Decode Sacred Tongue tokens to bytes
   */
  decodeTokens(tongueCode: TongueCode, tokens: string[]): Uint8Array {
    const table = this.tokenToByte.get(tongueCode);
    if (!table) throw new Error(`Unknown tongue: ${tongueCode}`);

    const bytes = new Uint8Array(tokens.length);
    for (let i = 0; i < tokens.length; i++) {
      const b = table.get(tokens[i]);
      if (b === undefined) {
        throw new Error(`Invalid token for ${tongueCode}: ${tokens[i]}`);
      }
      bytes[i] = b;
    }
    return bytes;
  }

  /**
   * Encode string to Sacred Tongue tokens
   */
  encodeString(tongueCode: TongueCode, str: string): string[] {
    const encoder = new TextEncoder();
    return this.encodeBytes(tongueCode, encoder.encode(str));
  }

  /**
   * Decode Sacred Tongue tokens to string
   */
  decodeString(tongueCode: TongueCode, tokens: string[]): string {
    const bytes = this.decodeTokens(tongueCode, tokens);
    const decoder = new TextDecoder();
    return decoder.decode(bytes);
  }

  // ==================== Section API ====================

  /**
   * Encode RWP section using canonical tongue
   */
  encodeSection(section: SS1Section, data: Uint8Array | number[]): string[] {
    const tongueCode = SECTION_TONGUES[section];
    return this.encodeBytes(tongueCode, data);
  }

  /**
   * Decode RWP section from tokens
   */
  decodeSection(section: SS1Section, tokens: string[]): Uint8Array {
    const tongueCode = SECTION_TONGUES[section];
    return this.decodeTokens(tongueCode, tokens);
  }

  // ==================== Cross-Tokenization ====================

  /**
   * Translate data from one tongue to another (lossless)
   */
  crossTokenize(fromTongue: TongueCode, toTongue: TongueCode, tokens: string[]): CrossTokenResult {
    // Decode from source tongue
    const bytes = this.decodeTokens(fromTongue, tokens);

    // Encode to target tongue
    const newTokens = this.encodeBytes(toTongue, bytes);

    // Generate attestation
    const fromSpec = TONGUES[fromTongue];
    const toSpec = TONGUES[toTongue];

    return {
      tokens: newTokens,
      attestation: {
        fromTongue,
        toTongue,
        phaseDelta: toSpec.phase - fromSpec.phase,
        weightRatio: toSpec.weight / fromSpec.weight,
        timestamp: Date.now()
      }
    };
  }

  // ==================== SS1 Blob Format ====================

  /**
   * Parse SS1 blob string into components
   * Format: SS1|kid=xxx|salt=ru:token token|ct=ca:token token|tag=dr:token token
   */
  parseBlob(blob: string): SS1Blob {
    const result: SS1Blob = { version: 'SS1' };

    if (!blob.startsWith('SS1|')) {
      throw new Error('Invalid SS1 blob: missing SS1| prefix');
    }

    const parts = blob.slice(4).split('|');
    for (const part of parts) {
      const [key, value] = part.split('=', 2);
      if (!key || !value) continue;

      switch (key) {
        case 'kid':
          result.kid = value;
          break;
        case 'aad':
        case 'salt':
        case 'nonce':
        case 'ct':
        case 'tag':
          result[key] = value;
          break;
      }
    }

    return result;
  }

  /**
   * Build SS1 blob string from components
   */
  buildBlob(components: Omit<SS1Blob, 'version'>): string {
    const parts = ['SS1'];

    if (components.kid) parts.push(`kid=${components.kid}`);
    if (components.aad) parts.push(`aad=${components.aad}`);
    if (components.salt) parts.push(`salt=${components.salt}`);
    if (components.nonce) parts.push(`nonce=${components.nonce}`);
    if (components.ct) parts.push(`ct=${components.ct}`);
    if (components.tag) parts.push(`tag=${components.tag}`);

    return parts.join('|');
  }

  // ==================== Display Helpers ====================

  /**
   * Format tokens for display (space-separated with tongue prefix)
   */
  formatTokens(tongueCode: TongueCode, tokens: string[]): string {
    return `${tongueCode}:${tokens.join(' ')}`;
  }

  /**
   * Parse formatted token string
   */
  parseFormattedTokens(formatted: string): { tongueCode: TongueCode; tokens: string[] } {
    const colonIndex = formatted.indexOf(':');
    if (colonIndex === -1) {
      throw new Error('Invalid format: expected tongue:tokens');
    }

    const tongueCode = formatted.slice(0, colonIndex) as TongueCode;
    const tokens = formatted.slice(colonIndex + 1).split(' ').filter(t => t.length > 0);

    return { tongueCode, tokens };
  }

  /**
   * Get tongue spec by code
   */
  getTongue(code: TongueCode): TongueSpec {
    return TONGUES[code];
  }

  /**
   * Get all tongue codes
   */
  getTongueCodes(): TongueCode[] {
    return Object.keys(TONGUES) as TongueCode[];
  }

  /**
   * Validate if tokens belong to a specific tongue
   */
  validateTokens(tongueCode: TongueCode, tokens: string[]): boolean {
    const table = this.tokenToByte.get(tongueCode);
    if (!table) return false;
    return tokens.every(t => table.has(t));
  }

  /**
   * Get harmonic fingerprint for spectral validation (Layer 9)
   */
  computeHarmonicFingerprint(tongueCode: TongueCode, tokens: string[]): number {
    const spec = TONGUES[tongueCode];
    // Simple hash-based weight
    let hash = 0;
    for (const token of tokens) {
      for (let i = 0; i < token.length; i++) {
        hash = ((hash << 5) - hash) + token.charCodeAt(i);
        hash = hash & hash; // Convert to 32-bit int
      }
    }
    const weight = Math.abs(hash) / 0x7fffffff;
    return spec.harmonicFrequency * weight;
  }
}

// ============================================================
// SINGLETON & HELPERS
// ============================================================

let tokenizerInstance: SacredTongueTokenizer | null = null;

export function getTokenizer(): SacredTongueTokenizer {
  if (!tokenizerInstance) {
    tokenizerInstance = new SacredTongueTokenizer();
  }
  return tokenizerInstance;
}

/**
 * Quick encode helper
 */
export function encodeToSpellText(tongueCode: TongueCode, text: string): string {
  const tokenizer = getTokenizer();
  const tokens = tokenizer.encodeString(tongueCode, text);
  return tokenizer.formatTokens(tongueCode, tokens);
}

/**
 * Quick decode helper
 */
export function decodeFromSpellText(formatted: string): string {
  const tokenizer = getTokenizer();
  const { tongueCode, tokens } = tokenizer.parseFormattedTokens(formatted);
  return tokenizer.decodeString(tongueCode, tokens);
}

/**
 * Encode data for a specific RWP section
 */
export function encodeRWPSection(section: SS1Section, data: string): string {
  const tokenizer = getTokenizer();
  const encoder = new TextEncoder();
  const tokens = tokenizer.encodeSection(section, encoder.encode(data));
  const tongueCode = SECTION_TONGUES[section];
  return tokenizer.formatTokens(tongueCode, tokens);
}
