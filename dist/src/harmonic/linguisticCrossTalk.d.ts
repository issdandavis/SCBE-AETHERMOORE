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
/** Tongue code (uppercase, matching sacredEggs.ts convention) */
export type TongueCode = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/** All tongue codes in canonical order */
export declare const ALL_TONGUES: TongueCode[];
/** Academic knowledge domains */
export type AcademicDomain = 'humanities' | 'social_sciences' | 'mathematics' | 'engineering' | 'creative_arts' | 'physical_sciences';
/** All domains in canonical order (matching tongue order) */
export declare const ALL_DOMAINS: AcademicDomain[];
/** Grammar type for each tongue (from codex) */
export type GrammarType = 'SOV' | 'VSO' | 'SVO' | 'OVS' | 'VOS' | 'OSV';
/**
 * Domain metadata: links a tongue to its academic domain with properties
 */
export interface DomainProfile {
    tongue: TongueCode;
    domain: AcademicDomain;
    /** Grammar type parallels encoding strategy */
    grammar: GrammarType;
    /** Golden ratio weight (φ^(index) for langues, 1/φ^(index) for navigator) */
    languesWeight: number;
    navigatorWeight: number;
    /** Semantic role from existing codebase */
    technicalRole: string;
    /** Academic description */
    academicRole: string;
    /** How this domain handles vagueness */
    vaguenessStrategy: string;
}
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
export declare const DOMAIN_PROFILES: Record<TongueCode, DomainProfile>;
/**
 * Cross-talk edge: weighted connection between two tongue domains
 */
export interface CrossTalkEdge {
    /** Source tongue */
    from: TongueCode;
    /** Target tongue */
    to: TongueCode;
    /** Edge weight ∈ (0, 1] — higher = stronger cross-talk */
    weight: number;
    /** Type of cross-domain relationship */
    relationship: CrossTalkRelationship;
    /** Which polyhedral family validates this edge */
    validator: PolyhedralValidator;
}
/** Types of cross-domain relationships */
export type CrossTalkRelationship = 'adjacent' | 'complementary' | 'harmonic' | 'bridging';
/** Polyhedral family that validates a cross-talk edge */
export type PolyhedralValidator = 'platonic' | 'archimedean' | 'kepler-poinsot' | 'toroidal' | 'johnson' | 'rhombic';
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
export declare function buildCrossTalkEdges(): CrossTalkEdge[];
/**
 * A token tagged with domain information for cross-talk routing
 */
export interface DomainToken {
    /** Original input fragment */
    content: string;
    /** Primary domain this token belongs to */
    primaryDomain: AcademicDomain;
    /** Primary tongue for this domain */
    primaryTongue: TongueCode;
    /** Resonance scores across all 6 domains (6D vector) */
    resonance: Record<AcademicDomain, number>;
    /** Vagueness score ∈ [0, 1] — how ambiguous this token is across domains */
    vagueness: number;
}
/**
 * Cross-domain translation result
 */
export interface CrossDomainTranslation {
    /** Source domain and tongue */
    source: {
        domain: AcademicDomain;
        tongue: TongueCode;
    };
    /** Target domain and tongue */
    target: {
        domain: AcademicDomain;
        tongue: TongueCode;
    };
    /** Cross-talk edge used */
    edge: CrossTalkEdge;
    /** Translation confidence ∈ [0, 1] */
    confidence: number;
    /** Polyhedral validation passed? */
    validated: boolean;
}
/**
 * Route through the cross-talk graph
 */
export interface CrossTalkRoute {
    /** Sequence of tongues visited */
    path: TongueCode[];
    /** Edges traversed */
    edges: CrossTalkEdge[];
    /** Cumulative route weight (product of edge weights) */
    cumulativeWeight: number;
    /** Whether all polyhedral validators passed */
    allValidated: boolean;
}
/**
 * Full kernel processing result
 */
export interface CrossTalkResult {
    /** Input tokens with domain tags */
    tokens: DomainToken[];
    /** Detected primary domain */
    primaryDomain: AcademicDomain;
    /** Cross-talk translations applied */
    translations: CrossDomainTranslation[];
    /** Best route through cross-talk graph */
    route: CrossTalkRoute | null;
    /** 6D resonance vector (one per domain) */
    resonanceVector: number[];
    /** Overall coherence score ∈ [0, 1] */
    coherence: number;
    /** Governance decision */
    decision: 'ALLOW' | 'QUARANTINE' | 'DENY';
}
export interface CrossTalkKernelConfig {
    /** Minimum confidence for cross-domain translation (default 0.3) */
    minTranslationConfidence: number;
    /** Vagueness threshold to trigger cross-domain routing (default 0.4) */
    vaguenessThreshold: number;
    /** Maximum route length through cross-talk graph (default 4) */
    maxRouteLength: number;
    /** Coherence threshold for ALLOW decision (default 0.6) */
    allowThreshold: number;
    /** Coherence threshold for QUARANTINE (below this → DENY) (default 0.3) */
    denyThreshold: number;
    /** Active flux state controls which validators are available */
    fluxState: 'POLLY' | 'QUASI' | 'DEMI';
}
export declare const DEFAULT_KERNEL_CONFIG: CrossTalkKernelConfig;
/**
 * Check if a polyhedral validator is available under the current flux state.
 */
