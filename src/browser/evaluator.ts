/**
 * SCBE Browser Action Evaluator
 * ==============================
 *
 * Evaluates browser actions through the SCBE 14-layer governance pipeline.
 *
 * Pipeline flow:
 * 1. Action → Semantic encoding (Polyglot L1-2)
 * 2. Position encoding (Aethercode L4 Poincaré)
 * 3. Hyperbolic distance metrics (L5)
 * 4. Harmonic scaling (L12)
 * 5. Risk decision (L13 with Hive Memory)
 * 6. 4-tier decision: ALLOW / QUARANTINE / ESCALATE / DENY
 *
 * @module browser/evaluator
 * @layer Layers 1-14 (full pipeline)
 * @version 3.0.0
 */

import { randomUUID } from 'crypto';
import { TongueCode, TONGUE_CODES } from '../tokenizer/ss1.js';
import {
  BrowserAction,
  BrowserObservation,
  BrowserDecision,
  GovernanceResult,
  ACTION_SENSITIVITY,
  DOMAIN_RISK,
  DomainRiskCategory,
  describeAction,
  isNavigateAction,
  isTypeAction,
  isExecuteScriptAction,
} from './types.js';
import {
  layer1ComplexState,
  layer2Realification,
  layer3WeightedTransform,
  layer4PoincareEmbedding,
  layer5HyperbolicDistance,
  layer12HarmonicScaling,
} from '../harmonic/pipeline14.js';

// =============================================================================
// CONSTANTS
// =============================================================================

const PHI = 1.618033988749895;

/** Governance thresholds */
const THRESHOLDS = {
  /** Below this: ALLOW */
  allow: 0.3,
  /** Below this: QUARANTINE (with monitoring) */
  quarantine: 0.6,
  /** Below this: ESCALATE (needs human/AI review) */
  escalate: 0.85,
  /** Above this: DENY */
  deny: 0.85,
};

/** Tier requirements for actions */
const TIER_REQUIREMENTS: Record<string, TongueCode> = {
  navigate: 'KO',
  scroll: 'KO',
  hover: 'KO',
  wait: 'KO',
  screenshot: 'KO',
  go_back: 'KO',
  go_forward: 'KO',
  click: 'AV',
  select: 'AV',
  press: 'AV',
  dialog_dismiss: 'AV',
  refresh: 'AV',
  type: 'RU',
  dialog_accept: 'RU',
  download: 'CA',
  clear_cookies: 'CA',
  set_cookie: 'UM',
  upload: 'UM',
  execute_script: 'DR',
};

/** Domain patterns for risk classification */
const DOMAIN_PATTERNS: [RegExp, DomainRiskCategory][] = [
  [/bank|chase|wellsfargo|citi|bofa|capital.*one/i, 'banking'],
  [/paypal|stripe|venmo|finance|invest|trading|stock/i, 'financial'],
  [/health|medical|doctor|hospital|pharmacy|epic.*care/i, 'healthcare'],
  [/\.gov$|government|irs|ssa\.gov/i, 'government'],
  [/amazon|ebay|walmart|target|shop|store|cart|checkout/i, 'shopping'],
  [/facebook|twitter|instagram|tiktok|linkedin|social/i, 'social_media'],
  [/news|cnn|bbc|nytimes|reuters|wsj/i, 'news'],
  [/google|bing|duckduckgo|search/i, 'search'],
];

// =============================================================================
// ACTION ENCODER (Layers 1-2)
// =============================================================================

/**
 * Encode a browser action into the semantic space using Polyglot encoding.
 *
 * This implements Layers 1-2:
 * - Layer 1: Complex state (amplitude = sensitivity, phase = action type)
 * - Layer 2: Realification to ℝ^{2D}
 */
function encodeActionSemantic(
  action: BrowserAction,
  observation: BrowserObservation
): { complex: { real: number[]; imag: number[] }; realified: number[] } {
  // Map action type to 6D tongue space
  // Each action type activates certain tongues
  const tongueActivation = getTongueActivation(action);

  // Get base sensitivity
  const sensitivity = ACTION_SENSITIVITY[action.type];

  // Compute amplitudes (how much each tongue is activated)
  const amplitudes = TONGUE_CODES.map((tongue) => {
    const baseActivation = tongueActivation[tongue] ?? 0;
    return baseActivation * sensitivity;
  });

  // Compute phases based on action characteristics
  const phases = computeActionPhases(action, observation);

  // Layer 1: Complex state
  const t = [...amplitudes, ...phases];
  const complex = layer1ComplexState(t, 6);

  // Layer 2: Realification
  const realified = layer2Realification(complex);

  return { complex, realified };
}

