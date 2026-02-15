"use strict";
/**
 * @file linguisticCrossTalk.ts
 * @module harmonic/linguisticCrossTalk
 * @layer Layer 9, Layer 10, Layer 13
 * @component Linguistic Cross-Talk Kernel
 * @version 3.2.5
 *
 * Cross-domain reasoning kernel mapping the Six Sacred Tongues to academic
 * knowledge domains. Creates an interconnected but not fragile nodal network
 * for cross-domain AI reasoning.
 *
 * Architecture:
 *   6 tongues × 6 academic domains × 16 polyhedral validators
 *   → Golden-ratio-weighted cross-talk graph
 *   → Tokenize → Route → Translate → Validate pipeline
 *
 * Academic Domain Mapping:
 *   KO (Kor'aelin)     → Humanities       (identity, narrative, context, authority)
 *   AV (Avali)          → Social Sciences  (temporal dynamics, diplomacy, empathy)
 *   RU (Runethic)       → Mathematics      (binding, formal structures, proofs)
 *   CA (Cassisivadan)   → Engineering      (bitcraft, verification, building)
 *   UM (Umbroth)        → Creative Arts    (shadow, veiling, intuition, expression)
 *   DR (Draumric)       → Physical Sciences (structure, power, material, forge)
 *
 * Cross-talk edges connect domains with golden ratio decay weights.
 * Polyhedral families serve as validators at domain intersections.
 *
 * Patent kernel: Six Sacred Tongues as 6D vector navigation where each
 * dimension processes through its own linguistic lens, creating emergent
 * cross-domain properties impossible in single-language systems.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultCrossTalkKernel = exports.CrossTalkKernel = exports.DEFAULT_KERNEL_CONFIG = exports.DOMAIN_PROFILES = exports.ALL_DOMAINS = exports.ALL_TONGUES = void 0;
exports.buildCrossTalkEdges = buildCrossTalkEdges;
exports.isValidatorAvailable = isValidatorAvailable;
exports.validatorFacetCount = validatorFacetCount;
exports.validationStrength = validationStrength;
exports.domainToTongue = domainToTongue;
exports.tongueToDomain = tongueToDomain;
exports.resonanceToVector = resonanceToVector;
exports.computeVagueness = computeVagueness;
exports.createCrossTalkKernel = createCrossTalkKernel;
// ═══════════════════════════════════════════════════════════════
// Types and Constants
// ═══════════════════════════════════════════════════════════════
/** Golden ratio φ = (1 + √5) / 2 */
const PHI = (1 + Math.sqrt(5)) / 2;
/** All tongue codes in canonical order */
exports.ALL_TONGUES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
/** All domains in canonical order (matching tongue order) */
exports.ALL_DOMAINS = [
    'humanities',
    'social_sciences',
    'mathematics',
    'engineering',
    'creative_arts',
    'physical_sciences',
];
/**
 * Complete domain profile mapping.
 *
 * Integrates:
 * - sacredTongues.ts domains (nonce/flow, aad/header, salt/binding, etc.)
 * - SACRED_TONGUE_SPECTRAL_MAP.md roles (Foundation, Temporal, Verification, etc.)
 * - SIX_SACRED_TONGUES_CODEX.md grammar rules
 * - Patent doc 6D axes (ShadowWeave, Starfire, etc.)
 * - User's academic domain mapping
 */
