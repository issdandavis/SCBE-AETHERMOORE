/**
 * Spiralverse Protocol - Patent Seam Demonstration
 * Implements: (1) Manifold-Gated Dual-Lane (2) Trajectory + Drift Coherence
 * Zero dependencies - AWS Lambda ready
 */

// SEAM 1: Manifold-Gated Dual-Lane Classifier
const ManifoldClassifier = {
  PHI: 1.618033988749895,
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
    return Math.max(...Object.values(obj).map(v => this.objectDepth(v, d + 1)), d);
  },

  computeLaneBit(geometry) {
    const { entropy, complexity, depth } = geometry;
    const r = Math.sqrt(entropy * entropy + (complexity / 100) ** 2);
    const theta = Math.atan2(depth, entropy) * this.PHI;
    const projection = Math.sin(theta) * r / (1 + Math.abs(Math.cos(theta * this.PHI)));
    const normalized = (Math.tanh(projection) + 1) / 2;
    return { laneBit: normalized >= this.LANE_THRESHOLD ? 1 : 0, confidence: normalized };
  },

  classify(context) {
    const geometry = this.extractGeometry(context);
    const { laneBit, confidence } = this.computeLaneBit(geometry);
    return {
      lane: laneBit === 0 ? 'brain' : 'oversight',
      laneBit, confidence: Math.round(confidence * 1000) / 1000, geometry
    };
  }
};

// SEAM 2: Trajectory + Drift Coherence Kernel (5-variable authorization)
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
      signature: this.computeSignature(request)
    };
  },

  hashOrigin(sourceId) {
    let hash = 0;
    for (let i = 0; i < sourceId.length; i++) {
      hash = ((hash << 5) - hash) + sourceId.charCodeAt(i);
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
    for (let i = 1; i < history.length; i++) diffs.push(history[i] - history[i-1]);
    for (let i = 1; i < diffs.length; i++) diffs2.push(diffs[i] - diffs[i-1]);
    const avgCurve = diffs2.reduce((a, b) => a + b, 0) / diffs2.length;
    return Math.tanh(avgCurve / 100) * 0.5 + 0.5;
  },

  computePhase(now) { return (now % 60000) / 60000; },

  computeSignature(request) {
    const payload = JSON.stringify(request.payload || {});
    let sig = 0;
    for (let i = 0; i < payload.length; i++) sig = (sig * 31 + payload.charCodeAt(i)) & 0xFFFFFFFF;
    return (sig >>> 0) / 0xFFFFFFFF;
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
      thresholds: { coherence: this.COHERENCE_THRESHOLD, drift: this.DRIFT_TOLERANCE }
    };
  }
};

// Lambda Handler - API Gateway Integration
exports.handler = async (event) => {
  const method = event.httpMethod || event.requestContext?.http?.method || 'GET';
  const path = event.path || event.rawPath || '/';
  const respond = (statusCode, body) => ({
    statusCode,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  try {
    if (method === 'GET' && path === '/health') {
      return respond(200, { status: 'healthy', seams: ['manifold-dual-lane', 'trajectory-kernel'], ts: Date.now() });
    }

    const body = event.body ? JSON.parse(event.body) : {};

    if (method === 'POST' && path === '/brain-lane') {
      const classification = ManifoldClassifier.classify({ payload: body, route: 'brain' });
      if (classification.laneBit !== 0) {
        return respond(403, { error: 'Request classified for oversight lane', ...classification });
      }
      return respond(200, { processed: true, lane: 'brain', latency: 'fast', classification });
    }

    if (method === 'POST' && path === '/oversight-lane') {
      const classification = ManifoldClassifier.classify({ payload: body, route: 'oversight' });
      const verification = TrajectoryKernel.verify({ payload: body, ...body });
      if (!verification.authorized) {
        return respond(403, { error: 'Trajectory verification failed', classification, verification });
      }
      return respond(200, { processed: true, lane: 'oversight', latency: 'strict', classification, verification });
    }

    if (method === 'POST' && path === '/verify') {
      const verification = TrajectoryKernel.verify({ payload: body, ...body });
      return respond(verification.authorized ? 200 : 403, verification);
    }

    return respond(404, { error: 'Not found', endpoints: ['/health', '/brain-lane', '/oversight-lane', '/verify'] });
  } catch (err) {
    return respond(500, { error: 'Internal error', message: err.message });
  }
};
