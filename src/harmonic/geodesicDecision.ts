/**
 * @file geodesicDecision.ts
 * @module harmonic/geodesicDecision
 * @layer Layer 12, Layer 13
 *
 * GeodesicDecisionBundle — replaces the L12 scalar harmonic score.
 *
 * Current L12 output: H(d,pd) ∈ (0,1] — one number, one threshold.
 * This output: a full geometric object in the Poincaré disk.
 *
 * Every AI governance decision is now a point in hyperbolic space with:
 *   - coordinates in the Poincaré unit disk
 *   - hyperbolic distance to each of the four decision wells
 *   - the geodesic arc to each well (for visualization and auditing)
 *   - a probability distribution over decisions (softmax over -distances)
 *   - a confidence score (1 - entropy of the distribution)
 *
 * Why this matters:
 *   The scalar score tells you HOW safe. The geodesic bundle tells you
 *   WHERE you are, WHICH well you're converging toward, and WHETHER
 *   your trajectory is stable or contested. L13 reads the nearest well,
 *   not whether a number crossed an arbitrary threshold.
 *
 * Hyperbolic distance (Poincaré disk model):
 *   d_H(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 *
 * Geodesic arcs in the Poincaré disk are circular arcs orthogonal to
 * the unit circle (or straight lines through the origin).
 */

// ─── Decision wells ───────────────────────────────────────────────────────────

export type DecisionTier = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

export const DECISION_TIERS: DecisionTier[] = ['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY'];

/**
 * Fixed well positions in the Poincaré disk [x, y], ‖p‖ < 1.
 *
 * Layout rationale:
 *   ALLOW     near origin — safe behavior, low hyperbolic distance cost
 *   QUARANTINE mid-ring, x-axis — suspicious but recoverable
 *   ESCALATE  mid-ring, y-axis — high-risk, needs review
 *   DENY      near boundary — adversarial; exponential distance from safe
 *
 * The exponential metric near ‖p‖→1 means DENY is geometrically far from
 * everything else — reaching it from ALLOW requires enormous "drift energy".
 */
export const DECISION_WELLS: Record<DecisionTier, [number, number]> = {
  ALLOW: [0.05, 0.05],
  QUARANTINE: [0.45, 0.3],
  ESCALATE: [0.3, 0.55],
  DENY: [0.85, 0.1],
};

// ─── Geometry ─────────────────────────────────────────────────────────────────

/** Euclidean distance squared between two 2D points. */
function euclidSq(u: [number, number], v: [number, number]): number {
  const dx = u[0] - v[0];
  const dy = u[1] - v[1];
  return dx * dx + dy * dy;
}

/** Euclidean norm squared of a 2D vector. */
function normSq(p: [number, number]): number {
  return p[0] * p[0] + p[1] * p[1];
}

/**
 * Hyperbolic distance in the Poincaré disk.
 * d_H(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 *
 * Clamped to avoid arcosh(x < 1) domain error at coincident points.
 */
export function hyperbolicDistance(u: [number, number], v: [number, number]): number {
  const num = 2 * euclidSq(u, v);
  const denom = (1 - normSq(u)) * (1 - normSq(v));
  if (denom <= 0) return Infinity; // on or outside boundary
  const arg = 1 + num / denom;
  return Math.acosh(Math.max(1, arg));
}

/**
 * A geodesic arc in the Poincaré disk.
 *
 * Geodesics are circular arcs orthogonal to the unit circle.
 * Special case: if the arc passes through the origin, it is a straight line
 * (represented as arcCenter = null, radius = Infinity).
 */
export interface GeodesicArc {
  from: [number, number];
  to: [number, number];
  /** Arc center in Euclidean space. Null for straight-line geodesics. */
  arcCenter: [number, number] | null;
  /** Arc radius in Euclidean space. Infinity for straight-line geodesics. */
  arcRadius: number;
  /** Start angle (radians) for canvas arc drawing. */
  startAngle: number;
  /** End angle (radians) for canvas arc drawing. */
  endAngle: number;
  /** True if canvas arc should sweep counterclockwise. */
  counterclockwise: boolean;
  /** Hyperbolic length of this arc. */
  hyperbolicLength: number;
}

/**
 * Compute the geodesic arc from point p to point q in the Poincaré disk.
 *
 * Algorithm:
 *   The geodesic through p and q is the unique circle orthogonal to the
 *   unit circle passing through both points. Its center lies on the
 *   perpendicular bisector of the chord pq and satisfies the orthogonality
 *   condition |center|² = |center - p|² + 1 (tangency with unit circle).
 */