exports.DOMAIN_PROFILES = {
    KO: {
        tongue: 'KO',
        domain: 'humanities',
        grammar: 'SOV',
        languesWeight: Math.pow(PHI, 0), // 1.000
        navigatorWeight: 1.0,
        technicalRole: 'Identity/Context — nonce, flow, intent, command authority',
        academicRole: 'Humanities — narrative, history, philosophy, cultural studies',
        vaguenessStrategy: 'contextual_grounding',
    },
    AV: {
        tongue: 'AV',
        domain: 'social_sciences',
        grammar: 'SVO',
        languesWeight: Math.pow(PHI, 1), // 1.618
        navigatorWeight: 1 / PHI,
        technicalRole: 'Temporal/Phase — aad, header, metadata, diplomacy',
        academicRole: 'Social Sciences — psychology, sociology, economics, political science',
        vaguenessStrategy: 'temporal_contextualization',
    },
    RU: {
        tongue: 'RU',
        domain: 'mathematics',
        grammar: 'VSO',
        languesWeight: Math.pow(PHI, 2), // 2.618
        navigatorWeight: 1 / (PHI * PHI),
        technicalRole: 'Energy/Spectral — salt, binding, permanence',
        academicRole: 'Mathematics — algebra, analysis, topology, formal logic',
        vaguenessStrategy: 'formal_binding',
    },
    CA: {
        tongue: 'CA',
        domain: 'engineering',
        grammar: 'OVS',
        languesWeight: Math.pow(PHI, 3), // 4.236
        navigatorWeight: 1 / (PHI * PHI * PHI),
        technicalRole: 'Verification/Consensus — ciphertext, bitcraft, math',
        academicRole: 'Engineering — software, mechanical, electrical, systems',
        vaguenessStrategy: 'modular_decomposition',
    },
    UM: {
        tongue: 'UM',
        domain: 'creative_arts',
        grammar: 'VOS',
        languesWeight: Math.pow(PHI, 4), // 6.854
        navigatorWeight: 1 / (PHI * PHI * PHI * PHI),
        technicalRole: 'Trust/Decision — redaction, veil, shadow protocols',
        academicRole: 'Creative Arts — visual arts, music, design, creative writing',
        vaguenessStrategy: 'intuitive_exploration',
    },
    DR: {
        tongue: 'DR',
        domain: 'physical_sciences',
        grammar: 'OSV',
        languesWeight: Math.pow(PHI, 5), // 11.09
        navigatorWeight: 1 / (PHI * PHI * PHI * PHI * PHI),
        technicalRole: 'Deep Security — auth tag, structure, power amplification',
        academicRole: 'Physical Sciences — physics, chemistry, materials science, astronomy',
        vaguenessStrategy: 'structural_analysis',
    },
};
/**
 * Build the cross-talk edge set.
 *
 * Edge weights use golden ratio scaling based on "distance" between tongues
 * in the spectral ordering (KO→AV→RU→CA→UM→DR wrapping around).
 *
 * Adjacent pairs get the strongest cross-talk (1/φ ≈ 0.618).
 * Complementary (opposite) pairs get moderate cross-talk (1/φ² ≈ 0.382).
 * Bridging pairs get the weakest (1/φ³ ≈ 0.236).
 */
function buildCrossTalkEdges() {
    const edges = [];
    const n = exports.ALL_TONGUES.length;
    for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
            const from = exports.ALL_TONGUES[i];
            const to = exports.ALL_TONGUES[j];
            // Circular distance (min of clockwise/counter-clockwise)
            const rawDist = Math.min(j - i, n - (j - i));
            let relationship;
            let weight;
            let validator;
            if (rawDist === 1) {
                // Adjacent in spectral ordering
                relationship = 'adjacent';
                weight = 1 / PHI; // ≈ 0.618
                validator = 'platonic'; // Always valid
            }
            else if (rawDist === 3) {
                // Opposite (complementary)
                relationship = 'complementary';
                weight = 1 / (PHI * PHI); // ≈ 0.382
                validator = 'archimedean'; // Needs processing layer
            }
            else if (rawDist === 2) {
                // Two apart — harmonic relationship (φ-related interval)
                relationship = 'harmonic';
                weight = 1 / (PHI * PHI * PHI); // ≈ 0.236
                validator = 'johnson'; // Domain connectors
            }
            else {
                relationship = 'bridging';
                weight = 1 / (PHI * PHI * PHI * PHI); // ≈ 0.146
                validator = 'kepler-poinsot'; // High-risk
            }
            // Bidirectional edges
            edges.push({ from, to, weight, relationship, validator });
            edges.push({ from: to, to: from, weight, relationship, validator });
        }
    }
    return edges;
}
exports.DEFAULT_KERNEL_CONFIG = {
    minTranslationConfidence: 0.3,
    vaguenessThreshold: 0.4,
    maxRouteLength: 4,
    allowThreshold: 0.6,
    denyThreshold: 0.3,
    fluxState: 'POLLY',
};
// ═══════════════════════════════════════════════════════════════
// Domain Keyword Maps (for tokenization heuristics)
// ═══════════════════════════════════════════════════════════════
/**
 * Keyword→domain signal map.
 * Used by the tokenizer to detect domain affinity.
 * Each keyword maps to a partial resonance vector across domains.
 */
