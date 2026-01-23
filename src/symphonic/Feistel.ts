/**
 * SCBE Symphonic Cipher - Feistel Network
 *
 * Implementation of a Balanced Feistel Network for "Intent Modulation".
 * Scrambles input data into a pseudo-random signal while maintaining
 * reversibility (decryptability).
 *
 * The Feistel structure allows using a non-invertible round function (HMAC)
 * while still enabling full decryption. This is used to create high-entropy
 * signals from structured data (like JSON) before FFT analysis.
 *
 * @module symphonic/Feistel
 */

import { createHmac, createHash, randomBytes } from 'crypto';

/**
 * Feistel Network configuration
 */
export interface FeistelConfig {
  /** Number of rounds (default 6) */
  rounds: number;
  /** Hash algorithm for round function (default 'sha256') */
  hashAlgorithm: 'sha256' | 'sha512' | 'sha384';
}

const DEFAULT_CONFIG: FeistelConfig = {
  rounds: 6,
  hashAlgorithm: 'sha256',
};

/**
 * Balanced Feistel Network implementation
 */
export class Feistel {
  private readonly config: FeistelConfig;

  /**
   * Creates a new Feistel cipher.
   *
   * @param config Configuration options
   */
  constructor(config: Partial<FeistelConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };

    if (this.config.rounds < 2) {
      throw new Error('Feistel network requires at least 2 rounds');
    }
  }

  /**
   * The Round Function F.
   * F(R, K) = HMAC-SHA256(Key, R)
   *
   * The output is truncated or extended to match the length of the block half.
   *
   * @param right Right half of the block
   * @param roundKey Round-specific key
   * @returns Transformed output matching right's length
   */
  private roundFunction(right: Uint8Array, roundKey: Uint8Array): Uint8Array {
    const hmac = createHmac(this.config.hashAlgorithm, roundKey);
    hmac.update(right);
    const digest = hmac.digest();

    if (digest.length >= right.length) {
      // Truncate if digest is larger
      return new Uint8Array(digest.subarray(0, right.length));
    } else {
      // Extend by repeating digest if block is larger than hash output
      const result = new Uint8Array(right.length);
      let offset = 0;
      while (offset < right.length) {
        const copyLen = Math.min(digest.length, right.length - offset);
        result.set(digest.subarray(0, copyLen), offset);
        offset += copyLen;
      }
      return result;
    }
  }

  /**
   * XORs two buffers together.
   *
   * @param a First buffer
   * @param b Second buffer
   * @returns XOR result
   */
  private xorBuffers(a: Uint8Array, b: Uint8Array): Uint8Array {
    const length = Math.min(a.length, b.length);
    const result = new Uint8Array(length);
    for (let i = 0; i < length; i++) {
      result[i] = a[i] ^ b[i];
    }
    return result;
  }

  /**
   * Derives round keys from the master key.
   *
   * @param masterKey Master key buffer
   * @returns Array of round keys
   */
  private deriveRoundKeys(masterKey: Uint8Array): Uint8Array[] {
    const keys: Uint8Array[] = [];

    // Hash the master key for uniform distribution
    const masterHash = createHash(this.config.hashAlgorithm).update(masterKey).digest();

    for (let i = 0; i < this.config.rounds; i++) {
      // K_i = HMAC(Master, Round_Index)
      const hmac = createHmac(this.config.hashAlgorithm, masterHash);
      hmac.update(new Uint8Array([i]));
      keys.push(new Uint8Array(hmac.digest()));
    }

    return keys;
  }

  /**
   * Encrypts (modulates) the data buffer.
   *
   * @param data Raw input data
   * @param key Master key (string or buffer)
   * @returns Encrypted/modulated data
   */
  encrypt(data: Uint8Array, key: string | Uint8Array): Uint8Array {
    const keyBuffer = typeof key === 'string' ? new TextEncoder().encode(key) : key;

    // Ensure even length by padding if necessary
    let workingData = data;
    const needsPadding = data.length % 2 !== 0;
    if (needsPadding) {
      workingData = new Uint8Array(data.length + 1);
      workingData.set(data);
      workingData[data.length] = 0;
    }

    const halfLen = workingData.length / 2;
    let left: Uint8Array = workingData.slice(0, halfLen);
    let right: Uint8Array = workingData.slice(halfLen);

    const roundKeys = this.deriveRoundKeys(keyBuffer);

    // Feistel rounds
    for (let i = 0; i < this.config.rounds; i++) {
      const nextLeft = right; // L_{i+1} = R_i
      const fOutput = this.roundFunction(right, roundKeys[i]);
      const nextRight = this.xorBuffers(left, fOutput); // R_{i+1} = L_i XOR F(R_i, K_i)

      left = nextLeft;
      right = nextRight;
    }

    // Combine halves
    const result = new Uint8Array(workingData.length);
    result.set(left, 0);
    result.set(right, halfLen);

    return result;
  }

  /**
   * Decrypts (demodulates) the data buffer.
   *
   * @param data Encrypted data
   * @param key Master key (string or buffer)
   * @returns Decrypted data
   */
  decrypt(data: Uint8Array, key: string | Uint8Array): Uint8Array {
    const keyBuffer = typeof key === 'string' ? new TextEncoder().encode(key) : key;

    const halfLen = data.length / 2;
    let left: Uint8Array = data.slice(0, halfLen);
    let right: Uint8Array = data.slice(halfLen);

    const roundKeys = this.deriveRoundKeys(keyBuffer);

    // Feistel decryption: same rounds but in reverse order
    for (let i = this.config.rounds - 1; i >= 0; i--) {
      const prevRight = left; // R_i = L_{i+1}
      const fOutput = this.roundFunction(left, roundKeys[i]);
      const prevLeft = this.xorBuffers(right, fOutput); // L_i = R_{i+1} XOR F(L_{i+1}, K_i)

      left = prevLeft;
      right = prevRight;
    }

    // Combine halves
    const result = new Uint8Array(data.length);
    result.set(left, 0);
    result.set(right, halfLen);

    return result;
  }

  /**
   * Encrypts a string and returns the result as a Uint8Array.
   *
   * @param plaintext String to encrypt
   * @param key Encryption key
   * @returns Encrypted bytes
   */
  encryptString(plaintext: string, key: string): Uint8Array {
    const data = new TextEncoder().encode(plaintext);
    return this.encrypt(data, key);
  }

  /**
   * Decrypts bytes and returns the result as a string.
   *
   * @param ciphertext Encrypted bytes
   * @param key Decryption key
   * @returns Decrypted string
   */
  decryptString(ciphertext: Uint8Array, key: string): string {
    const decrypted = this.decrypt(ciphertext, key);
    // Remove padding null bytes from end
    let end = decrypted.length;
    while (end > 0 && decrypted[end - 1] === 0) {
      end--;
    }
    return new TextDecoder().decode(decrypted.subarray(0, end));
  }

  /**
   * Generates a random key of specified length.
   *
   * @param length Key length in bytes (default 32)
   * @returns Random key buffer
   */
  static generateKey(length: number = 32): Uint8Array {
    return new Uint8Array(randomBytes(length));
  }

  /**
   * Verifies that encryption/decryption round-trips correctly.
   *
   * @param data Test data
   * @param key Test key
   * @returns True if round-trip succeeds
   */
  verify(data: Uint8Array, key: string | Uint8Array): boolean {
    const encrypted = this.encrypt(data, key);
    const decrypted = this.decrypt(encrypted, key);

    // Compare (accounting for potential padding)
    const minLen = Math.min(data.length, decrypted.length);
    for (let i = 0; i < minLen; i++) {
      if (data[i] !== decrypted[i]) return false;
    }

    // Check padding bytes are zero
    for (let i = minLen; i < decrypted.length; i++) {
      if (decrypted[i] !== 0) return false;
    }

    return true;
  }
}

/**
 * Creates a Feistel cipher with default settings.
 */
export function createFeistel(config?: Partial<FeistelConfig>): Feistel {
  return new Feistel(config);
}
