/**
 * Hybrid Encryption Layer (Quantum + Algorithmic)
 *
 * Handles "Onion" wrapping with distinction between:
 * - Quantum Key Distribution (QKD) capable nodes
 * - Algorithmic derivation (π^φ system) for legacy nodes
 *
 * References:
 * - arXiv:2505.13239 (Network-wide QKD with Onion Routing)
 * - arXiv:2502.06657 (Onion Routing Key Distribution for QKDN)
 * - arXiv:1507.05724 (HORNET: High-speed Onion Routing)
 */
/// <reference types="node" />
/// <reference types="node" />
import type { RelayNode } from './space-tor-router';
export declare class HybridSpaceCrypto {
    /**
     * Logic: Layer encryption from Exit -> Entry
     *
     * Builds onion encryption layers backwards (exit first, entry last)
     * so that each relay can peel one layer to reveal next hop.
     *
     * @param payload - Original data to encrypt
     * @param path - Array of relay nodes [entry, middle, exit]
     * @returns Encrypted onion packet
     */
    buildOnion(payload: Buffer, path: RelayNode[]): Promise<Buffer>;
    /**
     * Decrypt one layer of the onion
     *
     * @param onion - Encrypted onion packet
     * @param node - Current relay node
     * @returns Decrypted inner onion and next hop ID
     */
    peelOnion(onion: Buffer, node: RelayNode): Promise<{
        nextHopId: string;
        innerOnion: Buffer;
    }>;
    /**
     * Key exchange handshake
     *
     * @param node - Relay node
     * @returns 32-byte symmetric key
     */
    private handshake;
    /**
     * Simulation of Entangled Photon exchange (QKD)
     *
     * In production, this interfaces with quantum hardware drivers.
     * For now, we simulate with deterministic key derivation.
     *
     * @param nodeId - Node identifier
     * @returns 32-byte quantum-derived key
     */
    private simulateQKD;
    /**
     * Deterministic Key Generation based on math constants (π^φ system)
     *
     * Uses transcendental numbers (π, φ) for high-entropy key derivation
     * when quantum channels are unavailable.
     *
     * @param nodeId - Node identifier
     * @returns 32-byte algorithmically-derived key
     */
    private deriveTranscendentalKey;
    /**
     * Verify onion integrity
     *
     * @param onion - Onion packet to verify
     * @returns True if onion structure is valid
     */
    verifyOnionStructure(onion: Buffer): boolean;
}
//# sourceMappingURL=hybrid-crypto.d.ts.map