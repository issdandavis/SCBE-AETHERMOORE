/**
 * Spectral Identity Generator
 *
 * Generates unique spectral fingerprints for agents based on
 * harmonic analysis and trust vectors.
 */

export interface SpectralIdentity {
  id: string;
  fingerprint: string;
  spectralHash: string;
  timestamp: number;
  trustVector: number[];
}

export class SpectralIdentityGenerator {
  /**
   * Generate a unique spectral identity
   */
  public generate(trustVector: number[] = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]): SpectralIdentity {
    const timestamp = Date.now();
    const fingerprint = this.computeFingerprint(trustVector, timestamp);
    const randomPart = Math.random().toString(36).substring(2, 8);

    return {
      id: `sid-${timestamp.toString(36)}-${randomPart}`,
      fingerprint,
      spectralHash: fingerprint,
      timestamp,
      trustVector: [...trustVector]
    };
  }

  /**
   * Generate identity with specific ID - used by fleet components
   */
  public generateIdentity(id?: string, trustVector?: number[]): SpectralIdentity {
    const identity = this.generate(trustVector);
    if (id) {
      identity.id = id;
    }
    return identity;
  }

  /**
   * Compute spectral fingerprint from trust vector
   */
  private computeFingerprint(trustVector: number[], timestamp: number): string {
    // Combine trust vector with timestamp using harmonic mixing
    let hash = 0;
    for (let i = 0; i < trustVector.length; i++) {
      hash = ((hash << 5) - hash) + Math.floor(trustVector[i] * 1000);
      hash = hash ^ (timestamp >> (i * 4));
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16).padStart(8, '0');
  }

  /**
   * Verify a spectral identity
   */
  public verify(identity: SpectralIdentity): boolean {
    const expected = this.computeFingerprint(identity.trustVector, identity.timestamp);
    return expected === identity.fingerprint;
  }
}