/**
 * Map action type to tongue activation levels.
 */
function getTongueActivation(action: BrowserAction): Record<TongueCode, number> {
  // Base activations per action type
  const activations: Record<string, Record<TongueCode, number>> = {
    navigate: { KO: 0.8, AV: 0.4, RU: 0.2, CA: 0.3, UM: 0.1, DR: 0.1 },
    click: { KO: 0.6, AV: 0.8, RU: 0.3, CA: 0.2, UM: 0.2, DR: 0.1 },
    type: { KO: 0.4, AV: 0.3, RU: 0.8, CA: 0.2, UM: 0.4, DR: 0.2 },
    scroll: { KO: 0.3, AV: 0.6, RU: 0.1, CA: 0.1, UM: 0.1, DR: 0.0 },
    select: { KO: 0.4, AV: 0.7, RU: 0.5, CA: 0.2, UM: 0.2, DR: 0.1 },
    hover: { KO: 0.2, AV: 0.5, RU: 0.1, CA: 0.1, UM: 0.1, DR: 0.0 },
    press: { KO: 0.5, AV: 0.6, RU: 0.4, CA: 0.2, UM: 0.2, DR: 0.1 },
    screenshot: { KO: 0.3, AV: 0.2, RU: 0.2, CA: 0.1, UM: 0.3, DR: 0.1 },
    wait: { KO: 0.1, AV: 0.2, RU: 0.1, CA: 0.5, UM: 0.1, DR: 0.0 },
    execute_script: { KO: 0.7, AV: 0.5, RU: 0.8, CA: 0.6, UM: 0.8, DR: 0.9 },
    download: { KO: 0.5, AV: 0.3, RU: 0.4, CA: 0.6, UM: 0.5, DR: 0.4 },
    upload: { KO: 0.5, AV: 0.4, RU: 0.5, CA: 0.6, UM: 0.7, DR: 0.5 },
    set_cookie: { KO: 0.4, AV: 0.3, RU: 0.5, CA: 0.4, UM: 0.7, DR: 0.3 },
    clear_cookies: { KO: 0.3, AV: 0.3, RU: 0.4, CA: 0.4, UM: 0.5, DR: 0.3 },
    dialog_accept: { KO: 0.6, AV: 0.5, RU: 0.4, CA: 0.3, UM: 0.4, DR: 0.2 },
    dialog_dismiss: { KO: 0.4, AV: 0.5, RU: 0.3, CA: 0.2, UM: 0.2, DR: 0.1 },
    go_back: { KO: 0.5, AV: 0.4, RU: 0.1, CA: 0.2, UM: 0.1, DR: 0.1 },
    go_forward: { KO: 0.5, AV: 0.4, RU: 0.1, CA: 0.2, UM: 0.1, DR: 0.1 },
    refresh: { KO: 0.4, AV: 0.3, RU: 0.2, CA: 0.3, UM: 0.2, DR: 0.1 },
  };

  return activations[action.type] ?? { KO: 0.5, AV: 0.5, RU: 0.5, CA: 0.5, UM: 0.5, DR: 0.5 };
}

/**
 * Compute phase angles based on action characteristics.
 */
function computeActionPhases(action: BrowserAction, observation: BrowserObservation): number[] {
  const phases: number[] = [];

  // Base phases evenly distributed
  for (let i = 0; i < 6; i++) {
    const base = (i * Math.PI) / 3; // 60° apart

    // Modulate based on context
    let modulation = 0;

    // Action-specific modulation
    if (isNavigateAction(action)) {
      modulation = (action.url.length % 360) * (Math.PI / 180);
    } else if (isTypeAction(action)) {
      modulation = action.sensitive ? Math.PI / 4 : 0;
    } else if (isExecuteScriptAction(action)) {
      modulation = Math.PI / 2; // High phase shift for scripts
    }

    // URL context modulation
    if (observation.page.url) {
      const urlHash = hashString(observation.page.url);
      modulation += (urlHash % 60) * (Math.PI / 180);
    }

    phases.push((base + modulation) % (2 * Math.PI));
  }

  return phases;
}

// =============================================================================
// POSITION ENCODING (Layer 4)
// =============================================================================

/**
 * Encode session state into Poincaré ball position.
 *
 * This represents the agent's "location" in governance space.
 */
