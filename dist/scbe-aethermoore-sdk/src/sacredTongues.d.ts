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
//# sourceMappingURL=sacredTongues.d.ts.map