const DOMAIN_KEYWORDS = {
    // Humanities keywords
    narrative: { humanities: 0.9, social_sciences: 0.3, creative_arts: 0.4 },
    identity: { humanities: 0.8, social_sciences: 0.5 },
    history: { humanities: 0.9, social_sciences: 0.4 },
    philosophy: { humanities: 0.9, mathematics: 0.3 },
    ethics: { humanities: 0.8, social_sciences: 0.5 },
    culture: { humanities: 0.8, social_sciences: 0.6, creative_arts: 0.3 },
    language: { humanities: 0.7, social_sciences: 0.3, engineering: 0.2 },
    meaning: { humanities: 0.7, creative_arts: 0.4 },
    context: { humanities: 0.7, social_sciences: 0.4 },
    // Social Sciences keywords
    society: { social_sciences: 0.9, humanities: 0.4 },
    behavior: { social_sciences: 0.8, humanities: 0.3 },
    economics: { social_sciences: 0.9, mathematics: 0.5 },
    psychology: { social_sciences: 0.9, humanities: 0.3 },
    temporal: { social_sciences: 0.6, physical_sciences: 0.5, mathematics: 0.3 },
    policy: { social_sciences: 0.8, humanities: 0.3 },
    diplomacy: { social_sciences: 0.8, humanities: 0.4 },
    interaction: { social_sciences: 0.7, engineering: 0.3 },
    // Mathematics keywords
    proof: { mathematics: 0.9, engineering: 0.3 },
    theorem: { mathematics: 0.95 },
    algebra: { mathematics: 0.9, engineering: 0.2 },
    topology: { mathematics: 0.9, physical_sciences: 0.3 },
    equation: { mathematics: 0.8, physical_sciences: 0.5, engineering: 0.3 },
    function: { mathematics: 0.7, engineering: 0.5 },
    logic: { mathematics: 0.8, humanities: 0.3, engineering: 0.3 },
    symmetry: { mathematics: 0.7, physical_sciences: 0.5, creative_arts: 0.3 },
    formal: { mathematics: 0.7, humanities: 0.2 },
    binding: { mathematics: 0.6, engineering: 0.4 },
    // Engineering keywords
    system: { engineering: 0.7, social_sciences: 0.2, physical_sciences: 0.3 },
    build: { engineering: 0.8, creative_arts: 0.3 },
    design: { engineering: 0.7, creative_arts: 0.6 },
    algorithm: { engineering: 0.8, mathematics: 0.6 },
    verification: { engineering: 0.8, mathematics: 0.4 },
    optimization: { engineering: 0.7, mathematics: 0.6 },
    modular: { engineering: 0.8, mathematics: 0.3 },
    protocol: { engineering: 0.7, social_sciences: 0.2 },
    structure: { engineering: 0.6, physical_sciences: 0.5, mathematics: 0.3 },
    // Creative Arts keywords
    art: { creative_arts: 0.9, humanities: 0.4 },
    music: { creative_arts: 0.9, mathematics: 0.3 },
    creative: { creative_arts: 0.9, humanities: 0.3 },
    expression: { creative_arts: 0.7, humanities: 0.5 },
    intuition: { creative_arts: 0.7, humanities: 0.3, social_sciences: 0.3 },
    aesthetic: { creative_arts: 0.8, humanities: 0.5 },
    imagination: { creative_arts: 0.9, humanities: 0.3 },
    shadow: { creative_arts: 0.5, humanities: 0.3, physical_sciences: 0.2 },
    // Physical Sciences keywords
    physics: { physical_sciences: 0.95 },
    energy: { physical_sciences: 0.8, engineering: 0.4 },
    force: { physical_sciences: 0.8, social_sciences: 0.2 },
    matter: { physical_sciences: 0.8, humanities: 0.2 },
    wave: { physical_sciences: 0.7, mathematics: 0.4, creative_arts: 0.2 },
    particle: { physical_sciences: 0.8, mathematics: 0.3 },
    material: { physical_sciences: 0.7, engineering: 0.5 },
    quantum: { physical_sciences: 0.8, mathematics: 0.5 },
    entropy: { physical_sciences: 0.7, mathematics: 0.5 },
    forge: { physical_sciences: 0.5, engineering: 0.5, creative_arts: 0.2 },
};
// ═══════════════════════════════════════════════════════════════
// Polyhedral Validation
// ═══════════════════════════════════════════════════════════════
/** Families available per flux state (from phdm.ts FLUX_FAMILIES) */
const FLUX_VALIDATORS = {
    POLLY: ['platonic', 'archimedean', 'kepler-poinsot', 'toroidal', 'johnson', 'rhombic'],
    QUASI: ['platonic', 'archimedean'],
    DEMI: ['platonic'],
};
/**
 * Check if a polyhedral validator is available under the current flux state.
 */
