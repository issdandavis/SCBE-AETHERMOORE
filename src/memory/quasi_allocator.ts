/**
 * @file quasi_allocator.ts
 * @module memory/quasi_allocator
 * @layer Layer 2
 * @component GeoSeal / Mixed-Curvature Access Kernel - HF model load gating
 */

export type HFLoadDecision = 'ALLOW' | 'QUARANTINE';

export interface HFLoadResult {
  repo: string;
  norm: number;
  decision: HFLoadDecision;
  reason: string;
}

/**
 * Quasicrystal lattice helper for governed resource loading.
 */
export class QuasicrystalLattice {
  private readonly boundary: number;

  constructor(boundary: number = 0.95) {
    this.boundary = boundary;
  }

  /**
   * Embed a repo id as a deterministic quasi-point and compute its norm.
   */
  private embedRepo(repo: string): number[] {
    const dims = 6;
    const vec = new Array<number>(dims).fill(0);
    for (let i = 0; i < repo.length; i++) {
      const code = repo.charCodeAt(i);
      vec[i % dims] += ((code % 32) - 15.5) / 31;
    }
    return vec.map((v) => Math.tanh(v / Math.max(1, repo.length / 4)));
  }

  private norm(v: number[]): number {
    return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
  }

  /**
   * Govern HF model downloads via quasi-point containment.
   * If norm > 0.95, treat as missing-artifact risk and quarantine.
   */
  hfLoad(repo: string): HFLoadResult {
    const point = this.embedRepo(repo);
    const n = this.norm(point);

    // Audit traceability: norm only, never secrets/tokens.
    console.info(`[L2][HF_LOAD] repo=${repo} lattice_norm=${n.toFixed(6)}`);

    if (n > this.boundary) {
      return {
        repo,
        norm: n,
        decision: 'QUARANTINE',
        reason: `quasi-norm ${n.toFixed(6)} exceeds boundary ${this.boundary}`,
      };
    }

    return {
      repo,
      norm: n,
      decision: 'ALLOW',
      reason: 'within quasi-lattice boundary',
    };
  }
}
