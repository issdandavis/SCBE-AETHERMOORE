"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.getTongueForSection = exports.SECTION_TONGUES = exports.TONGUES = exports.DRAUMRIC = exports.UMBROTH = exports.CASSISIVADAN = exports.RUNETHIC = exports.AVALI = exports.KOR_AELIN = void 0;
// ═══════════════════════════════════════════════════════════════
// THE SIX SACRED TONGUES - v1 Wordlists
// ═══════════════════════════════════════════════════════════════
/**
 * Kor'aelin - Command authority, flow, intent
 * Used for: Nonce encoding
 */
exports.KOR_AELIN = {
    code: 'ko',
    name: "Kor'aelin",
    prefixes: ['sil', 'kor', 'vel', 'zar', 'keth', 'thul', 'nav', 'ael',
        'ra', 'med', 'gal', 'lan', 'joy', 'good', 'nex', 'vara'],
    suffixes: ['a', 'ae', 'ei', 'ia', 'oa', 'uu', 'eth', 'ar',
        'or', 'il', 'an', 'en', 'un', 'ir', 'oth', 'esh'],
    domain: 'nonce/flow/intent',
};
/**
 * Avali - Emotional resonance, diplomacy
 * Used for: AAD/header/metadata
 */
exports.AVALI = {
    code: 'av',
    name: 'Avali',
    prefixes: ['saina', 'talan', 'vessa', 'maren', 'oriel', 'serin', 'nurel', 'lirea',
        'kiva', 'lumen', 'calma', 'ponte', 'verin', 'nava', 'sela', 'tide'],
    suffixes: ['a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
        'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'],
    domain: 'aad/header/metadata',
};
/**
 * Runethic - Historical binding, permanence
 * Used for: Salt encoding
 */
exports.RUNETHIC = {
    code: 'ru',
    name: 'Runethic',
    prefixes: ['khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak', 'tharn',
        'groth', 'basalt', 'rune', 'sear', 'oath', 'gnarl', 'rift', 'iron'],
    suffixes: ['ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
        'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'],
    domain: 'salt/binding',
};
/**
 * Cassisivadan - Divine invocation, mathematics, bitcraft
 * Used for: Ciphertext encoding
 */
exports.CASSISIVADAN = {
    code: 'ca',
    name: 'Cassisivadan',
    prefixes: ['bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa', 'spira',
        'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip', 'mix', 'chass'],
    suffixes: ['a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
        'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'],
    domain: 'ciphertext/bitcraft',
};
/**
 * Umbroth - Shadow protocols, veiling
 * Used for: Redaction encoding
 */
exports.UMBROTH = {
    code: 'um',
    name: 'Umbroth',
    prefixes: ['veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush', 'thorn',
        'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache', 'null', 'shade'],
    suffixes: ['a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
        'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'],
    domain: 'redaction/veil',
};
/**
 * Draumric - Power amplification, structure
 * Used for: Auth tag encoding
 */
exports.DRAUMRIC = {
    code: 'dr',
    name: 'Draumric',
    prefixes: ['anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal', 'temper', 'forge',
        'stone', 'steam', 'oath', 'seal', 'frame', 'pillar', 'rivet', 'ember'],
    suffixes: ['a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
        'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'],
    domain: 'tag/structure',
};
/**
 * All tongues indexed by code
 */
exports.TONGUES = {
    ko: exports.KOR_AELIN,
    av: exports.AVALI,
    ru: exports.RUNETHIC,
    ca: exports.CASSISIVADAN,
    um: exports.UMBROTH,
    dr: exports.DRAUMRIC,
};
/**
 * Section-to-tongue mapping (SS1 canonical)
 */
exports.SECTION_TONGUES = {
    aad: 'av', // Avali for metadata/context
    salt: 'ru', // Runethic for binding
    nonce: 'ko', // Kor'aelin for flow/intent
    ct: 'ca', // Cassisivadan for ciphertext
    tag: 'dr', // Draumric for auth tag
    redact: 'um', // Umbroth for redaction wrapper
};
/**
 * Get tongue for a section
 */
function getTongueForSection(section) {
    const code = exports.SECTION_TONGUES[section];
    return exports.TONGUES[code];
}
exports.getTongueForSection = getTongueForSection;
//# sourceMappingURL=sacredTongues.js.map