function isValidatorAvailable(validator, fluxState) {
    return FLUX_VALIDATORS[fluxState].includes(validator);
}
/**
 * Polyhedral facet count for a validator family.
 * Used to compute validation strength — more facets = more thorough.
 *
 * Based on total faces across polyhedra in each family from CANONICAL_POLYHEDRA.
 */
function validatorFacetCount(validator) {
    const FACET_COUNTS = {
        platonic: 50, // 4+6+8+12+20
        archimedean: 54, // 8+14+32
        'kepler-poinsot': 24, // 12+12
        toroidal: 28, // 14+14
        johnson: 18, // 10+8
        rhombic: 24, // 12+12
    };
    return FACET_COUNTS[validator];
}
/**
 * Compute validation strength for a cross-talk edge.
 * Combines facet count normalization with flux state availability.
 *
 * Returns 0 if validator not available, else normalized facet score.
 */
function validationStrength(edge, fluxState) {
    if (!isValidatorAvailable(edge.validator, fluxState)) {
        return 0;
    }
    // Normalize by max facets (archimedean has 54)
    return validatorFacetCount(edge.validator) / 54;
}
// ═══════════════════════════════════════════════════════════════
// Utility: Domain ↔ Tongue Mapping
// ═══════════════════════════════════════════════════════════════
/** Map domain → tongue */
function domainToTongue(domain) {
    const idx = exports.ALL_DOMAINS.indexOf(domain);
    return exports.ALL_TONGUES[idx];
}
/** Map tongue → domain */
function tongueToDomain(tongue) {
    return exports.DOMAIN_PROFILES[tongue].domain;
}
/** Get the 6D resonance vector as a plain array (domain order) */
function resonanceToVector(resonance) {
    return exports.ALL_DOMAINS.map((d) => resonance[d] ?? 0);
}
/** Compute vagueness from a resonance vector: 1 - (max - secondMax) / max */
function computeVagueness(resonance) {
    const values = exports.ALL_DOMAINS.map((d) => resonance[d] ?? 0);
    const sorted = [...values].sort((a, b) => b - a);
    if (sorted[0] <= 0)
        return 1.0; // No signal at all → maximally vague
    if (sorted.length < 2 || sorted[1] <= 0)
        return 0.0; // Only one domain → not vague
    // Vagueness = how close the top two domains are
    return sorted[1] / sorted[0];
}
// ═══════════════════════════════════════════════════════════════
// Cross-Talk Kernel
// ═══════════════════════════════════════════════════════════════
/**
 * Linguistic Cross-Talk Kernel
 *
 * The "spiral" that handles vague inputs by tokenizing them into domain-tagged
 * fragments, routing through the cross-talk graph, translating between domains,
 * and validating through polyhedral facets in hyperbolic space.
 *
 * @example
 * ```typescript
 * const kernel = new CrossTalkKernel();
 *
 * // Process a vague cross-domain query
 * const result = kernel.process('How does wave symmetry relate to musical design?');
 *
 * // result.primaryDomain → 'physical_sciences' (wave)
 * // result.translations → cross-domain links to creative_arts (music) + mathematics (symmetry)
 * // result.resonanceVector → [0.1, 0.1, 0.5, 0.2, 0.6, 0.7]
 * // result.coherence → 0.82
 * ```
 */