export function geodesicArc(p: [number, number], q: [number, number]): GeodesicArc {
  const hypLen = hyperbolicDistance(p, q);

  // If points are antipodal through origin, geodesic is a straight line
  const crossProduct = p[0] * q[1] - p[1] * q[0];
  if (Math.abs(crossProduct) < 1e-9) {
    // Collinear with origin — straight line geodesic
    const angle = Math.atan2(q[1] - p[1], q[0] - p[0]);
    return {
      from: p,
      to: q,
      arcCenter: null,
      arcRadius: Infinity,
      startAngle: angle,
      endAngle: angle,
      counterclockwise: false,
      hyperbolicLength: hypLen,
    };
  }

  // General case: find the Euclidean circle through p and q orthogonal to unit circle.
  // Center c satisfies: |c - p|² = |c|² - 1  and  |c - q|² = |c|² - 1
  // Subtracting: 2(q-p)·c = |q|² - |p|²
  // Let c = (cx, cy):
  //   2(qx-px)cx + 2(qy-py)cy = qx²+qy² - px²-py²
  // Combined with the perpendicular bisector equation gives a 2x2 system.
  const px = p[0],
    py = p[1],
    qx = q[0],
    qy = q[1];
  const a11 = 2 * (qx - px);
  const a12 = 2 * (qy - py);
  const b1 = qx * qx + qy * qy - px * px - py * py;
  // Second equation from orthogonality: |c|² - c·p*2 + |p|² = |c|² - 1
  //   → -2cx*px - 2cy*py = -1 - |p|²  →  2cx*px + 2cy*py = 1 + |p|²
  const a21 = 2 * px;
  const a22 = 2 * py;
  const b2 = 1 + px * px + py * py;

  const det = a11 * a22 - a12 * a21;
  if (Math.abs(det) < 1e-12) {
    // Degenerate — fall back to straight line
    const angle = Math.atan2(qy - py, qx - px);
    return {
      from: p,
      to: q,
      arcCenter: null,
      arcRadius: Infinity,
      startAngle: angle,
      endAngle: angle,
      counterclockwise: false,
      hyperbolicLength: hypLen,
    };
  }

  const cx = (b1 * a22 - b2 * a12) / det;
  const cy = (a11 * b2 - a21 * b1) / det;
  const center: [number, number] = [cx, cy];
  const radius = Math.sqrt((cx - px) * (cx - px) + (cy - py) * (cy - py));

  const startAngle = Math.atan2(py - cy, px - cx);
  const endAngle = Math.atan2(qy - cy, qx - cx);

  // Determine sweep direction: use the cross product sign
  const ccw = crossProduct > 0;

  return {
    from: p,
    to: q,
    arcCenter: center,
    arcRadius: radius,
    startAngle,
    endAngle,
    counterclockwise: ccw,
    hyperbolicLength: hypLen,
  };
}

// ─── Decision bundle ──────────────────────────────────────────────────────────

export interface GeodesicDecisionBundle {
  /** Schema version for audit receipts. */
  schema_version: 'scbe.geodesic_decision.v1';
  /** Position of the context point in the Poincaré disk. */
  manifoldPosition: [number, number];
  /** Hyperbolic distance from this point to each decision well. */
  distancesToWells: Record<DecisionTier, number>;
  /** Geodesic arc from this point to each decision well. */
  geodesics: Record<DecisionTier, GeodesicArc>;
  /** Probability of each decision: softmax over negative hyperbolic distances. */
  probabilities: Record<DecisionTier, number>;
  /** The decision tier with the highest probability (nearest well). */
  decision: DecisionTier;
  /**
   * Confidence in the decision: 1 - normalized entropy of the distribution.
   * 1.0 = certain, 0.0 = completely contested between all four wells.
   */
  confidence: number;
  /**
   * Whether the context point is in "contested territory" — two or more wells
   * are close in probability. This flags decisions that warrant human review
   * regardless of the winning tier.
   */
  contested: boolean;
}

function softmax(values: number[]): number[] {
  const max = Math.max(...values);
  const exps = values.map((v) => Math.exp(v - max));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map((v) => v / sum);
}

function entropy(probs: number[]): number {
  return -probs.reduce((acc, p) => {
    if (p <= 0) return acc;
    return acc + p * Math.log2(p);
  }, 0);
}

