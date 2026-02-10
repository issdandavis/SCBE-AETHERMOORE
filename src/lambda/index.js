/**
 * @file index.js
 * @module lambda/scbe-gateway
 * @version 3.2.4
 *
 * SCBE-AETHERMOORE Lambda Gateway — DualLatticeStack v2
 * Zero dependencies — AWS Lambda ready
 *
 * Integrates:
 *   Seam 1: Manifold-Gated Dual-Lane Classifier (original)
 *   Seam 2: Trajectory + Drift Coherence Kernel (original)
 *   Seam 3: HyperbolicRAG Trust Scoring (NEW — GeoSeal v2)
 *   Seam 4: Entropic Layer — escape detection, adaptive k, time dilation (NEW)
 *   Seam 5: CHSFN Quasi-Sphere — tongue impedance + phase coherence (NEW)
 *
 * Stack: Quasicrystal × Hyperbolic × GeoSeal
 */

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

const PHI = 1.618033988749895;
const EPSILON = 1e-10;
const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'DR', 'UM'];

// ═══════════════════════════════════════════════════════════════
// SEAM 1: Manifold-Gated Dual-Lane Classifier (original)
// ═══════════════════════════════════════════════════════════════

const ManifoldClassifier = {
  LANE_THRESHOLD: 0.5,

  extractGeometry(context) {
    const entropy = this.shannonEntropy(JSON.stringify(context));
    const complexity = context.payload?.length || 0;
    const depth = this.objectDepth(context);
    return { entropy, complexity, depth };
  },

  shannonEntropy(str) {
    const freq = {};
    for (const c of str) freq[c] = (freq[c] || 0) + 1;
    const len = str.length;
    return -Object.values(freq).reduce((h, f) => {
      const p = f / len;
      return h + p * Math.log2(p);
    }, 0);
  },

  objectDepth(obj, d = 0) {
    if (typeof obj !== 'object' || obj === null) return d;
    return Math.max(...Object.values(obj).map((v) => this.objectDepth(v, d + 1)), d);
  },

  computeLaneBit(geometry) {
    const { entropy, complexity, depth } = geometry;
    const r = Math.sqrt(entropy * entropy + (complexity / 100) ** 2);
    const theta = Math.atan2(depth, entropy) * PHI;
    const projection = (Math.sin(theta) * r) / (1 + Math.abs(Math.cos(theta * PHI)));
    const normalized = (Math.tanh(projection) + 1) / 2;
    return { laneBit: normalized >= this.LANE_THRESHOLD ? 1 : 0, confidence: normalized };
  },

  classify(context) {
    const geometry = this.extractGeometry(context);
    const { laneBit, confidence } = this.computeLaneBit(geometry);
    return {
      lane: laneBit === 0 ? 'brain' : 'oversight',
      laneBit,
      confidence: Math.round(confidence * 1000) / 1000,
      geometry,
    };
  },
};

// ═══════════════════════════════════════════════════════════════
// SEAM 2: Trajectory + Drift Coherence Kernel (original)
// ═══════════════════════════════════════════════════════════════

