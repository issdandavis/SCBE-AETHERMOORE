/**
 * Unified SCBE Gateway API
 *
 * Central entry point that integrates:
 * - SCBE 14-layer authorization pipeline
 * - Spiralverse Six Sacred Tongues encoding
 * - Swarm coordination and fleet management
 * - Contact graph routing
 * - Trust vector computation
 *
 * @module gateway/unified-api
 */

import { ContactGraph, computeContactGraph, type ContactPath } from '../network/contact-graph.js';

// Type definitions for the unified gateway
export interface AuthorizationRequest {
  agentId: string;
  action: string;
  target: string;
  context?: Record<string, unknown>;
  tongues?: TongueID[];
}

export interface AuthorizationResponse {
  decision: 'ALLOW' | 'QUARANTINE' | 'DENY';
  decisionId: string;
  score: number;
  riskFactors: RiskFactors;
  token?: string;
  expiresAt?: string;
  explanation?: LayerExplanation;
}

export interface RiskFactors {
  hyperbolicDistance: number;
  spectralCoherence: number;
  spinCoherence: number;
  triadicDistance: number;
  audioStability: number;
  harmonicMagnification: number;
  compositeRisk: number;
}

export interface LayerExplanation {
  layers: Record<string, LayerResult>;
  dominantFactor: string;
  recommendation: string;
}

export interface LayerResult {
  name: string;
  value: number;
  contribution: number;
  status: 'pass' | 'warn' | 'fail';
}

export type TongueID = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

export interface RWPEnvelope {
  ver: '2.1' | '3.0';
  primaryTongue: TongueID;
  payload: string;
  signatures: Record<TongueID, string>;
  nonce: string;
  timestamp: number;
  aad?: string;
}

export interface SwarmState {
  swarmId: string;
  agents: AgentState[];
  coherenceScore: number;
  dominantState: 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';
  trustMatrix: number[][];
  contactGraph: ContactGraphData;
}

export interface AgentState {
  id: string;
  position6D: number[];
  trustScore: number;
  trustLevel: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
  trustVector: number[];
  dimensionalState: 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';
  nu: number;
  swarmId?: string;
}

export interface ContactGraphData {
  nodes: Array<{ id: string; type: string; position: number[]; trust: number }>;
  edges: Array<{ source: string; target: string; latency: number; capacity: number }>;
}

export interface QuantumKeyExchange {
  sessionId: string;
  publicKey: string;
  algorithm: 'ML-KEM-768' | 'ML-KEM-1024';
  timestamp: number;
}

export interface GatewayConfig {
  scbeEndpoint?: string;
  quantumEndpoint?: string;
  spiralverseEndpoint?: string;
  redisUrl?: string;
  defaultTongues?: TongueID[];
  riskThresholds?: {
    allow: number;
    deny: number;
  };
}

/**
 * Unified SCBE Gateway
 *
 * Provides a single API for all SCBE ecosystem services:
 * - Authorization (14-layer pipeline)
 * - Protocol encoding (Six Sacred Tongues)
 * - Quantum key exchange (ML-KEM)
 * - Swarm coordination
 * - Contact graph routing
 */
export class UnifiedSCBEGateway {
  private config: Required<GatewayConfig>;
  private contactGraph: ContactGraph;
  private agentRegistry: Map<string, AgentState> = new Map();
  private swarmRegistry: Map<string, Set<string>> = new Map();

  constructor(config: GatewayConfig = {}) {
    this.config = {
      scbeEndpoint: config.scbeEndpoint ?? 'http://localhost:8000',
      quantumEndpoint: config.quantumEndpoint ?? 'http://localhost:8001',
      spiralverseEndpoint: config.spiralverseEndpoint ?? 'http://localhost:8002',
      redisUrl: config.redisUrl ?? 'redis://localhost:6379',
      defaultTongues: config.defaultTongues ?? ['KO', 'RU', 'UM'],
      riskThresholds: config.riskThresholds ?? { allow: 0.3, deny: 0.7 },
    };

    this.contactGraph = new ContactGraph();
  }

  // ============================================
  // AUTHORIZATION (14-Layer Pipeline)
  // ============================================