/**
 * Compute the full geodesic decision bundle for a context point in the disk.
 *
 * @param position - [x, y] coordinates in the Poincaré disk (‖p‖ < 1)
 * @param temperature - softmax temperature; lower = sharper decisions (default 1.0)
 */
export function computeGeodesicDecision(
  position: [number, number],
  temperature = 1.0
): GeodesicDecisionBundle {
  // Clamp position inside unit disk
  const mag = Math.sqrt(normSq(position));
  const safePos: [number, number] =
    mag >= 1.0 ? [(position[0] * 0.99) / mag, (position[1] * 0.99) / mag] : position;

  // Hyperbolic distances to all four wells
  const distances = {} as Record<DecisionTier, number>;
  const arcs = {} as Record<DecisionTier, GeodesicArc>;
  for (const tier of DECISION_TIERS) {
    distances[tier] = hyperbolicDistance(safePos, DECISION_WELLS[tier]);
    arcs[tier] = geodesicArc(safePos, DECISION_WELLS[tier]);
  }

  // Softmax over negative distances (closer well = higher probability)
  const distValues = DECISION_TIERS.map((t) => -distances[t] / temperature);
  const probs = softmax(distValues);
  const probMap = {} as Record<DecisionTier, number>;
  DECISION_TIERS.forEach((t, i) => {
    probMap[t] = probs[i];
  });

  // Winning decision
  const decision = DECISION_TIERS.reduce(
    (best, t) => (probMap[t] > probMap[best] ? t : best),
    DECISION_TIERS[0]
  );

  // Confidence: 1 - normalized entropy
  const maxEntropy = Math.log2(DECISION_TIERS.length); // log2(4) = 2
  const conf = 1.0 - entropy(probs) / maxEntropy;

  // Contested: top two probabilities within 0.15 of each other
  const sorted = [...probs].sort((a, b) => b - a);
  const contested = sorted[0] - sorted[1] < 0.15;

  return {
    schema_version: 'scbe.geodesic_decision.v1',
    manifoldPosition: safePos,
    distancesToWells: distances,
    geodesics: arcs,
    probabilities: probMap,
    decision,
    confidence: conf,
    contested,
  };
}

// ─── Pipeline integration helpers ────────────────────────────────────────────

/**
 * Map a harmonic wall score H ∈ (0,1] and hyperbolic distance d_H to a
 * position in the Poincaré disk, then compute the full geodesic bundle.
 *
 * This bridges the existing L12 scalar output to the geodesic surface.
 * As the pipeline is upgraded to natively track manifold position, this
 * adapter becomes unnecessary.
 *
 * Mapping convention:
 *   H is a safety score — high H = safe = near ALLOW well.
 *   d_H is hyperbolic distance from safe — high d_H = adversarial = near DENY.
 *
 *   x = d_H_normalized * cos(π * (1 - H))
 *   y = d_H_normalized * sin(π * (1 - H))
 *   where d_H_normalized = tanh(d_H / 4) keeps the point inside the unit disk.
 */
export function harmonicScoreToGeodesicDecision(
  harmonicScore: number,
  hyperbolicDist: number,
  temperature = 1.0
): GeodesicDecisionBundle {
  const r = Math.tanh(hyperbolicDist / 4); // maps [0,∞) → [0,1)
  const angle = Math.PI * (1 - Math.max(0, Math.min(1, harmonicScore)));
  const x = r * Math.cos(angle);
  const y = r * Math.sin(angle);
  return computeGeodesicDecision([x, y], temperature);
}

/**
 * Serialize a GeodesicDecisionBundle to a compact audit receipt string.
 * Drops the geodesic arc geometry (too large for receipts) but retains
 * all decision-relevant data.
 */
export function toAuditReceipt(bundle: GeodesicDecisionBundle): Record<string, unknown> {
  return {
    schema_version: bundle.schema_version,
    manifold: {
      x: bundle.manifoldPosition[0].toFixed(4),
      y: bundle.manifoldPosition[1].toFixed(4),
    },
    distances: Object.fromEntries(
      DECISION_TIERS.map((t) => [t, bundle.distancesToWells[t].toFixed(4)])
    ),
    probabilities: Object.fromEntries(
      DECISION_TIERS.map((t) => [t, bundle.probabilities[t].toFixed(4)])
    ),
    decision: bundle.decision,
    confidence: bundle.confidence.toFixed(4),
    contested: bundle.contested,
  };
}
