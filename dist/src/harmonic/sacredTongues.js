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
exports.SECTION_TONGUES = exports.TONGUES = exports.DRAUMRIC = exports.UMBROTH = exports.CASSISIVADAN = exports.RUNETHIC = exports.AVALI = exports.KOR_AELIN = void 0;
exports.getTongueForSection = getTongueForSection;
exports.validateLexicon = validateLexicon;
exports.registerTongue = registerTongue;
exports.loadLexicons = loadLexicons;
exports.resetToDefaultTongues = resetToDefaultTongues;
exports.getRegisteredTongues = getRegisteredTongues;
exports.hasTongue = hasTongue;
// ═══════════════════════════════════════════════════════════════
// THE SIX SACRED TONGUES - v1.1 Wordlists (bijective, consistent)
// ═══════════════════════════════════════════════════════════════
/**
 * Kor'aelin - Command authority, flow, intent
 * Used for: Nonce encoding
 */
exports.KOR_AELIN = {
    code: 'ko',
    name: "Kor'aelin",
    prefixes: [
        'kor',
        'ael',
        'lin',
        'dah',
        'ru',
        'mel',
        'ik',
        'sor',
        'in',
        'tiv',
        'ar',
        'ul',
        'mar',
        'vex',
        'yn',
        'zha',
    ],
    suffixes: [
        'ah',
        'el',
        'in',
        'or',
        'ru',
        'ik',
        'mel',
        'sor',
        'tiv',
        'ul',
        'vex',
        'zha',
        'dah',
        'lin',
        'yn',
        'mar',
    ],
    domain: 'nonce/flow/intent',
};
/**
 * Avali - Emotional resonance, diplomacy
 * Used for: AAD/header/metadata
 */
exports.AVALI = {
    code: 'av',
    name: 'Avali',
    prefixes: [
        'saina',
        'talan',
        'vessa',
        'maren',
        'oriel',
        'serin',
        'nurel',
        'lirea',
        'kiva',
        'lumen',
        'calma',
        'ponte',
        'verin',
        'nava',
        'sela',
        'tide',
    ],
    suffixes: [
        'a',
        'e',
        'i',
        'o',
        'u',
        'y',
        'la',
        're',
        'na',
        'sa',
        'to',
        'mi',
        've',
        'ri',
        'en',
        'ul',
    ],
    domain: 'aad/header/metadata',
};
/**
 * Runethic - Historical binding, permanence
 * Used for: Salt encoding
 */
exports.RUNETHIC = {
    code: 'ru',
    name: 'Runethic',
    prefixes: [
        'khar',
        'drath',
        'bront',
        'vael',
        'ur',
        'mem',
        'krak',
        'tharn',
        'groth',
        'basalt',
        'rune',
        'sear',
        'oath',
        'gnarl',
        'rift',
        'iron',
    ],
    suffixes: [
        'ak',
        'eth',
        'ik',
        'ul',
        'or',
        'ar',
        'um',
        'on',
        'ir',
        'esh',
        'nul',
        'vek',
        'dra',
        'kh',
        'va',
        'th',
    ],
    domain: 'salt/binding',
};
/**
 * Cassisivadan - Divine invocation, mathematics, bitcraft
 * Used for: Ciphertext encoding
 */
exports.CASSISIVADAN = {
    code: 'ca',
    name: 'Cassisivadan',
    prefixes: [
        'bip',
        'bop',
        'klik',
        'loopa',
        'ifta',
        'thena',
        'elsa',
        'spira',
        'rythm',
        'quirk',
        'fizz',
        'gear',
        'pop',
        'zip',
        'mix',
        'chass',
    ],
    suffixes: [
        'a',
        'e',
        'i',
        'o',
        'u',
        'y',
        'ta',
        'na',
        'sa',
        'ra',
        'lo',
        'mi',
        'ki',
        'zi',
        'qwa',
        'sh',
    ],
    domain: 'ciphertext/bitcraft',
};
/**
 * Umbroth - Shadow protocols, veiling
 * Used for: Redaction encoding
 */
