/**
 * Space Tor Trust Manager with Langues Weighting System
 * 
 * Implements Layer 3 (Langues Metric Tensor) for trust scoring across
 * the Six Sacred Tongues (KO, AV, RU, CA, UM, DR).
 * 
 * Mathematical Foundation:
 * L(x,t) = Σ(l=1 to 6) w_l * exp[β_l * (d_l + sin(ω_l*t + φ_l))]
 * where d_l = |x_l - μ_l|
 * 
 * @module spaceTor/trust-manager
 */

/**
 * Sacred Tongue identifiers
 */
export enum SacredTongue {
  KORAELIN = 0,    // KO - Base tongue (w=1.0)
  AVALI = 1,       // AV - Harmonic 1 (w=1.125)
  RUNETHIC = 2,    // RU - Harmonic 2 (w=1.25)
  CASSISIVADAN = 3, // CA - Harmonic 3 (w=1.333)
  UMBROTH = 4,     // UM - Harmonic 4 (w=1.5)
  DRAUMRIC = 5     // DR - Harmonic 5 (w=1.667)
}

/**
 * Langues Weighting System parameters
 */
export interface LanguesParams {
  /** Harmonic weights for each tongue (golden ratio scaling) */
  w: number[];
  
  /** Growth coefficients (β_l) */
  beta: number[];
  
  /** Temporal frequencies (ω_l) */
  omega: number[];
  
  /** Phase offsets (φ_l) */
  phi: number[];
  
  /** Ideal (trusted) values (μ_l) */
  mu: number[];
  
  /** Dimension flux coefficients (ν_l) for breathing */
  nu?: number[];
}

/**
 * Trust score result
 */
export interface TrustScore {
  /** Raw Langues metric L(x,t) */
  raw: number;
  
  /** Normalized score L_N ∈ [0,1] */
  normalized: number;
  
  /** Per-tongue contributions */
  contributions: number[];
  
  /** Gradient field ∇L for descent */
  gradient: number[];
  
  /** Trust level classification */
  level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
}

/**
 * Node trust state
 */
export interface NodeTrust {
  /** Node identifier */
  nodeId: string;
  
  /** 6D trust vector (one per Sacred Tongue) */
  trustVector: number[];
  
  /** Last update timestamp */
  lastUpdate: number;
  
  /** Historical trust scores */
  history: number[];
  
  /** Anomaly flags */
  anomalies: string[];
}

/**
 * Default Langues parameters (production-ready)
 */
export const DEFAULT_LANGUES_PARAMS: LanguesParams = {
  // Golden ratio scaling: w_l = φ^(l-1) where φ ≈ 1.618
  w: [1.0, 1.125, 1.25, 1.333, 1.5, 1.667],
  
  // Growth coefficients (moderate amplification)
  beta: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
  
  // Temporal frequencies (2π/T_l)
  omega: [1, 2, 3, 4, 5, 6],
  
  // Phase offsets (2πk/6)
  phi: [0, Math.PI/3, 2*Math.PI/3, Math.PI, 4*Math.PI/3, 5*Math.PI/3],
  
  // Ideal values (neutral trust)
  mu: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
  
  // Full dimensional participation (polly mode)
  nu: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
};

/**
 * Trust Manager for Space Tor network
 * 
 * Implements Langues Weighting System (Layer 3) for trust scoring
 * across the Six Sacred Tongues.
 */
export class TrustManager {
  private params: LanguesParams;
  private nodes: Map<string, NodeTrust>;
  private maxScore: number;
  
  constructor(params: LanguesParams = DEFAULT_LANGUES_PARAMS) {
    this.params = params;
    this.nodes = new Map();
    this.maxScore = this.computeMaxScore();
  }
  
  /**
   * Compute Langues metric L(x,t)
   * 
   * L(x,t) = Σ(l=1 to 6) ν_l * w_l * exp[β_l * (d_l + sin(ω_l*t + φ_l))]
   * 
   * @param x - 6D trust vector
   * @param t - Current time
   * @returns Raw Langues metric
   */
  private computeLanguesMetric(x: number[], t: number): number {
    const { w, beta, omega, phi, mu, nu } = this.params;
    const nuVec = nu || Array(6).fill(1.0);
    
    let L = 0;
    for (let l = 0; l < 6; l++) {
      // Deviation from ideal
      const d_l = Math.abs(x[l] - mu[l]);
      
      // Temporal oscillation
      const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
      
      // Exponential amplification with flux
      L += nuVec[l] * w[l] * Math.exp(beta[l] * s_l);
    }
    
    return L;
  }
  
