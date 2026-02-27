/**
 * SCBE Test Pad - Hyperbolic Containment Module
 *
 * Embeds test execution in a Poincare ball sandbox.
 * Applies H(d*) = exp(d*^2) risk scaling from harmonic_scaling_law.
 * Enforces Golden Ratio boundary (phi = 1.618) for governance denial.
 *
 * Layers 4-8 integration: Geometric Embedding, Hyperbolic Distance,
 * Harmonic Scaling, and Breath Transform.
 *
 * USPTO #63/961,403
 */

// ---------- Constants ----------

const PHI = 1.618033988749895;
const FORBIDDEN_PATTERNS = [
  /\brequire\s*\(\s*['"]child_process['"]\s*\)/,
  /\bexec\s*\(/,
  /\bexecSync\s*\(/,
  /\bspawn\s*\(/,
  /\bfs\s*\.\s*(?:unlink|rmdir|rm)Sync?\s*\(/,
  /\bprocess\s*\.\s*exit\s*\(/,
  /\beval\s*\(/,
  /\bnew\s+Function\s*\(/,
  /\brequire\s*\(\s*['"]net['"]\s*\)/,
  /\brequire\s*\(\s*['"]dgram['"]\s*\)/,
  /\brequire\s*\(\s*['"]cluster['"]\s*\)/,
];

// ---------- Types ----------

export interface ContainmentResult {
  allowed: boolean;
  distance: number;
  riskScore: number;
  violations: string[];
  auditLog: string;
  breathFactor: number;
}

export interface CodeVector {
  complexity: number;    // 0-1 normalized code complexity
  depth: number;         // nesting depth / layer count
  ioWeight: number;      // file/network I/O intensity
  cryptoWeight: number;  // crypto operation intensity
  processWeight: number; // process spawning intensity
  dynamicWeight: number; // dynamic eval / code gen intensity
}

// ---------- Core Functions ----------

/**
 * Analyze code and produce a 6D feature vector.
 */
export function analyzeCodeVector(code: string): CodeVector {
  const lines = code.split('\n').length;
  const chars = code.length;

  // Complexity: normalized by code size
  const complexity = Math.min(1.0, chars / 10000);

  // Depth: count nesting indicators
  const braceCount = (code.match(/\{/g) || []).length;
  const depth = Math.min(1.0, braceCount / 50);

  // I/O weight: file system and network references
  const ioMatches = (code.match(/\b(fs|http|https|net|dgram|fetch|axios|request)\b/g) || []).length;
  const ioWeight = Math.min(1.0, ioMatches / 10);

  // Crypto weight: crypto operations
  const cryptoMatches = (code.match(/\b(crypto|cipher|hash|encrypt|decrypt|sign|verify|hmac)\b/gi) || []).length;
  const cryptoWeight = Math.min(1.0, cryptoMatches / 8);

  // Process weight: spawning / exec
  const processMatches = (code.match(/\b(spawn|exec|fork|child_process|cluster)\b/g) || []).length;
  const processWeight = Math.min(1.0, processMatches / 5);

  // Dynamic weight: eval / Function / vm
  const dynamicMatches = (code.match(/\b(eval|Function|vm\.run|vm\.Script)\b/g) || []).length;
  const dynamicWeight = Math.min(1.0, dynamicMatches / 3);

  return { complexity, depth, ioWeight, cryptoWeight, processWeight, dynamicWeight };
}

/**
 * Compute hyperbolic distance from origin in the Poincare ball.
 * d(0, x) = 2 * arctanh(|x|) where |x| is the Euclidean norm.
 */
export function hyperbolicDistance(vector: CodeVector): number {
  const coords = [
    vector.complexity,
    vector.depth,
    vector.ioWeight,
    vector.cryptoWeight,
    vector.processWeight,
    vector.dynamicWeight,
  ];

  // Euclidean norm (clamped to <1 for Poincare ball)
  const norm = Math.sqrt(coords.reduce((s, c) => s + c * c, 0));
  const clampedNorm = Math.min(norm, 0.999);

  // Hyperbolic distance from origin
  return 2 * Math.atanh(clampedNorm);
}

/**
 * Harmonic wall scaling: H(d*) = exp(d*^2)
 * Amplifies risk superexponentially with depth.
 */
export function harmonicWallScaling(dStar: number): number {
  return Math.exp(dStar * dStar);
}

/**
 * Breathing transform: dynamically expand/contract the sandbox tolerance.
 * Lower breath factor = tighter containment.
 */
export function breathingTransform(riskScore: number): number {
  // Sigmoid-based breath: high risk -> contracted (low factor)
  return 1.0 / (1.0 + Math.exp(2.0 * (riskScore - 3.0)));
}

/**
 * Scan code for forbidden patterns (RU policy check).
 */
export function scanForViolations(code: string): string[] {
  const violations: string[] = [];

  for (const pattern of FORBIDDEN_PATTERNS) {
    if (pattern.test(code)) {
      violations.push(`Forbidden pattern detected: ${pattern.source}`);
    }
  }

  return violations;
}

/**
 * Full containment check: embed code in Poincare ball, compute risk,
 * apply governance, return allow/deny decision.
 */
export function checkContainment(code: string, intent: 'run' | 'test' | 'install'): ContainmentResult {
  // Layer 1-3: Analyze input
  const vector = analyzeCodeVector(code);

  // Layer 4-5: Poincare ball embedding
  const distance = hyperbolicDistance(vector);

  // Layer 6: Harmonic wall scaling
  const riskScore = harmonicWallScaling(distance);

  // Layer 7: Breathing transform
  const breathFactor = breathingTransform(riskScore);

  // RU policy scan
  const violations = scanForViolations(code);

  // Intent multiplier: "test" is safer than "run"
  const intentMultiplier = intent === 'test' ? 0.8 : intent === 'install' ? 1.2 : 1.0;
  const adjustedDistance = distance * intentMultiplier;

  // Golden Ratio boundary check
  const allowed = adjustedDistance < PHI && violations.length === 0;

  const auditLog = [
    `[CONTAINMENT] Intent: ${intent}`,
    `  Vector: complexity=${vector.complexity.toFixed(3)}, depth=${vector.depth.toFixed(3)}, io=${vector.ioWeight.toFixed(3)}`,
    `  Hyperbolic distance: ${distance.toFixed(4)}`,
    `  Adjusted distance: ${adjustedDistance.toFixed(4)} (intent multiplier: ${intentMultiplier})`,
    `  Risk score H(d*): ${riskScore.toFixed(4)}`,
    `  Breath factor: ${breathFactor.toFixed(4)}`,
    `  Violations: ${violations.length === 0 ? 'none' : violations.join('; ')}`,
    `  PHI boundary: ${PHI.toFixed(6)}`,
    `  Decision: ${allowed ? 'ALLOW' : 'DENY'}`,
  ].join('\n');

  return { allowed, distance: adjustedDistance, riskScore, violations, auditLog, breathFactor };
}
