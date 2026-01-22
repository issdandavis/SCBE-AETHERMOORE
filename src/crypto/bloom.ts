export class BloomFilter {
  private bits: Uint8Array;
  private k: number;
  constructor(sizeBits = 2048, hashes = 4) {
    this.bits = new Uint8Array(sizeBits);
    this.k = hashes;
  }
  private hN(s: string, n: number): number {
    // Simple 32-bit FNV-1a variant with n salt
    let h = 0x811c9dc5 ^ n;
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = (h * 0x01000193) >>> 0;
    }
    return h % (this.bits.length * 8);
  }
  add(s: string) {
    for (let i = 0; i < this.k; i++) {
      const bit = this.hN(s, i);
      const byte = bit >> 3,
        mask = 1 << (bit & 7);
      this.bits[byte] |= mask;
    }
  }
  mightHave(s: string) {
    for (let i = 0; i < this.k; i++) {
      const bit = this.hN(s, i);
      const byte = bit >> 3,
        mask = 1 << (bit & 7);
      if ((this.bits[byte] & mask) === 0) return false;
    }
    return true;
  }
}