  /**
   * Process authorization request through 14-layer SCBE pipeline
   */
  async authorize(request: AuthorizationRequest): Promise<AuthorizationResponse> {
    const startTime = Date.now();

    // Layer 1-4: Context encoding and embedding
    const contextVector = this.encodeContext(request);
    const embeddedPoint = this.embedToPoincareBall(contextVector);

    // Layer 5: Hyperbolic distance to trust centers
    const hyperbolicDistance = this.computeHyperbolicDistance(embeddedPoint);

    // Layer 6: Breathing transform
    const breathedPoint = this.applyBreathingTransform(embeddedPoint);

    // Layer 7: Phase transform
    const phasedPoint = this.applyPhaseTransform(breathedPoint);

    // Layer 8: Multi-well realm distance
    const realmDistance = this.computeRealmDistance(phasedPoint);

    // Layer 9: Spectral coherence
    const spectralCoherence = this.computeSpectralCoherence(request);

    // Layer 10: Spin coherence
    const spinCoherence = this.computeSpinCoherence(request);

    // Layer 11: Triadic temporal distance
    const triadicDistance = this.computeTriadicDistance(request);

    // Layer 12: Harmonic magnification
    const harmonicMagnification = this.computeHarmonicScaling(realmDistance);

    // Layer 13: Composite risk
    const audioStability = this.computeAudioStability(request);
    const compositeRisk = this.computeCompositeRisk({
      hyperbolicDistance,
      spectralCoherence,
      spinCoherence,
      triadicDistance,
      audioStability,
      harmonicMagnification,
    });

    // Layer 14: Decision
    const decision = this.makeDecision(compositeRisk);

    const decisionId = `dec_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

    return {
      decision,
      decisionId,
      score: compositeRisk,
      riskFactors: {
        hyperbolicDistance,
        spectralCoherence,
        spinCoherence,
        triadicDistance,
        audioStability,
        harmonicMagnification,
        compositeRisk,
      },
      token: decision === 'ALLOW' ? this.generateToken(decisionId) : undefined,
      expiresAt: decision === 'ALLOW' ? new Date(Date.now() + 300000).toISOString() : undefined,
      explanation: {
        layers: this.buildLayerExplanation({
          hyperbolicDistance,
          spectralCoherence,
          spinCoherence,
          triadicDistance,
          audioStability,
        }),
        dominantFactor: this.findDominantFactor({
          hyperbolicDistance,
          spectralCoherence,
          spinCoherence,
          triadicDistance,
          audioStability,
        }),
        recommendation: this.generateRecommendation(decision, compositeRisk),
      },
    };
  }

  // ============================================
  // PROTOCOL ENCODING (Six Sacred Tongues)
  // ============================================

  /**
   * Encode message using Spiralverse protocol
   */
  async encodeRWP(
    payload: unknown,
    tongues: TongueID[] = this.config.defaultTongues
  ): Promise<RWPEnvelope> {
    const payloadStr = JSON.stringify(payload);
    const payloadB64 = Buffer.from(payloadStr).toString('base64url');
    const nonce = this.generateNonce();
    const timestamp = Date.now();

    // Generate signatures for each tongue
    const signatures: Record<TongueID, string> = {} as Record<TongueID, string>;
    for (const tongue of tongues) {
      signatures[tongue] = await this.signWithTongue(payloadB64, tongue, nonce);
    }

    return {
      ver: '2.1',
      primaryTongue: tongues[0],
      payload: payloadB64,
      signatures,
      nonce,
      timestamp,
      aad: `gateway=unified;tongues=${tongues.join(',')}`,
    };
  }

  /**
   * Verify and decode RWP envelope
   */
  async decodeRWP(
    envelope: RWPEnvelope
  ): Promise<{ valid: boolean; payload?: unknown; error?: string }> {
    // Verify all signatures
    for (const [tongue, signature] of Object.entries(envelope.signatures)) {
      const valid = await this.verifyTongueSignature(
        envelope.payload,
        tongue as TongueID,
        signature,
        envelope.nonce
      );
      if (!valid) {
        return { valid: false, error: `Invalid ${tongue} signature` };
      }
    }

    // Check timestamp (5 minute window)
    if (Math.abs(Date.now() - envelope.timestamp) > 300000) {
      return { valid: false, error: 'Envelope expired' };
    }

    // Decode payload
    const payloadStr = Buffer.from(envelope.payload, 'base64url').toString();
    return { valid: true, payload: JSON.parse(payloadStr) };
  }

  // ============================================
  // SWARM COORDINATION
  // ============================================

  /**
   * Get current state of a swarm
   */
  async getSwarmState(swarmId: string): Promise<SwarmState> {
    const agentIds = this.swarmRegistry.get(swarmId) ?? new Set();
    const agents: AgentState[] = [];

    for (const agentId of agentIds) {
      const agent = this.agentRegistry.get(agentId);
      if (agent) agents.push(agent);
    }

    // Compute swarm metrics
    const coherenceScore = this.computeSwarmCoherence(agents);
    const dominantState = this.computeDominantState(agents);
    const trustMatrix = this.computeTrustMatrix(agents);

    return {
      swarmId,
      agents,
      coherenceScore,
      dominantState,
      trustMatrix,
      contactGraph: this.contactGraph.toVisualizationData(),
    };
  }

  /**
   * Register an agent with a swarm
   */
  registerAgent(agent: AgentState, swarmId?: string): void {
    this.agentRegistry.set(agent.id, agent);

    // Add to contact graph
    this.contactGraph.addNode({
      id: agent.id,
      type: 'LEO',
      position6D: agent.position6D,
      trustScore: agent.trustScore,
      lastSeen: Date.now(),
    });

    // Add to swarm if specified
    if (swarmId) {
      if (!this.swarmRegistry.has(swarmId)) {
        this.swarmRegistry.set(swarmId, new Set());
      }
      this.swarmRegistry.get(swarmId)!.add(agent.id);
      agent.swarmId = swarmId;
    }
  }

  /**
   * Update agent state
   */
  updateAgent(agentId: string, updates: Partial<AgentState>): boolean {
    const agent = this.agentRegistry.get(agentId);
    if (!agent) return false;

    Object.assign(agent, updates);
    return true;
  }

  // ============================================
  // CONTACT GRAPH ROUTING
  // ============================================

  /**
   * Find optimal path between two agents
   */
  findPath(source: string, target: string): ContactPath | null {
    return this.contactGraph.findShortestPath(source, target);
  }

  /**
   * Find k-redundant paths for fault tolerance
   */
  findRedundantPaths(source: string, target: string, k: number = 3): ContactPath[] {
    return this.contactGraph.findDisjointPaths(source, target, k);
  }

  /**
   * Rebuild contact graph from current agents
   */
  rebuildContactGraph(): void {
    const agents = Array.from(this.agentRegistry.values());
    this.contactGraph = computeContactGraph(
      agents.map((a) => ({
        id: a.id,
        type: 'LEO' as const,
        position6D: a.position6D,
        trustScore: a.trustScore,
      })),
      3600000 // 1 hour horizon
    );
  }

  // ============================================
  // QUANTUM KEY EXCHANGE
  // ============================================

  /**
   * Initiate quantum key exchange
   */
  async initiateQuantumKeyExchange(
    peerId: string,
    algorithm: 'ML-KEM-768' | 'ML-KEM-1024' = 'ML-KEM-768'
  ): Promise<QuantumKeyExchange> {
    // In a real implementation, this would call scbe-quantum-prototype
    const sessionId = `qkex_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

    // Placeholder for actual Kyber keygen
    const publicKey = Buffer.from(
      crypto.getRandomValues(new Uint8Array(algorithm === 'ML-KEM-768' ? 1184 : 1568))
    ).toString('base64');

    return {
      sessionId,
      publicKey,
      algorithm,
      timestamp: Date.now(),
    };
  }