  /**
   * Compute gradient field ∇L
   * 
   * ∂L/∂x_l = ν_l * w_l * β_l * exp[β_l * (d_l + sin(...))] * sgn(x_l - μ_l)
   * 
   * @param x - 6D trust vector
   * @param t - Current time
   * @returns Gradient vector
   */
  private computeGradient(x: number[], t: number): number[] {
    const { w, beta, omega, phi, mu, nu } = this.params;
    const nuVec = nu || Array(6).fill(1.0);
    
    const gradient: number[] = [];
    for (let l = 0; l < 6; l++) {
      const d_l = Math.abs(x[l] - mu[l]);
      const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
      const sign = Math.sign(x[l] - mu[l]);
      
      gradient[l] = nuVec[l] * w[l] * beta[l] * Math.exp(beta[l] * s_l) * sign;
    }
    
    return gradient;
  }
  
  /**
   * Compute per-tongue contributions
   * 
   * @param x - 6D trust vector
   * @param t - Current time
   * @returns Array of 6 contributions
   */
  private computeContributions(x: number[], t: number): number[] {
    const { w, beta, omega, phi, mu, nu } = this.params;
    const nuVec = nu || Array(6).fill(1.0);
    
    const contributions: number[] = [];
    for (let l = 0; l < 6; l++) {
      const d_l = Math.abs(x[l] - mu[l]);
      const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
      contributions[l] = nuVec[l] * w[l] * Math.exp(beta[l] * s_l);
    }
    
    return contributions;
  }
  
  /**
   * Compute maximum possible score (for normalization)
   * 
   * L_max occurs when all d_l = 1 and sin(...) = 1
   * 
   * @returns Maximum Langues metric
   */
  private computeMaxScore(): number {
    const { w, beta, nu } = this.params;
    const nuVec = nu || Array(6).fill(1.0);
    
    let maxScore = 0;
    for (let l = 0; l < 6; l++) {
      // Maximum deviation (d_l = 1) + maximum oscillation (sin = 1)
      maxScore += nuVec[l] * w[l] * Math.exp(beta[l] * 2.0);
    }
    
    return maxScore;
  }
  
