/**
 * src/core/Feistel.ts
 * Balanced Feistel Network for Intent Modulation
 * Integrates with SCBE-AETHERMOORE Layer 0 (Pre-processing)
 */
import * as crypto from 'crypto';

export class Feistel {
  private rounds: number;

  constructor(rounds: number = 6) {
    this.rounds = rounds;
  }

  private roundFunction(right: Buffer, roundKey: Buffer): Buffer {
    const hmac = crypto.createHmac('sha256', roundKey);
    hmac.update(right);
    const digest = hmac.digest();
    
    if (digest.length >= right.length) {
      return digest.subarray(0, right.length);
    } else {
      const repeatCount = Math.ceil(right.length / digest.length);
      return Buffer.alloc(right.length, Buffer.concat(Array(repeatCount).fill(digest)));
    }
  }

  private xorBuffers(a: Buffer, b: Buffer): Buffer {
    const length = Math.min(a.length, b.length);
    const result = Buffer.alloc(length);
    for (let i = 0; i < length; i++) {
      result[i] = a[i] ^ b[i];
    }
    return result;
  }

  encrypt(data: Buffer, key: string): Buffer {
    let workingBuffer = Buffer.from(data);
    if (workingBuffer.length % 2 !== 0) {
      workingBuffer = Buffer.concat([workingBuffer, Buffer.from([0])]);
    }

    const halfLen = workingBuffer.length / 2;
    let left = workingBuffer.subarray(0, halfLen);
    let right = workingBuffer.subarray(halfLen);

    const masterKeyBuf = crypto.createHash('sha256').update(key).digest();

    for (let i = 0; i < this.rounds; i++) {
      const roundKey = crypto.createHmac('sha256', masterKeyBuf)
                            .update(Buffer.from([i]))
                            .digest();
      
      const nextLeft = right;
      const fOutput = this.roundFunction(right, roundKey);
      const nextRight = this.xorBuffers(left, fOutput);

      left = nextLeft;
      right = nextRight;
    }

    return Buffer.concat([left, right]);
  }

  decrypt(data: Buffer, key: string): Buffer {
    const halfLen = data.length / 2;
    let left = data.subarray(0, halfLen);
    let right = data.subarray(halfLen);
    
    const masterKeyBuf = crypto.createHash('sha256').update(key).digest();

    for (let i = this.rounds - 1; i >= 0; i--) {
      const roundKey = crypto.createHmac('sha256', masterKeyBuf)
                            .update(Buffer.from([i]))
                            .digest();
      
      const prevRight = left;
      const fOutput = this.roundFunction(left, roundKey);
      const prevLeft = this.xorBuffers(right, fOutput);

      left = prevLeft;
      right = prevRight;
    }

    return Buffer.concat([left, right]);
  }
}