function encodeSessionPosition(
  sessionRisk: number,
  actionCount: number,
  errorCount: number,
  domainRisk: number
): number[] {
  // Create 6D position from session state
  const position = [
    sessionRisk, // AXIOM: accumulated risk
    actionCount / 100, // FLOW: normalized action count
    errorCount / 10, // GLYPH: normalized error count
    domainRisk, // ORACLE: current domain risk
    1 - sessionRisk, // CHARM: inverted risk (harmony)
    Math.min(actionCount / 50, 1), // LEDGER: session maturity
  ];

  // Apply Layer 3 weighting
  const weighted = layer3WeightedTransform(position);

  // Apply Layer 4 Poincaré embedding
  return layer4PoincareEmbedding(weighted, 1.0, 0.01);
}

// =============================================================================
// RISK COMPUTATION
// =============================================================================

/**
 * Classify domain from URL.
 */
function classifyDomain(url: string): DomainRiskCategory {
  for (const [pattern, category] of DOMAIN_PATTERNS) {
    if (pattern.test(url)) {
      return category;
    }
  }
  return 'unknown';
}

/**
 * Compute combined risk score using 14-layer pipeline.
 */
function computeRiskScore(
  action: BrowserAction,
  observation: BrowserObservation,
  sessionState: { sessionRisk: number; actionCount: number; errorCount: number }
): {
  score: number;
  factors: GovernanceResult['riskFactors'];
  pipelineOutputs: Record<string, unknown>;
} {
  // Get base action risk
  const actionRisk = ACTION_SENSITIVITY[action.type];

  // Get domain risk
  const domainCategory = classifyDomain(observation.page.url);
  const domainRisk = DOMAIN_RISK[domainCategory];

  // Encode action semantically (L1-L2)
  const { realified } = encodeActionSemantic(action, observation);

  // Encode session position (L3-L4)
  const sessionPosition = encodeSessionPosition(
    sessionState.sessionRisk,
    sessionState.actionCount,
    sessionState.errorCount,
    domainRisk
  );

  // Safe origin position (center of Poincaré ball)
  const safeOrigin = new Array(sessionPosition.length).fill(0);

  // Compute hyperbolic distance from safe state (L5)
  const hyperbolicDist = layer5HyperbolicDistance(sessionPosition, safeOrigin);

  // Apply harmonic scaling (L12)
  // H(d) = φ^d where d is hyperbolic distance
  const harmonicFactor = layer12HarmonicScaling(hyperbolicDist);

  // Compute temporal risk (based on action frequency)
  const temporalRisk = Math.min(sessionState.actionCount / 100, 1) * 0.3;

  // Compute historical risk (session accumulator)
  const historicalRisk = sessionState.sessionRisk;

  // Combined risk with L12 harmonic amplification
  const baseRisk = actionRisk * 0.35 + domainRisk * 0.25 + temporalRisk * 0.2 + historicalRisk * 0.2;

  // Apply harmonic scaling (makes risk grow super-exponentially near boundary)
  const amplifiedRisk = Math.min(baseRisk * harmonicFactor, 1.0);

  return {
    score: amplifiedRisk,
    factors: {
      actionRisk,
      domainRisk,
      sessionRisk: sessionState.sessionRisk,
      temporalRisk,
      historicalRisk,
    },
    pipelineOutputs: {
      semanticEncoding: realified,
      sessionPosition,
      hyperbolicDistance: hyperbolicDist,
      harmonicFactor,
      baseRisk,
      amplifiedRisk,
    },
  };
}

// =============================================================================
// DECISION LOGIC
// =============================================================================

/**
 * Make governance decision based on risk score.
 */
function makeDecision(riskScore: number, action: BrowserAction): {
  decision: BrowserDecision;
  confidence: number;
  requiresRoundtable: boolean;
} {
  // Check if action inherently requires Roundtable
  const isHighRiskAction =
    action.type === 'execute_script' || action.type === 'upload' || action.type === 'set_cookie';

  // Determine decision
  let decision: BrowserDecision;
  let confidence: number;

  if (riskScore < THRESHOLDS.allow) {
    decision = 'ALLOW';
    confidence = 1 - riskScore / THRESHOLDS.allow;
  } else if (riskScore < THRESHOLDS.quarantine) {
    decision = 'QUARANTINE';
    confidence = (riskScore - THRESHOLDS.allow) / (THRESHOLDS.quarantine - THRESHOLDS.allow);
  } else if (riskScore < THRESHOLDS.escalate) {
    decision = 'ESCALATE';
    confidence = (riskScore - THRESHOLDS.quarantine) / (THRESHOLDS.escalate - THRESHOLDS.quarantine);
  } else {
    decision = 'DENY';
    confidence = Math.min((riskScore - THRESHOLDS.deny) / (1 - THRESHOLDS.deny), 1);
  }

  // High-risk actions always require Roundtable unless ALLOW
  const requiresRoundtable = isHighRiskAction && decision !== 'DENY';

  return { decision, confidence, requiresRoundtable };
}