  /**
   * Classify trust level based on normalized score
   * 
   * @param normalized - Normalized score ∈ [0,1]
   * @returns Trust level
   */
  private classifyTrustLevel(normalized: number): 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL' {
    if (normalized <= 0.3) return 'HIGH';      // Low deviation = high trust
    if (normalized <= 0.5) return 'MEDIUM';    // Moderate deviation
    if (normalized <= 0.7) return 'LOW';       // High deviation = low trust
    return 'CRITICAL';                         // Critical deviation
  }
  
  /**
   * Compute trust score for a node
   * 
   * @param nodeId - Node identifier
   * @param trustVector - 6D trust vector (one per Sacred Tongue)
   * @param t - Current time (default: Date.now() / 1000)
   * @returns Trust score with classification
   */
  public computeTrustScore(
    nodeId: string,
    trustVector: number[],
    t: number = Date.now() / 1000
  ): TrustScore {
    if (trustVector.length !== 6) {
      throw new Error('Trust vector must have 6 dimensions (one per Sacred Tongue)');
    }
    
    // Validate trust vector values ∈ [0,1]
    for (let i = 0; i < 6; i++) {
      if (trustVector[i] < 0 || trustVector[i] > 1) {
        throw new Error(`Trust vector[${i}] must be in [0,1], got ${trustVector[i]}`);
      }
    }
    
    // Compute Langues metric
    const raw = this.computeLanguesMetric(trustVector, t);
    const normalized = raw / this.maxScore;
    const contributions = this.computeContributions(trustVector, t);
    const gradient = this.computeGradient(trustVector, t);
    const level = this.classifyTrustLevel(normalized);
    
    // Update node trust state
    this.updateNodeTrust(nodeId, trustVector, raw);
    
    return {
      raw,
      normalized,
      contributions,
      gradient,
      level
    };
  }
  
  /**
   * Update node trust state
   * 
   * @param nodeId - Node identifier
   * @param trustVector - 6D trust vector
   * @param score - Raw trust score
   */
  private updateNodeTrust(nodeId: string, trustVector: number[], score: number): void {
    const existing = this.nodes.get(nodeId);
    
    if (existing) {
      existing.trustVector = trustVector;
      existing.lastUpdate = Date.now();
      existing.history.push(score);
      
      // Keep last 100 scores
      if (existing.history.length > 100) {
        existing.history.shift();
      }
      
      // Detect anomalies (sudden trust drops)
      if (existing.history.length >= 2) {
        const prev = existing.history[existing.history.length - 2];
        const curr = score;
        const drop = (prev - curr) / prev;
        
        if (drop > 0.3) {
          existing.anomalies.push(`Trust drop: ${(drop * 100).toFixed(1)}% at ${new Date().toISOString()}`);
        }
      }
    } else {
      this.nodes.set(nodeId, {
        nodeId,
        trustVector,
        lastUpdate: Date.now(),
        history: [score],
        anomalies: []
      });
    }
  }
  
  /**
   * Get node trust state
   * 
   * @param nodeId - Node identifier
   * @returns Node trust state or undefined
   */
  public getNodeTrust(nodeId: string): NodeTrust | undefined {
    return this.nodes.get(nodeId);
  }
  
  /**
   * Get all nodes with trust level
   * 
   * @param level - Trust level filter
   * @returns Array of node IDs
   */
  public getNodesByTrustLevel(level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL'): string[] {
    const result: string[] = [];
    const t = Date.now() / 1000;
    
    for (const [nodeId, node] of this.nodes.entries()) {
      const score = this.computeTrustScore(nodeId, node.trustVector, t);
      if (score.level === level) {
        result.push(nodeId);
      }
    }
    
    return result;
  }
  
  /**
   * Update dimension flux coefficients (breathing)
   * 
   * Allows dynamic adjustment of dimensional participation:
   * - ν_l = 1.0: Full participation (polly)
   * - 0.5 < ν_l < 1.0: Partial participation (demi)
   * - ν_l < 0.5: Weak participation (quasi)
   * 
   * @param nu - New flux coefficients [6]
   */
  public updateFluxCoefficients(nu: number[]): void {
    if (nu.length !== 6) {
      throw new Error('Flux coefficients must have 6 dimensions');
    }
    
    for (let i = 0; i < 6; i++) {
      if (nu[i] < 0 || nu[i] > 1) {
        throw new Error(`Flux coefficient[${i}] must be in [0,1], got ${nu[i]}`);
      }
    }
    
    this.params.nu = nu;
    this.maxScore = this.computeMaxScore(); // Recompute max score
  }
  
  /**
   * Get trust statistics
   * 
   * @returns Statistics object
   */
  public getStatistics(): {
    totalNodes: number;
    highTrust: number;
    mediumTrust: number;
    lowTrust: number;
    criticalTrust: number;
    averageScore: number;
  } {
    const t = Date.now() / 1000;
    let totalScore = 0;
    let highTrust = 0;
    let mediumTrust = 0;
    let lowTrust = 0;
    let criticalTrust = 0;
    
    for (const [nodeId, node] of this.nodes.entries()) {
      const score = this.computeTrustScore(nodeId, node.trustVector, t);
      totalScore += score.normalized;
      
      switch (score.level) {
        case 'HIGH': highTrust++; break;
        case 'MEDIUM': mediumTrust++; break;
        case 'LOW': lowTrust++; break;
        case 'CRITICAL': criticalTrust++; break;
      }
    }
    
    return {
      totalNodes: this.nodes.size,
      highTrust,
      mediumTrust,
      lowTrust,
      criticalTrust,
      averageScore: this.nodes.size > 0 ? totalScore / this.nodes.size : 0
    };
  }
  
  /**
   * Clear all node trust data
   */
  public clear(): void {
    this.nodes.clear();
  }
}

/**
 * Standalone Langues metric function (for external use)
 * 
 * @param x - 6D trust vector
 * @param mu - Ideal values [6]
 * @param w - Harmonic weights [6]
 * @param beta - Growth coefficients [6]
 * @param omega - Temporal frequencies [6]
 * @param phi - Phase offsets [6]
 * @param t - Current time
 * @param nu - Flux coefficients [6] (optional)
 * @returns Langues metric L(x,t)
 */
export function languesMetric(
  x: number[],
  mu: number[],
  w: number[],
  beta: number[],
  omega: number[],
  phi: number[],
  t: number,
  nu?: number[]
): number {
  const nuVec = nu || Array(6).fill(1.0);
  
  let L = 0;
  for (let l = 0; l < 6; l++) {
    const d_l = Math.abs(x[l] - mu[l]);
    const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
    L += nuVec[l] * w[l] * Math.exp(beta[l] * s_l);
  }
  
  return L;
}

/**
 * Langues metric with flux (breathing dimensions)
 * 
 * @param x - 6D trust vector
 * @param mu - Ideal values [6]
 * @param w - Harmonic weights [6]
 * @param beta - Growth coefficients [6]
 * @param omega - Temporal frequencies [6]
 * @param phi - Phase offsets [6]
 * @param t - Current time
 * @param nu - Flux coefficients [6]
 * @returns Langues metric L_f(x,t)
 */
export function languesMetricFlux(
  x: number[],
  mu: number[],
  w: number[],
  beta: number[],
  omega: number[],
  phi: number[],
  t: number,
  nu: number[]
): number {
  return languesMetric(x, mu, w, beta, omega, phi, t, nu);
}

/**
 * Export all functions for Layer 3 integration
 */
export default {
  TrustManager,
  languesMetric,
  languesMetricFlux,
  DEFAULT_LANGUES_PARAMS,
  SacredTongue
};
