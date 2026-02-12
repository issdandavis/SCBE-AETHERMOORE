/**
 * SCBE SpiralSeal SS1 - Sacred Tongue Definitions
 *
 * The Six Sacred Tongues for cryptographic spell-text encoding.
 * Each tongue has 16 prefixes × 16 suffixes = 256 unique tokens.
 *
 * Token format: prefix'suffix (apostrophe as morpheme seam)
 *
 * Section-to-tongue mapping (SS1 canonical):
 * - aad/header → Avali (AV) - diplomacy/context
 * - salt → Runethic (RU) - binding
 * - nonce → Kor'aelin (KO) - flow/intent
 * - ciphertext → Cassisivadan (CA) - bitcraft/maths
 * - auth tag → Draumric (DR) - structure stands
 * - redaction → Umbroth (UM) - veil
 */
/**
 * Tongue specification interface
 */
export interface TongueSpec {
    /** 2-letter code (ko, av, ru, ca, um, dr) */
    code: string;
    /** Full name */
    name: string;
    /** 16 prefixes */
    prefixes: readonly string[];
    /** 16 suffixes */
    suffixes: readonly string[];
    /** Domain/purpose */
    domain: string;
}
/**
 * Kor'aelin - Command authority, flow, intent
 * Used for: Nonce encoding
 */
export declare const KOR_AELIN: TongueSpec;
/**
 * Avali - Emotional resonance, diplomacy
 * Used for: AAD/header/metadata
 */
export declare const AVALI: TongueSpec;
/**
 * Runethic - Historical binding, permanence
 * Used for: Salt encoding
 */
export declare const RUNETHIC: TongueSpec;
/**
 * Cassisivadan - Divine invocation, mathematics, bitcraft
 * Used for: Ciphertext encoding
 */
export declare const CASSISIVADAN: TongueSpec;
/**
 * Umbroth - Shadow protocols, veiling
 * Used for: Redaction encoding
 */
export declare const UMBROTH: TongueSpec;
/**
 * Draumric - Power amplification, structure
 * Used for: Auth tag encoding
 */
export declare const DRAUMRIC: TongueSpec;
/**
 * All tongues indexed by code
 */
export declare const TONGUES: Record<string, TongueSpec>;
/**
 * Tongue codes as a type
 */
export type TongueCode = 'ko' | 'av' | 'ru' | 'ca' | 'um' | 'dr';
/**
 * Section-to-tongue mapping (SS1 canonical)
 */
export declare const SECTION_TONGUES: Record<string, TongueCode>;
/**
 * SS1 section types
 */
export type SS1Section = 'aad' | 'salt' | 'nonce' | 'ct' | 'tag' | 'redact';
/**
 * Get tongue for a section
 */
export declare function getTongueForSection(section: SS1Section): TongueSpec;
/**
 * Custom lexicon definition for loading from JSON
 */
export interface LexiconDefinition {
    code: string;
    name: string;
    prefixes: string[];
    suffixes: string[];
    domain: string;
    /** Optional harmonic frequency for spectral validation */
    harmonicFrequency?: number;
    /** Optional description/lore */
    description?: string;
}
/**
 * Lexicon file format
 */
export interface LexiconFile {
    version: string;
    tongues: LexiconDefinition[];
}
/**
 * Validate a lexicon definition
 * @throws Error if invalid
 */
export declare function validateLexicon(lexicon: LexiconDefinition): void;
/**
 * Register a custom tongue lexicon.
 * Overwrites existing tongue if code matches.
 *
 * @example
 * registerTongue({
 *   code: 'ko',
 *   name: "Kor'aelin",
 *   prefixes: ['vel', 'ashi', 'thar', ...], // 16 total
 *   suffixes: ['oni', 'eth', 'ara', ...],   // 16 total
 *   domain: 'nonce/flow/intent'
 * });
 */
export declare function registerTongue(lexicon: LexiconDefinition): void;
/**
 * Load multiple tongues from a lexicon file object.
 *
 * @example
 * const lexiconData = JSON.parse(fs.readFileSync('custom-lexicons.json', 'utf-8'));
 * loadLexicons(lexiconData);
 */
export declare function loadLexicons(file: LexiconFile): {
    loaded: string[];
    errors: string[];
};
/**
 * Reset tongues to built-in defaults.
 * Useful for testing or resetting after loading custom lexicons.
 */
export declare function resetToDefaultTongues(): void;
/**
 * Get all registered tongue codes
 */
export declare function getRegisteredTongues(): string[];
/**
 * Check if a tongue code is registered
 */
export declare function hasTongue(code: string): boolean;
//# sourceMappingURL=sacredTongues.d.ts.map