exports.UMBROTH = {
    code: 'um',
    name: 'Umbroth',
    prefixes: [
        'veil',
        'zhur',
        'nar',
        'shul',
        'math',
        'hollow',
        'hush',
        'thorn',
        'dusk',
        'echo',
        'ink',
        'wisp',
        'bind',
        'ache',
        'null',
        'shade',
    ],
    suffixes: [
        'a',
        'e',
        'i',
        'o',
        'u',
        'ae',
        'sh',
        'th',
        'ak',
        'ul',
        'or',
        'ir',
        'en',
        'on',
        'vek',
        'nul',
    ],
    domain: 'redaction/veil',
};
/**
 * Draumric - Power amplification, structure
 * Used for: Auth tag encoding
 */
exports.DRAUMRIC = {
    code: 'dr',
    name: 'Draumric',
    prefixes: [
        'anvil',
        'tharn',
        'mek',
        'grond',
        'draum',
        'ektal',
        'temper',
        'forge',
        'stone',
        'steam',
        'oath',
        'seal',
        'frame',
        'pillar',
        'rivet',
        'ember',
    ],
    suffixes: [
        'a',
        'e',
        'i',
        'o',
        'u',
        'ae',
        'rak',
        'mek',
        'tharn',
        'grond',
        'vek',
        'ul',
        'or',
        'ar',
        'en',
        'on',
    ],
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
/**
 * Validate a lexicon definition
 * @throws Error if invalid
 */
function validateLexicon(lexicon) {
    if (!lexicon.code || typeof lexicon.code !== 'string') {
        throw new Error('Lexicon must have a string code');
    }
    if (lexicon.code.length !== 2) {
        throw new Error(`Lexicon code must be 2 characters, got: ${lexicon.code}`);
    }
    if (!lexicon.name || typeof lexicon.name !== 'string') {
        throw new Error('Lexicon must have a string name');
    }
    if (!Array.isArray(lexicon.prefixes) || lexicon.prefixes.length !== 16) {
        throw new Error(`Lexicon ${lexicon.code} must have exactly 16 prefixes, got ${lexicon.prefixes?.length}`);
    }
    if (!Array.isArray(lexicon.suffixes) || lexicon.suffixes.length !== 16) {
        throw new Error(`Lexicon ${lexicon.code} must have exactly 16 suffixes, got ${lexicon.suffixes?.length}`);
    }
    // Check for unique prefixes and suffixes
    const uniquePrefixes = new Set(lexicon.prefixes);
    if (uniquePrefixes.size !== 16) {
        throw new Error(`Lexicon ${lexicon.code} has duplicate prefixes`);
    }
    const uniqueSuffixes = new Set(lexicon.suffixes);
    if (uniqueSuffixes.size !== 16) {
        throw new Error(`Lexicon ${lexicon.code} has duplicate suffixes`);
    }
}
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
function registerTongue(lexicon) {
    validateLexicon(lexicon);
    const spec = {
        code: lexicon.code,
        name: lexicon.name,
        prefixes: Object.freeze([...lexicon.prefixes]),
        suffixes: Object.freeze([...lexicon.suffixes]),
        domain: lexicon.domain,
    };
    exports.TONGUES[lexicon.code] = spec;
}
/**
 * Load multiple tongues from a lexicon file object.
 *
 * @example
 * const lexiconData = JSON.parse(fs.readFileSync('custom-lexicons.json', 'utf-8'));
 * loadLexicons(lexiconData);
 */
function loadLexicons(file) {
    const loaded = [];
    const errors = [];
    for (const lexicon of file.tongues) {
        try {
            registerTongue(lexicon);
            loaded.push(lexicon.code);
        }
        catch (e) {
            errors.push(`${lexicon.code}: ${e instanceof Error ? e.message : String(e)}`);
        }
    }
    return { loaded, errors };
}
/**
 * Reset tongues to built-in defaults.
 * Useful for testing or resetting after loading custom lexicons.
 */
function resetToDefaultTongues() {
    exports.TONGUES.ko = exports.KOR_AELIN;
    exports.TONGUES.av = exports.AVALI;
    exports.TONGUES.ru = exports.RUNETHIC;
    exports.TONGUES.ca = exports.CASSISIVADAN;
    exports.TONGUES.um = exports.UMBROTH;
    exports.TONGUES.dr = exports.DRAUMRIC;
}
/**
 * Get all registered tongue codes
 */
function getRegisteredTongues() {
    return Object.keys(exports.TONGUES);
}
/**
 * Check if a tongue code is registered
 */
function hasTongue(code) {
    return code in exports.TONGUES;
}
//# sourceMappingURL=sacredTongues.js.map