class CrossTalkKernel {
    config;
    edges;
    /** Adjacency list for routing: tongue → outgoing edges */
    adjacency;
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_KERNEL_CONFIG, ...config };
        this.edges = buildCrossTalkEdges();
        // Build adjacency list
        this.adjacency = new Map();
        for (const t of exports.ALL_TONGUES) {
            this.adjacency.set(t, []);
        }
        for (const edge of this.edges) {
            this.adjacency.get(edge.from).push(edge);
        }
    }
    // ─────────────────────────────────────────────────────────────
    // Tokenization
    // ─────────────────────────────────────────────────────────────
    /**
     * Tokenize input text into domain-tagged tokens.
     *
     * Splits on whitespace, looks up each word in the keyword map to build
     * a 6D resonance vector, then assigns primary domain and vagueness.
     */
    tokenize(input) {
        const words = input
            .toLowerCase()
            .replace(/[^a-z0-9\s]/g, '')
            .split(/\s+/)
            .filter((w) => w.length > 0);
        return words.map((word) => {
            const signals = DOMAIN_KEYWORDS[word];
            const resonance = {
                humanities: 0,
                social_sciences: 0,
                mathematics: 0,
                engineering: 0,
                creative_arts: 0,
                physical_sciences: 0,
            };
            if (signals) {
                for (const [domain, score] of Object.entries(signals)) {
                    if (exports.ALL_DOMAINS.includes(domain)) {
                        resonance[domain] = score;
                    }
                }
            }
            // Find primary domain (highest resonance)
            let primaryDomain = 'humanities';
            let maxScore = 0;
            for (const d of exports.ALL_DOMAINS) {
                if (resonance[d] > maxScore) {
                    maxScore = resonance[d];
                    primaryDomain = d;
                }
            }
            const vagueness = computeVagueness(resonance);
            const primaryTongue = domainToTongue(primaryDomain);
            return { content: word, primaryDomain, primaryTongue, resonance, vagueness };
        });
    }
    // ─────────────────────────────────────────────────────────────
    // Cross-Domain Translation
    // ─────────────────────────────────────────────────────────────
    /**
     * Translate a token from its primary domain to a target domain.
     * Confidence is based on: token's resonance in target × edge weight × validation strength.
     */
    translate(token, targetDomain) {
        if (token.primaryDomain === targetDomain)
            return null;
        const sourceTongue = token.primaryTongue;
        const targetTongue = domainToTongue(targetDomain);
        // Find edge
        const outEdges = this.adjacency.get(sourceTongue) ?? [];
        const edge = outEdges.find((e) => e.to === targetTongue);
        if (!edge)
            return null;
        // Compute confidence
        const targetResonance = token.resonance[targetDomain] ?? 0;
        const valStrength = validationStrength(edge, this.config.fluxState);
        const confidence = targetResonance * edge.weight * (0.5 + 0.5 * valStrength);
        if (confidence < this.config.minTranslationConfidence)
            return null;
        const validated = valStrength > 0;
        return {
            source: { domain: token.primaryDomain, tongue: sourceTongue },
            target: { domain: targetDomain, tongue: targetTongue },
            edge,
            confidence,
            validated,
        };
    }
    /**
     * Find all valid cross-domain translations for a token.
     */
    translateAll(token) {
        const results = [];
        for (const domain of exports.ALL_DOMAINS) {
            const t = this.translate(token, domain);
            if (t)
                results.push(t);
        }
        return results.sort((a, b) => b.confidence - a.confidence);
    }
    // ─────────────────────────────────────────────────────────────
    // Route Finding
    // ─────────────────────────────────────────────────────────────
    /**
     * Find the best route between two tongues through the cross-talk graph.
     *
     * Uses BFS with weight accumulation (product of edge weights).
     * Respects flux state: routes through unavailable validators are pruned.
     */
    findRoute(from, to) {
        if (from === to) {
            return { path: [from], edges: [], cumulativeWeight: 1.0, allValidated: true };
        }
        const queue = [
            { tongue: from, path: [from], edges: [], weight: 1.0, allValidated: true },
        ];
        const visited = new Set([from]);
        let bestRoute = null;
        while (queue.length > 0) {
            const current = queue.shift();
            if (current.path.length > this.config.maxRouteLength)
                continue;
            const outEdges = this.adjacency.get(current.tongue) ?? [];
            for (const edge of outEdges) {
                if (visited.has(edge.to))
                    continue;
                const valAvailable = isValidatorAvailable(edge.validator, this.config.fluxState);
                const newWeight = current.weight * edge.weight;
                const newPath = [...current.path, edge.to];
                const newEdges = [...current.edges, edge];
                const newValidated = current.allValidated && valAvailable;
                if (edge.to === to) {
                    const route = {
                        path: newPath,
                        edges: newEdges,
                        cumulativeWeight: newWeight,
                        allValidated: newValidated,
                    };
                    if (!bestRoute || route.cumulativeWeight > bestRoute.cumulativeWeight) {
                        bestRoute = route;
                    }
                }
                else {
                    visited.add(edge.to);
                    queue.push({
                        tongue: edge.to,
                        path: newPath,
                        edges: newEdges,
                        weight: newWeight,
                        allValidated: newValidated,
                    });
                }
            }
        }
        return bestRoute;
    }
    // ─────────────────────────────────────────────────────────────
    // Main Processing Pipeline
    // ─────────────────────────────────────────────────────────────
    /**
     * Process input through the full cross-talk pipeline:
     *
     * 1. Tokenize → domain-tagged tokens
     * 2. Aggregate → 6D resonance vector
     * 3. Route → find cross-domain paths for vague tokens
     * 4. Translate → cross-domain translations
     * 5. Validate → polyhedral checks
     * 6. Score → coherence and governance decision
     */
    process(input) {
        // 1. Tokenize
        const tokens = this.tokenize(input);
        // 2. Aggregate resonance vector
        const aggregated = {
            humanities: 0,
            social_sciences: 0,
            mathematics: 0,
            engineering: 0,
            creative_arts: 0,
            physical_sciences: 0,
        };
        let signalCount = 0;
        for (const token of tokens) {
            for (const d of exports.ALL_DOMAINS) {
                if (token.resonance[d] > 0) {
                    aggregated[d] += token.resonance[d];
                    signalCount++;
                }
            }
        }
        // Normalize
        const maxAgg = Math.max(...exports.ALL_DOMAINS.map((d) => aggregated[d]), 1e-10);
        for (const d of exports.ALL_DOMAINS) {
            aggregated[d] /= maxAgg;
        }
        // Primary domain
        let primaryDomain = 'humanities';
        let maxScore = 0;
        for (const d of exports.ALL_DOMAINS) {
            if (aggregated[d] > maxScore) {
                maxScore = aggregated[d];
                primaryDomain = d;
            }
        }
        // 3. Route — find cross-domain paths for vague tokens
        const allTranslations = [];
        let bestRoute = null;
        for (const token of tokens) {
            if (token.vagueness >= this.config.vaguenessThreshold) {
                // Token is vague — try cross-domain translations
                const translations = this.translateAll(token);
                allTranslations.push(...translations);
            }
        }
        // Find route between the two strongest non-primary domains
        const sortedDomains = exports.ALL_DOMAINS
            .filter((d) => d !== primaryDomain)
            .sort((a, b) => aggregated[b] - aggregated[a]);
        if (sortedDomains.length >= 1 && aggregated[sortedDomains[0]] > 0.2) {
            const primaryTongue = domainToTongue(primaryDomain);
            const secondaryTongue = domainToTongue(sortedDomains[0]);
            bestRoute = this.findRoute(primaryTongue, secondaryTongue);
        }
        // 4. Compute resonance vector
        const resonanceVector = exports.ALL_DOMAINS.map((d) => aggregated[d]);
        // 5. Compute coherence
        const coherence = this.computeCoherence(resonanceVector, allTranslations, bestRoute);
        // 6. Governance decision
        let decision;
        if (coherence >= this.config.allowThreshold) {
            decision = 'ALLOW';
        }
        else if (coherence >= this.config.denyThreshold) {
            decision = 'QUARANTINE';
        }
        else {
            decision = 'DENY';
        }
        return {
            tokens,
            primaryDomain,
            translations: allTranslations,
            route: bestRoute,
            resonanceVector,
            coherence,
            decision,
        };
    }
    // ─────────────────────────────────────────────────────────────
    // Coherence Scoring
    // ─────────────────────────────────────────────────────────────
    /**
     * Compute overall coherence from:
     * - Resonance concentration (how focused the signal is)
     * - Translation quality (average confidence of valid translations)
     * - Route integrity (whether polyhedral validators passed)
     */
    computeCoherence(resonanceVector, translations, route) {
        // Resonance concentration: normalized entropy (low entropy = focused = good)
        const total = resonanceVector.reduce((s, v) => s + v, 0);
        if (total <= 0)
            return 0;
        const probs = resonanceVector.map((v) => v / total);
        let entropy = 0;
        for (const p of probs) {
            if (p > 0)
                entropy -= p * Math.log2(p);
        }
        const maxEntropy = Math.log2(6); // 6 domains
        const concentration = 1 - entropy / maxEntropy;
        // Translation quality
        let translationScore = 0;
        if (translations.length > 0) {
            const validTranslations = translations.filter((t) => t.validated);
            const avgConfidence = validTranslations.reduce((s, t) => s + t.confidence, 0) /
                Math.max(validTranslations.length, 1);
            translationScore = avgConfidence;
        }
        // Route integrity
        let routeScore = 0;
        if (route) {
            routeScore = route.allValidated ? route.cumulativeWeight : route.cumulativeWeight * 0.5;
        }
        // Weighted combination
        // If no translations needed (focused query), concentration dominates
        if (translations.length === 0) {
            return Math.min(1, concentration * 0.8 + 0.2);
        }
        return Math.min(1, concentration * 0.4 + translationScore * 0.35 + routeScore * 0.25);
    }
    // ─────────────────────────────────────────────────────────────
    // Analysis Methods
    // ─────────────────────────────────────────────────────────────
    /**
     * Get the cross-talk affinity between two domains.
     * Returns the edge weight if a direct edge exists, or the best route weight.
     */
    domainAffinity(domainA, domainB) {
        if (domainA === domainB)
            return 1.0;
        const tongueA = domainToTongue(domainA);
        const tongueB = domainToTongue(domainB);
        // Direct edge?
        const outEdges = this.adjacency.get(tongueA) ?? [];
        const direct = outEdges.find((e) => e.to === tongueB);
        if (direct) {
            const valStrength = validationStrength(direct, this.config.fluxState);
            return direct.weight * (valStrength > 0 ? 1.0 : 0.5);
        }
        // Route
        const route = this.findRoute(tongueA, tongueB);
        return route ? route.cumulativeWeight : 0;
    }
    /**
     * Compute the full 6×6 affinity matrix between all domains.
     */
    affinityMatrix() {
        return exports.ALL_DOMAINS.map((a) => exports.ALL_DOMAINS.map((b) => this.domainAffinity(a, b)));
    }
    /**
     * Identify which domains a query resonates with most strongly.
     * Returns sorted list of (domain, score) pairs.
     */
    domainResonance(input) {
        const result = this.process(input);
        return exports.ALL_DOMAINS
            .map((d, i) => ({
            domain: d,
            tongue: domainToTongue(d),
            score: result.resonanceVector[i],
        }))
            .sort((a, b) => b.score - a.score);
    }
    /**
     * Get all edges in the cross-talk graph.
     */
    getEdges() {
        return [...this.edges];
    }
    /**
     * Get the kernel configuration.
     */
    getConfig() {
        return { ...this.config };
    }
}
exports.CrossTalkKernel = CrossTalkKernel;
// ═══════════════════════════════════════════════════════════════
// Factory and Default Instance
// ═══════════════════════════════════════════════════════════════
/**
 * Create a cross-talk kernel with custom configuration.
 */
function createCrossTalkKernel(config) {
    return new CrossTalkKernel(config);
}
/**
 * Default cross-talk kernel instance (POLLY mode, all validators active).
 */
exports.defaultCrossTalkKernel = new CrossTalkKernel();
//# sourceMappingURL=linguisticCrossTalk.js.map