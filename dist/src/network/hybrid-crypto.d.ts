/**
 * Hybrid Space Crypto
 *
 * Quantum-resistant cryptography for space communications.
 * Implements onion routing encryption with hybrid classical/post-quantum schemes.
 */
import { RelayNode } from './space-tor-router.js';
export interface OnionLayer {
    nodeId: string;
    encryptedPayload: Buffer;
    mac: Buffer;
}
export interface KeyPair {
    publicKey: Buffer;
    privateKey: Buffer;
}
export declare class HybridSpaceCrypto {
    private readonly algorithm;
    private readonly keyLength;
    private readonly ivLength;
    private readonly tagLength;
    /**
     * Build onion-encrypted packet for path traversal
     *
     * @param payload - Original payload to encrypt
     * @param path - Array of relay nodes in path order
     * @returns Encrypted onion packet
     */
    buildOnion(payload: Buffer, path: RelayNode[]): Promise<Buffer>;
    /**
     * Peel one layer of onion encryption
     *
     * @param packet - Encrypted onion packet
     * @param nodeId - Current node's ID
     * @returns Decrypted inner packet and next hop
     */
    peelOnion(packet: Buffer, nodeId: string): Promise<{
        payload: Buffer;
        nextHop: string;
        timestamp: number;
    }>;
    /**
     * Derive node-specific key (simplified - production would use proper KDF)
     */
    private deriveNodeKey;
    /**
     * Generate ephemeral key pair (for future ML-KEM integration)
     */
    generateKeyPair(): KeyPair;
    /**
     * Create MAC for packet integrity
     */
    createMAC(data: Buffer, key: Buffer): Buffer;
    /**
     * Verify MAC
     */
    verifyMAC(data: Buffer, mac: Buffer, key: Buffer): boolean;
}
//# sourceMappingURL=hybrid-crypto.d.ts.map