const TrajectoryKernel = {
  COHERENCE_THRESHOLD: 0.7,
  DRIFT_TOLERANCE: 0.15,

  computeKernel(request) {
    const now = Date.now();
    return {
      origin: this.hashOrigin(request.sourceId || 'anonymous'),
      velocity: this.computeVelocity(request.timestamp || now, now),
      curvature: this.computeCurvature(request.history || []),
      phase: this.computePhase(now),
      signature: this.computeSignature(request),
    };
  },

  hashOrigin(sourceId) {
    let hash = 0;
    for (let i = 0; i < sourceId.length; i++) {
      hash = (hash << 5) - hash + sourceId.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(Math.sin(hash));
  },

  computeVelocity(reqTime, now) {
    const delta = Math.max(1, now - reqTime);
    return Math.min(1, 1000 / delta);
  },

  computeCurvature(history) {
    if (history.length < 3) return 0.5;
    const diffs = [], diffs2 = [];
    for (let i = 1; i < history.length; i++) diffs.push(history[i] - history[i - 1]);
    for (let i = 1; i < diffs.length; i++) diffs2.push(diffs[i] - diffs[i - 1]);
    const avgCurve = diffs2.reduce((a, b) => a + b, 0) / diffs2.length;
    return Math.tanh(avgCurve / 100) * 0.5 + 0.5;
  },

  computePhase(now) { return (now % 60000) / 60000; },

  computeSignature(request) {
    const payload = JSON.stringify(request.payload || {});
    let sig = 0;
    for (let i = 0; i < payload.length; i++) sig = (sig * 31 + payload.charCodeAt(i)) & 0xffffffff;
    return (sig >>> 0) / 0xffffffff;
  },

  computeCoherence(kernel) {
    const vars = [kernel.origin, kernel.velocity, kernel.curvature, kernel.phase, kernel.signature];
    const mean = vars.reduce((a, b) => a + b, 0) / vars.length;
    const variance = vars.reduce((a, v) => a + (v - mean) ** 2, 0) / vars.length;
    return 1 - Math.sqrt(variance);
  },

  computeDrift(kernel, expectedPhase = 0.5) {
    return (Math.abs(kernel.phase - expectedPhase) + Math.abs(kernel.velocity - 0.5)) / 2;
  },

  verify(request) {
    const kernel = this.computeKernel(request);
    const coherence = this.computeCoherence(kernel);
    const drift = this.computeDrift(kernel);
    const authorized = coherence >= this.COHERENCE_THRESHOLD && drift <= this.DRIFT_TOLERANCE;
    return {
      authorized, kernel,
      coherence: Math.round(coherence * 1000) / 1000,
      drift: Math.round(drift * 1000) / 1000,
      thresholds: { coherence: this.COHERENCE_THRESHOLD, drift: this.DRIFT_TOLERANCE },
    };
  },
};

// ═══════════════════════════════════════════════════════════════
// SEAM 3: HyperbolicRAG Trust Scoring (GeoSeal v2)
// ═══════════════════════════════════════════════════════════════

const HyperbolicRAG = {
  /** Tongue anchor positions in the Poincaré ball */
  ANCHORS: {
    KO: [0.5, 0, 0, 0, 0, 0],
    AV: [0, 0.5, 0, 0, 0, 0],
    RU: [0, 0, 0.5, 0, 0, 0],
    CA: [0, 0, 0, 0.5, 0, 0],
    DR: [0, 0, 0, 0, 0.5, 0],
    UM: [0, 0, 0, 0, 0, 0.5],
  },

  /** Project arbitrary vector into 6D Poincaré ball via tanh mapping */
  projectToBall(values, scale = 0.5) {
    const reduced = [0, 0, 0, 0, 0, 0];
    const chunkSize = Math.max(1, Math.floor(values.length / 6));
    for (let dim = 0; dim < 6; dim++) {
      const start = dim * chunkSize;
      const end = dim === 5 ? values.length : (dim + 1) * chunkSize;
      let sum = 0, count = 0;
      for (let j = start; j < end; j++) { sum += values[j]; count++; }
      reduced[dim] = count > 0 ? sum / count : 0;
    }
    let normSq = 0;
    for (let i = 0; i < 6; i++) normSq += reduced[i] * reduced[i];
    const norm = Math.sqrt(normSq);
    if (norm < EPSILON) return [0, 0, 0, 0, 0, 0];
    const mapped = Math.tanh(scale * norm);
    return reduced.map((v) => mapped * (v / norm));
  },

  /** Hyperbolic distance in 6D Poincaré ball */
  hyperbolicDist(u, v) {
    let diffSq = 0, uSq = 0, vSq = 0;
    for (let i = 0; i < 6; i++) {
      diffSq += (u[i] - v[i]) ** 2;
      uSq += u[i] * u[i];
      vSq += v[i] * v[i];
    }
    const denom = (1 - uSq) * (1 - vSq);
    if (denom <= 0) return Infinity;
    const arg = 1 + (2 * diffSq) / Math.max(denom, EPSILON);
    return Math.acosh(Math.max(arg, 1));
  },

  /** Access cost: H(d*, R) = R · π^(φ·d*) */
  accessCost(dStar, R = 1.5) {
    return R * Math.pow(Math.PI, PHI * dStar);
  },

  /** Proximity score: exponential decay via access cost */
  proximityScore(queryPos, chunkPos, maxDist = 3.0) {
    const dist = this.hyperbolicDist(queryPos, chunkPos);
    if (dist > maxDist) return 0;
    return this.accessCost(0) / this.accessCost(dist);
  },

  /** Phase coherence between two phase vectors */
  phaseCoherence(a, b) {
    let sum = 0;
    for (let i = 0; i < 6; i++) sum += Math.cos(a[i] - b[i]);
    return (sum / 6 + 1) / 2;
  },

  /** Nearest tongue anchor to a position */
  nearestAnchor(pos) {
    let best = 'KO', bestDist = Infinity;
    for (const tongue of TONGUE_NAMES) {
      const d = this.hyperbolicDist(pos, this.ANCHORS[tongue]);
      if (d < bestDist) { bestDist = d; best = tongue; }
    }
    return { tongue: best, distance: bestDist };
  },

  /** Score a retrieval chunk: 3-signal fusion */
  scoreChunk(queryPos, queryPhase, chunkPos, chunkPhase, uncertainty = 0.1) {
    const proxScore = this.proximityScore(queryPos, chunkPos);
    const phaseScore = this.phaseCoherence(chunkPhase, queryPhase);
    const uncPenalty = Math.min(Math.max(uncertainty, 0), 1);
    const { tongue, distance: anchorDist } = this.nearestAnchor(chunkPos);
    const raw = 0.5 * proxScore + 0.3 * phaseScore - 0.2 * uncPenalty;
    const trustScore = Math.max(0, Math.min(1, raw));
    const quarantine = trustScore < 0.3 || uncertainty > 0.7;
    return {
      trustScore: Math.round(trustScore * 1000) / 1000,
      anomalyProb: Math.round((1 - trustScore) * 1000) / 1000,
      quarantine,
      attentionWeight: quarantine ? 0 : Math.round(trustScore * trustScore * 1000) / 1000,
      signals: { proximity: Math.round(proxScore * 1000) / 1000,
                 phase: Math.round(phaseScore * 1000) / 1000,
                 uncertainty: Math.round(uncPenalty * 1000) / 1000,
                 nearestTongue: tongue, anchorDist: Math.round(anchorDist * 1000) / 1000 },
    };
  },

  /** Score a request body as a retrieval trust assessment */
  assess(body) {
    const payloadStr = JSON.stringify(body.payload || body);
    const values = [];
    for (let i = 0; i < payloadStr.length; i++) values.push((payloadStr.charCodeAt(i) - 128) / 128);
    const pos = this.projectToBall(values);
    const phase = [0, 1, 2, 3, 4, 5].map((i) => Math.atan2(
      values[(i * 2 + 1) % values.length] || 0,
      values[(i * 2) % values.length] || EPSILON
    ));
    const queryPos = body.queryEmbedding ? this.projectToBall(body.queryEmbedding) : [0, 0, 0, 0, 0, 0];
    const queryPhase = [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3];
    const variance = values.length > 0
      ? values.reduce((s, v) => s + v * v, 0) / values.length - (values.reduce((s, v) => s + v, 0) / values.length) ** 2
      : 1;
    const uncertainty = 1 / (1 + Math.exp(-10 * (Math.abs(variance) - 0.1)));
    return {
      position: pos.map((v) => Math.round(v * 10000) / 10000),
      phase: phase.map((v) => Math.round(v * 1000) / 1000),
      score: this.scoreChunk(queryPos, queryPhase, pos, phase, uncertainty),
      anchor: this.nearestAnchor(pos),
    };
  },
};

// ═══════════════════════════════════════════════════════════════
// SEAM 4: Entropic Layer — Escape, Adaptive k, Time Dilation
// ═══════════════════════════════════════════════════════════════

const EntropicLayer = {
  /** Position history for loop detection (in-memory, per-warm-start) */
  positionHistory: [],
  MAX_HISTORY: 100,

  /** Record a position and detect loops */
  recordAndDetect(position) {
    this.positionHistory.push(position);
    if (this.positionHistory.length > this.MAX_HISTORY) this.positionHistory.shift();

    const window = this.positionHistory.slice(-20);
    let loopCount = 0;
    for (let i = 0; i < window.length; i++) {
      for (let j = i + 2; j < window.length; j++) {
        const dist = HyperbolicRAG.hyperbolicDist(window[i], window[j]);
        if (1 / (1 + dist) > 0.95) loopCount++;
      }
    }

    const dilationFactor = Math.pow(PHI, Math.min(loopCount, 20));
    const hostile = loopCount >= 3;
    const entropy = this.positionEntropy(window);

    return { loopCount, dilationFactor, hostile, entropy: Math.round(entropy * 1000) / 1000 };
  },

  /** Shannon entropy of discretized positions */
  positionEntropy(positions) {
    if (positions.length < 2) return 1;
    const bins = {};
    for (const pos of positions) {
      const key = pos.map((v) => Math.min(9, Math.max(0, Math.floor(((v + 1) / 2) * 10)))).join(',');
      bins[key] = (bins[key] || 0) + 1;
    }
    const n = positions.length;
    let entropy = 0;
    for (const count of Object.values(bins)) {
      const p = count / n;
      if (p > 0) entropy -= p * Math.log2(p);
    }
    const maxEntropy = Math.log2(n);
    return maxEntropy > 0 ? entropy / maxEntropy : 0;
  },

  /** Escape detection: is position leaving trust basin? */
  detectEscape(position, coherence = 0.5) {
    const norm = Math.sqrt(position.reduce((s, v) => s + v * v, 0));
    const basinRadius = Math.min(-Math.log(1 - Math.min(coherence, 0.999)), 0.95);
    const basinFraction = basinRadius > 0 ? norm / basinRadius : 1;
    return {
      escaping: basinFraction > 0.8,
      norm: Math.round(norm * 10000) / 10000,
      basinRadius: Math.round(basinRadius * 10000) / 10000,
      basinFraction: Math.round(basinFraction * 1000) / 1000,
    };
  },

  /** Adaptive k: how many governance nodes to query */
  adaptiveK(position, minK = 2, maxK = 6) {
    const origin = [0, 0, 0, 0, 0, 0];
    const dist = HyperbolicRAG.hyperbolicDist(position, origin);
    const threat = 1 / (1 + Math.exp(-2 * (dist - 1.5)));
    const k = Math.max(minK, Math.min(maxK, Math.round(minK + (maxK - minK) * threat)));
    return { k, threat: Math.round(threat * 1000) / 1000 };
  },

  /** Full entropic assessment */
  assess(position, coherence = 0.5) {
    const escape = this.detectEscape(position, coherence);
    const loops = this.recordAndDetect(position);
    const { k, threat } = this.adaptiveK(position);

    let risk = 0.3 * (escape.escaping ? 0.8 : escape.basinFraction * 0.3)
             + 0.25 * (loops.hostile ? 0.9 : loops.loopCount * 0.15)
             + 0.25 * threat
             + 0.2 * (1 - loops.entropy);
    risk = Math.min(1, Math.max(0, risk));

    let recommendation;
    if (risk > 0.8 || loops.hostile) recommendation = 'DENY';
    else if (risk > 0.5 || escape.escaping) recommendation = 'QUARANTINE';
    else if (risk > 0.2) recommendation = 'SLOW';
    else recommendation = 'PROCEED';

    return {
      recommendation,
      risk: Math.round(risk * 1000) / 1000,
      adaptiveK: k,
      escape, loops, threat,
    };
  },
};

// ═══════════════════════════════════════════════════════════════
// SEAM 5: CHSFN Quasi-Sphere — tongue impedance + cymatic field
// ═══════════════════════════════════════════════════════════════

const CHSFN = {
  /** Compute 6D cymatic field value Φ(x) */
  cymaticField(x, n = [3, 5, 7, 4, 6, 2], m = [2, 4, 3, 5, 1, 6]) {
    let sum = 0;
    for (let i = 0; i < 6; i++) {
      const cosVal = Math.cos(Math.PI * n[i] * x[i]);
      let sinProd = 1;
      for (let j = 0; j < 6; j++) {
        if (j !== i) sinProd *= Math.sin(Math.PI * m[j] * x[j]);
      }
      sum += cosVal * sinProd;
    }
    return sum;
  },

  /** Check if position is near a cymatic zero-set (nodal surface) */
  isNearZeroSet(x, tol = 0.01) {
    return Math.abs(this.cymaticField(x)) < tol;
  },

  /** Tongue impedance at a position */
  tongueImpedance(phase, tongueIndex) {
    const expected = (2 * Math.PI * tongueIndex) / 6;
    const diff = Math.abs(phase[tongueIndex] - expected);
    return Math.min((diff % (2 * Math.PI)) / Math.PI, 1.0);
  },

  /** Is a node semantically accessible? */
  isAccessible(position, phase, tongueIndex, maxImpedance = 0.3, maxDist = 3.0) {
    const origin = [0, 0, 0, 0, 0, 0];
    const dist = HyperbolicRAG.hyperbolicDist(position, origin);
    if (dist > maxDist) return false;
    if (this.tongueImpedance(phase, tongueIndex) > maxImpedance) return false;
    return this.isNearZeroSet(position, 0.1);
  },

  /** Compute combined security cost for a state */
  securityCost(position, phase) {
    const origin = [0, 0, 0, 0, 0, 0];
    const dist = HyperbolicRAG.hyperbolicDist(position, origin);
    const distCost = HyperbolicRAG.accessCost(dist);
    let phaseCost = 1;
    for (let i = 0; i < 6; i++) phaseCost *= 1 + this.tongueImpedance(phase, i) * 10;
    const nodalCost = 1 + Math.abs(this.cymaticField(position)) * 100;
    return distCost * phaseCost * nodalCost;
  },

  /** Security bits equivalent */
  securityBits(position, phase) {
    return Math.round(Math.log2(Math.max(this.securityCost(position, phase), 1)) * 100) / 100;
  },

  /** Full CHSFN assessment */
  assess(position, phase) {
    const field = this.cymaticField(position);
    const nearZeroSet = Math.abs(field) < 0.01;
    const impedances = {};
    for (let i = 0; i < 6; i++) impedances[TONGUE_NAMES[i]] = Math.round(this.tongueImpedance(phase, i) * 1000) / 1000;
    return {
      field: Math.round(field * 10000) / 10000,
      nearZeroSet,
      impedances,
      securityBits: this.securityBits(position, phase),
      accessible: TONGUE_NAMES.map((t, i) => ({ tongue: t, accessible: this.isAccessible(position, phase, i) })),
    };
  },
};

// ═══════════════════════════════════════════════════════════════
// Lambda Handler — DualLatticeStack v2 API Gateway
// ═══════════════════════════════════════════════════════════════

exports.handler = async (event) => {
  const method = event.httpMethod || event.requestContext?.http?.method || 'GET';
  const path = event.path || event.rawPath || '/';
  const respond = (statusCode, body) => ({
    statusCode,
    headers: {
      'Content-Type': 'application/json',
      'X-SCBE-Version': '3.2.4',
      'X-DualLattice-Stack': 'v2',
    },
    body: JSON.stringify(body),
  });

  try {
    // ─── Health check ───
    if (method === 'GET' && path === '/health') {
      return respond(200, {
        status: 'healthy',
        version: '3.2.4',
        stack: 'DualLatticeStack v2: Quasicrystal × Hyperbolic × GeoSeal',
        seams: ['manifold-dual-lane', 'trajectory-kernel', 'hyperbolic-rag', 'entropic-layer', 'chsfn'],
        tongues: TONGUE_NAMES,
        ts: Date.now(),
      });
    }

    const body = event.body ? JSON.parse(event.body) : {};

    // ─── Original: Brain lane (fast path) ───
    if (method === 'POST' && path === '/brain-lane') {
      const classification = ManifoldClassifier.classify({ payload: body, route: 'brain' });
      if (classification.laneBit !== 0) {
        return respond(403, { error: 'Request classified for oversight lane', ...classification });
      }
      return respond(200, { processed: true, lane: 'brain', latency: 'fast', classification });
    }

    // ─── Original: Oversight lane (strict path) ───
    if (method === 'POST' && path === '/oversight-lane') {
      const classification = ManifoldClassifier.classify({ payload: body, route: 'oversight' });
      const verification = TrajectoryKernel.verify({ payload: body, ...body });
      if (!verification.authorized) {
        return respond(403, { error: 'Trajectory verification failed', classification, verification });
      }
      return respond(200, { processed: true, lane: 'oversight', latency: 'strict', classification, verification });
    }

    // ─── Original: Verify ───
    if (method === 'POST' && path === '/verify') {
      const verification = TrajectoryKernel.verify({ payload: body, ...body });
      return respond(verification.authorized ? 200 : 403, verification);
    }

    // ─── NEW: HyperbolicRAG trust scoring ───
    if (method === 'POST' && path === '/trust') {
      const ragResult = HyperbolicRAG.assess(body);
      const decision = ragResult.score.quarantine ? 'QUARANTINE' : 'ALLOW';
      return respond(ragResult.score.quarantine ? 403 : 200, {
        decision,
        ...ragResult,
      });
    }

    // ─── NEW: Entropic layer assessment ───
    if (method === 'POST' && path === '/entropic') {
      const ragResult = HyperbolicRAG.assess(body);
      const coherence = body.coherence || ragResult.score.trustScore;
      const entropic = EntropicLayer.assess(ragResult.position, coherence);
      return respond(entropic.recommendation === 'DENY' ? 403 : 200, {
        entropic,
        position: ragResult.position,
      });
    }

    // ─── NEW: CHSFN quasi-sphere assessment ───
    if (method === 'POST' && path === '/chsfn') {
      const ragResult = HyperbolicRAG.assess(body);
      const chsfnResult = CHSFN.assess(ragResult.position, ragResult.phase);
      return respond(200, {
        chsfn: chsfnResult,
        position: ragResult.position,
        phase: ragResult.phase,
      });
    }

    // ─── NEW: Full DualLatticeStack v2 governance pipeline ───
    if (method === 'POST' && path === '/govern') {
      const classification = ManifoldClassifier.classify({ payload: body, route: body.route || 'oversight' });
      const trajectory = TrajectoryKernel.verify({ payload: body, ...body });
      const rag = HyperbolicRAG.assess(body);
      const coherence = body.coherence || rag.score.trustScore;
      const entropic = EntropicLayer.assess(rag.position, coherence);
      const chsfn = CHSFN.assess(rag.position, rag.phase);

      // Unified decision: strictest wins
      let decision = 'ALLOW';
      if (entropic.recommendation === 'DENY' || rag.score.quarantine) decision = 'DENY';
      else if (entropic.recommendation === 'QUARANTINE' || !trajectory.authorized) decision = 'QUARANTINE';
      else if (entropic.recommendation === 'SLOW') decision = 'ESCALATE';

      const statusCode = decision === 'ALLOW' ? 200 : decision === 'ESCALATE' ? 200 : 403;

      return respond(statusCode, {
        decision,
        securityBits: chsfn.securityBits,
        adaptiveK: entropic.adaptiveK,
        pipeline: { classification, trajectory, rag, entropic, chsfn },
      });
    }

    return respond(404, {
      error: 'Not found',
      endpoints: [
        'GET  /health           — Stack status',
        'POST /brain-lane       — Fast-path classifier',
        'POST /oversight-lane   — Strict verification',
        'POST /verify           — Trajectory coherence',
        'POST /trust            — HyperbolicRAG trust scoring (NEW)',
        'POST /entropic         — Entropic layer assessment (NEW)',
        'POST /chsfn            — CHSFN quasi-sphere analysis (NEW)',
        'POST /govern           — Full DualLatticeStack v2 pipeline (NEW)',
      ],
    });
  } catch (err) {
    return respond(500, { error: 'Internal error', message: err.message });
  }
};