export declare function isValidatorAvailable(validator: PolyhedralValidator, fluxState: 'POLLY' | 'QUASI' | 'DEMI'): boolean;
/**
 * Polyhedral facet count for a validator family.
 * Used to compute validation strength — more facets = more thorough.
 *
 * Based on total faces across polyhedra in each family from CANONICAL_POLYHEDRA.
 */
export declare function validatorFacetCount(validator: PolyhedralValidator): number;
/**
 * Compute validation strength for a cross-talk edge.
 * Combines facet count normalization with flux state availability.
 *
 * Returns 0 if validator not available, else normalized facet score.
 */
export declare function validationStrength(edge: CrossTalkEdge, fluxState: 'POLLY' | 'QUASI' | 'DEMI'): number;
/** Map domain → tongue */
export declare function domainToTongue(domain: AcademicDomain): TongueCode;
/** Map tongue → domain */
export declare function tongueToDomain(tongue: TongueCode): AcademicDomain;
/** Get the 6D resonance vector as a plain array (domain order) */
export declare function resonanceToVector(resonance: Record<AcademicDomain, number>): number[];
/** Compute vagueness from a resonance vector: 1 - (max - secondMax) / max */
export declare function computeVagueness(resonance: Record<AcademicDomain, number>): number;
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
export declare class CrossTalkKernel {
    private config;
    private edges;
    /** Adjacency list for routing: tongue → outgoing edges */
    private adjacency;
    constructor(config?: Partial<CrossTalkKernelConfig>);
    /**
     * Tokenize input text into domain-tagged tokens.
     *
     * Splits on whitespace, looks up each word in the keyword map to build
     * a 6D resonance vector, then assigns primary domain and vagueness.
     */
    tokenize(input: string): DomainToken[];
    /**
     * Translate a token from its primary domain to a target domain.
     * Confidence is based on: token's resonance in target × edge weight × validation strength.
     */
    translate(token: DomainToken, targetDomain: AcademicDomain): CrossDomainTranslation | null;
    /**
     * Find all valid cross-domain translations for a token.
     */
    translateAll(token: DomainToken): CrossDomainTranslation[];
    /**
     * Find the best route between two tongues through the cross-talk graph.
     *
     * Uses BFS with weight accumulation (product of edge weights).
     * Respects flux state: routes through unavailable validators are pruned.
     */
    findRoute(from: TongueCode, to: TongueCode): CrossTalkRoute | null;
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
    process(input: string): CrossTalkResult;
    /**
     * Compute overall coherence from:
     * - Resonance concentration (how focused the signal is)
     * - Translation quality (average confidence of valid translations)
     * - Route integrity (whether polyhedral validators passed)
     */
    private computeCoherence;
    /**
     * Get the cross-talk affinity between two domains.
     * Returns the edge weight if a direct edge exists, or the best route weight.
     */
    domainAffinity(domainA: AcademicDomain, domainB: AcademicDomain): number;
    /**
     * Compute the full 6×6 affinity matrix between all domains.
     */
    affinityMatrix(): number[][];
    /**
     * Identify which domains a query resonates with most strongly.
     * Returns sorted list of (domain, score) pairs.
     */
    domainResonance(input: string): Array<{
        domain: AcademicDomain;
        tongue: TongueCode;
        score: number;
    }>;
    /**
     * Get all edges in the cross-talk graph.
     */
    getEdges(): CrossTalkEdge[];
    /**
     * Get the kernel configuration.
     */
    getConfig(): CrossTalkKernelConfig;
}
/**
 * Create a cross-talk kernel with custom configuration.
 */
export declare function createCrossTalkKernel(config?: Partial<CrossTalkKernelConfig>): CrossTalkKernel;
/**
 * Default cross-talk kernel instance (POLLY mode, all validators active).
 */
export declare const defaultCrossTalkKernel: CrossTalkKernel;
//# sourceMappingURL=linguisticCrossTalk.d.ts.map