  // ============================================
  // PRIVATE HELPER METHODS
  // ============================================

  private encodeContext(request: AuthorizationRequest): number[] {
    // Simple context encoding to 6D vector
    const actionHash = this.hashString(request.action);
    const targetHash = this.hashString(request.target);
    const agentHash = this.hashString(request.agentId);

    return [
      (actionHash % 1000) / 1000,
      (targetHash % 1000) / 1000,
      (agentHash % 1000) / 1000,
      (request.context?.sensitivity as number) ?? 0.5,
      (request.context?.urgency as number) ?? 0.5,
      request.tongues?.length ?? 3 / 6,
    ];
  }

  private embedToPoincareBall(vector: number[]): number[] {
    // Poincaré ball embedding: u = tanh(||x||) * x / ||x||
    const norm = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0));
    if (norm < 1e-10) return vector.map(() => 0);

    const scale = Math.tanh(norm) / norm;
    return vector.map((v) => v * scale * 0.99); // Keep inside ball
  }

  private computeHyperbolicDistance(point: number[]): number {
    // Distance to origin in Poincaré ball
    const normSq = point.reduce((sum, v) => sum + v * v, 0);
    if (normSq >= 1) return Infinity;

    // d_H(0, u) = 2 * arctanh(||u||)
    const norm = Math.sqrt(normSq);
    return 2 * Math.atanh(Math.min(norm, 0.9999));
  }

  private applyBreathingTransform(point: number[]): number[] {
    // Radial breathing: b > 1 contracts, b < 1 expands
    const b = 1.2; // Default: slight contraction (more secure)
    const norm = Math.sqrt(point.reduce((sum, v) => sum + v * v, 0));
    if (norm < 1e-10) return point;

    const r = Math.tanh(b * Math.atanh(norm));
    return point.map((v) => (v / norm) * r);
  }

  private applyPhaseTransform(point: number[]): number[] {
    // Simple rotation (in production, would use epoch-based Q matrix)
    const theta = (Date.now() / 86400000) * Math.PI * 2; // Daily rotation
    const cos = Math.cos(theta);
    const sin = Math.sin(theta);

    // Rotate first two dimensions
    return [point[0] * cos - point[1] * sin, point[0] * sin + point[1] * cos, ...point.slice(2)];
  }

  private computeRealmDistance(point: number[]): number {
    // Distance to nearest realm center
    const realmCenters = [
      [0.3, 0, 0, 0, 0, 0],
      [-0.3, 0, 0, 0, 0, 0],
      [0, 0.3, 0, 0, 0, 0],
      [0, -0.3, 0, 0, 0, 0],
    ];

    let minDist = Infinity;
    for (const center of realmCenters) {
      const dist = Math.sqrt(point.reduce((sum, v, i) => sum + (v - center[i]) ** 2, 0));
      minDist = Math.min(minDist, dist);
    }

    return minDist;
  }

  private computeSpectralCoherence(_request: AuthorizationRequest): number {
    // Placeholder: would analyze telemetry FFT
    return 0.85 + Math.random() * 0.1;
  }

  private computeSpinCoherence(_request: AuthorizationRequest): number {
    // Placeholder: would compute phase-sensitive interference
    return 0.8 + Math.random() * 0.15;
  }

  private computeTriadicDistance(_request: AuthorizationRequest): number {
    // Placeholder: would compute across 3 timescales
    return 0.2 + Math.random() * 0.3;
  }

  private computeAudioStability(_request: AuthorizationRequest): number {
    // Placeholder: Layer 14 audio telemetry
    return 0.9 + Math.random() * 0.08;
  }

  private computeHarmonicScaling(distance: number): number {
    // H(d, R) = R^(d²) where R = e
    const R = Math.E;
    return Math.pow(R, distance * distance);
  }

  private computeCompositeRisk(factors: Omit<RiskFactors, 'compositeRisk'>): number {
    const weights = {
      hyperbolicDistance: 0.2,
      spectralCoherence: 0.15,
      spinCoherence: 0.15,
      triadicDistance: 0.2,
      audioStability: 0.1,
    };

    // Normalize triadic distance to 0-1
    const normalizedTriadic = Math.min(1, factors.triadicDistance / 2);

    // Compute weighted sum
    const baseRisk =
      weights.hyperbolicDistance * Math.min(1, factors.hyperbolicDistance / 3) +
      weights.spectralCoherence * (1 - factors.spectralCoherence) +
      weights.spinCoherence * (1 - factors.spinCoherence) +
      weights.triadicDistance * normalizedTriadic +
      weights.audioStability * (1 - factors.audioStability);

    // Apply harmonic magnification
    return baseRisk * factors.harmonicMagnification;
  }

  private makeDecision(compositeRisk: number): 'ALLOW' | 'QUARANTINE' | 'DENY' {
    if (compositeRisk < this.config.riskThresholds.allow) return 'ALLOW';
    if (compositeRisk > this.config.riskThresholds.deny) return 'DENY';
    return 'QUARANTINE';
  }

  private generateToken(decisionId: string): string {
    return `scbe_tok_${decisionId}_${Date.now().toString(36)}`;
  }

  private generateNonce(): string {
    const bytes = crypto.getRandomValues(new Uint8Array(12));
    return Buffer.from(bytes).toString('base64url');
  }

  private async signWithTongue(payload: string, tongue: TongueID, nonce: string): Promise<string> {
    // Placeholder: would use actual HMAC with tongue-specific key
    const data = `${tongue}:${payload}:${nonce}`;
    const hash = this.hashString(data);
    return `sig_${tongue}_${hash.toString(16)}`;
  }

  private async verifyTongueSignature(
    payload: string,
    tongue: TongueID,
    signature: string,
    nonce: string
  ): Promise<boolean> {
    const expected = await this.signWithTongue(payload, tongue, nonce);
    return signature === expected;
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  private computeSwarmCoherence(agents: AgentState[]): number {
    if (agents.length < 2) return 1;

    // Compute variance of nu values
    const nuValues = agents.map((a) => a.nu);
    const mean = nuValues.reduce((a, b) => a + b, 0) / nuValues.length;
    const variance = nuValues.reduce((sum, v) => sum + (v - mean) ** 2, 0) / nuValues.length;

    return 1 / (1 + variance);
  }

  private computeDominantState(agents: AgentState[]): SwarmState['dominantState'] {
    const stateCounts = { POLLY: 0, QUASI: 0, DEMI: 0, COLLAPSED: 0 };

    for (const agent of agents) {
      stateCounts[agent.dimensionalState]++;
    }

    let maxCount = 0;
    let dominant: SwarmState['dominantState'] = 'POLLY';

    for (const [state, count] of Object.entries(stateCounts)) {
      if (count > maxCount) {
        maxCount = count;
        dominant = state as SwarmState['dominantState'];
      }
    }

    return dominant;
  }

  private computeTrustMatrix(agents: AgentState[]): number[][] {
    const n = agents.length;
    const matrix: number[][] = Array(n)
      .fill(null)
      .map(() => Array(n).fill(0));

    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if (i === j) {
          matrix[i][j] = 1;
        } else {
          // Trust based on distance and trust scores
          const dist = Math.sqrt(
            agents[i].position6D.reduce((sum, v, k) => sum + (v - agents[j].position6D[k]) ** 2, 0)
          );
          matrix[i][j] = (agents[i].trustScore * agents[j].trustScore) / (1 + dist);
        }
      }
    }

    return matrix;
  }

  private buildLayerExplanation(
    factors: Omit<RiskFactors, 'compositeRisk' | 'harmonicMagnification'>
  ): Record<string, LayerResult> {
    return {
      hyperbolicDistance: {
        name: 'Hyperbolic Distance (L5)',
        value: factors.hyperbolicDistance,
        contribution: factors.hyperbolicDistance / 3,
        status:
          factors.hyperbolicDistance < 1
            ? 'pass'
            : factors.hyperbolicDistance < 2
              ? 'warn'
              : 'fail',
      },
      spectralCoherence: {
        name: 'Spectral Coherence (L9)',
        value: factors.spectralCoherence,
        contribution: 1 - factors.spectralCoherence,
        status:
          factors.spectralCoherence > 0.8
            ? 'pass'
            : factors.spectralCoherence > 0.6
              ? 'warn'
              : 'fail',
      },
      spinCoherence: {
        name: 'Spin Coherence (L10)',
        value: factors.spinCoherence,
        contribution: 1 - factors.spinCoherence,
        status:
          factors.spinCoherence > 0.7 ? 'pass' : factors.spinCoherence > 0.5 ? 'warn' : 'fail',
      },
      triadicDistance: {
        name: 'Triadic Temporal (L11)',
        value: factors.triadicDistance,
        contribution: factors.triadicDistance / 2,
        status:
          factors.triadicDistance < 0.5 ? 'pass' : factors.triadicDistance < 1 ? 'warn' : 'fail',
      },
      audioStability: {
        name: 'Audio Stability (L14)',
        value: factors.audioStability,
        contribution: 1 - factors.audioStability,
        status:
          factors.audioStability > 0.9 ? 'pass' : factors.audioStability > 0.7 ? 'warn' : 'fail',
      },
    };
  }

  private findDominantFactor(
    factors: Omit<RiskFactors, 'compositeRisk' | 'harmonicMagnification'>
  ): string {
    const contributions = [
      { name: 'hyperbolicDistance', value: factors.hyperbolicDistance / 3 },
      { name: 'spectralCoherence', value: 1 - factors.spectralCoherence },
      { name: 'spinCoherence', value: 1 - factors.spinCoherence },
      { name: 'triadicDistance', value: factors.triadicDistance / 2 },
      { name: 'audioStability', value: 1 - factors.audioStability },
    ];

    return contributions.reduce((max, curr) => (curr.value > max.value ? curr : max)).name;
  }

  private generateRecommendation(decision: 'ALLOW' | 'QUARANTINE' | 'DENY', risk: number): string {
    if (decision === 'ALLOW') {
      return `Request approved (risk: ${(risk * 100).toFixed(1)}%). Token valid for 5 minutes.`;
    } else if (decision === 'QUARANTINE') {
      return `Request requires additional verification (risk: ${(risk * 100).toFixed(1)}%). Consider multi-tongue signature escalation.`;
    } else {
      return `Request denied (risk: ${(risk * 100).toFixed(1)}%). Agent should re-authenticate or reduce request scope.`;
    }
  }
}

export default UnifiedSCBEGateway;