/**
 * Generate human-readable explanation.
 */
function generateExplanation(
  action: BrowserAction,
  observation: BrowserObservation,
  riskFactors: GovernanceResult['riskFactors'],
  decision: BrowserDecision
): string {
  const actionDesc = describeAction(action);
  const domain = classifyDomain(observation.page.url);
  const domainDesc = domain === 'unknown' ? 'unknown domain' : `${domain} domain`;

  const factors: string[] = [];

  if (riskFactors.actionRisk >= 0.7) {
    factors.push(`high-risk action type (${riskFactors.actionRisk.toFixed(2)})`);
  }
  if (riskFactors.domainRisk >= 0.7) {
    factors.push(`sensitive ${domainDesc} (${riskFactors.domainRisk.toFixed(2)})`);
  }
  if (riskFactors.sessionRisk >= 0.5) {
    factors.push(`elevated session risk (${riskFactors.sessionRisk.toFixed(2)})`);
  }
  if (riskFactors.temporalRisk >= 0.3) {
    factors.push(`rapid action sequence (${riskFactors.temporalRisk.toFixed(2)})`);
  }

  let explanation = `${decision}: "${actionDesc}" on ${domainDesc}`;

  if (factors.length > 0) {
    explanation += `. Risk factors: ${factors.join(', ')}`;
  }

  return explanation;
}

// =============================================================================
// MAIN EVALUATOR
// =============================================================================

export interface EvaluatorOptions {
  /** Override thresholds */
  thresholds?: Partial<typeof THRESHOLDS>;
  /** Enable debug pipeline outputs */
  debug?: boolean;
}

/**
 * SCBE Browser Action Evaluator.
 *
 * Processes browser actions through the 14-layer governance pipeline.
 */
export class BrowserActionEvaluator {
  private thresholds: typeof THRESHOLDS;
  private debug: boolean;

  constructor(options: EvaluatorOptions = {}) {
    this.thresholds = { ...THRESHOLDS, ...options.thresholds };
    this.debug = options.debug ?? false;
  }

  /**
   * Evaluate a browser action through the SCBE pipeline.
   *
   * @param action - The action to evaluate
   * @param observation - Current browser observation
   * @param sessionState - Current session state
   * @returns Governance result with decision
   */
  evaluate(
    action: BrowserAction,
    observation: BrowserObservation,
    sessionState: {
      sessionRisk: number;
      actionCount: number;
      errorCount: number;
    }
  ): GovernanceResult {
    const decisionId = randomUUID();

    // Compute risk through pipeline
    const { score: riskScore, factors: riskFactors, pipelineOutputs } = computeRiskScore(
      action,
      observation,
      sessionState
    );

    // Make decision
    const { decision, confidence, requiresRoundtable } = makeDecision(riskScore, action);

    // Get required tier
    const requiredTier = TIER_REQUIREMENTS[action.type] ?? 'RU';

    // Generate explanation
    const explanation = generateExplanation(action, observation, riskFactors, decision);

    // Generate token for allowed/quarantined actions
    let token: string | undefined;
    let expiresAt: number | undefined;

    if (decision === 'ALLOW' || decision === 'QUARANTINE') {
      token = this.generateToken(decisionId, action);
      expiresAt = Date.now() + 5 * 60 * 1000; // 5 minute expiry
    }

    return {
      decision,
      decisionId,
      riskScore,
      confidence,
      riskFactors,
      explanation,
      requiredTier,
      requiresRoundtable,
      token,
      expiresAt,
      pipelineOutputs: this.debug ? pipelineOutputs : undefined,
    };
  }

  /**
   * Batch evaluate multiple actions.
   */
  evaluateBatch(
    actions: BrowserAction[],
    observation: BrowserObservation,
    sessionState: { sessionRisk: number; actionCount: number; errorCount: number }
  ): GovernanceResult[] {
    return actions.map((action) => this.evaluate(action, observation, sessionState));
  }

  /**
   * Check if a token is valid.
   */
  validateToken(token: string, decisionId: string, action: BrowserAction): boolean {
    const expected = this.generateToken(decisionId, action);
    return token === expected;
  }

  /**
   * Generate execution token for allowed actions.
   */
  private generateToken(decisionId: string, action: BrowserAction): string {
    const content = `${decisionId}:${action.type}:${JSON.stringify(action)}`;
    return hashString(content).toString(16).padStart(16, '0');
  }
}

// =============================================================================
// UTILITIES
// =============================================================================

/**
 * Simple string hash function.
 */
function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
}

// =============================================================================
// EXPORTS
// =============================================================================

export { computeRiskScore, classifyDomain, encodeActionSemantic, encodeSessionPosition };
