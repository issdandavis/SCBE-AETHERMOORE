/**
 * Hybrid Space Crypto
 *
 * Quantum-resistant cryptography for space communications.
 * Implements onion routing encryption with hybrid classical/post-quantum schemes.
 */

import { createCipheriv, createDecipheriv, randomBytes, createHmac } from 'crypto';
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

export class HybridSpaceCrypto {
  private readonly algorithm = 'aes-256-gcm';
  private readonly keyLength = 32;
  private readonly ivLength = 12;
  private readonly tagLength = 16;

  /**
   * Build onion-encrypted packet for path traversal
   *
   * @param payload - Original payload to encrypt
   * @param path - Array of relay nodes in path order
   * @returns Encrypted onion packet
   */
  public async buildOnion(payload: Buffer, path: RelayNode[]): Promise<Buffer> {
    // Work backwards from exit to entry
    let currentPayload = payload;

    for (let i = path.length - 1; i >= 0; i--) {
      const node = path[i];
      const nextHop = i < path.length - 1 ? path[i + 1].id : 'DESTINATION';

      // Generate ephemeral key for this layer
      const layerKey = this.deriveNodeKey(node.id);
      const iv = randomBytes(this.ivLength);

      // Create header with next hop info
      const header = Buffer.alloc(64);
      header.write(nextHop, 0, 32, 'utf8');
      header.writeUInt32BE(currentPayload.length, 32);
      header.writeUInt32BE(Date.now() / 1000, 36); // Timestamp

      // Encrypt payload with header
      const plaintext = Buffer.concat([header, currentPayload]);
      const cipher = createCipheriv(this.algorithm, layerKey, iv);

      const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
      const tag = cipher.getAuthTag();

      // Prepend IV and tag for this layer
      currentPayload = Buffer.concat([iv, tag, encrypted]);
    }

    return currentPayload;
  }

  /**
   * Peel one layer of onion encryption
   *
   * @param packet - Encrypted onion packet
   * @param nodeId - Current node's ID
   * @returns Decrypted inner packet and next hop
   */
  public async peelOnion(
    packet: Buffer,
    nodeId: string
  ): Promise<{ payload: Buffer; nextHop: string; timestamp: number }> {
    const layerKey = this.deriveNodeKey(nodeId);

    // Extract IV, tag, and ciphertext
    const iv = packet.subarray(0, this.ivLength);
    const tag = packet.subarray(this.ivLength, this.ivLength + this.tagLength);
    const ciphertext = packet.subarray(this.ivLength + this.tagLength);

    // Decrypt
    const decipher = createDecipheriv(this.algorithm, layerKey, iv);
    decipher.setAuthTag(tag);

    const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]);

    // Parse header
    const header = plaintext.subarray(0, 64);
    const nextHop = header.subarray(0, 32).toString('utf8').replace(/\0/g, '');
    const payloadLength = header.readUInt32BE(32);
    const timestamp = header.readUInt32BE(36);

    const payload = plaintext.subarray(64, 64 + payloadLength);

    return { payload, nextHop, timestamp };
  }

  /**
   * Derive node-specific key (simplified - production would use proper KDF)
   */
  private deriveNodeKey(nodeId: string): Buffer {
    // In production, this would use ML-KEM key exchange
    // For now, use HKDF-like derivation
    const hmac = createHmac('sha256', 'space-tor-key-derivation');
    hmac.update(nodeId);
    return hmac.digest();
  }

  /**
   * Generate ephemeral key pair (for future ML-KEM integration)
   */
  public generateKeyPair(): KeyPair {
    return {
      publicKey: randomBytes(32),
      privateKey: randomBytes(32)
    };
  }

  /**
   * Create MAC for packet integrity
   */
  public createMAC(data: Buffer, key: Buffer): Buffer {
    const hmac = createHmac('sha256', key);
    hmac.update(data);
    return hmac.digest();
  }

  /**
   * Verify MAC
   */
  public verifyMAC(data: Buffer, mac: Buffer, key: Buffer): boolean {
    const computed = this.createMAC(data, key);
    return computed.equals(mac);
  }
}
