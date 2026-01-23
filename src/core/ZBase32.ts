/**
 * Z-Base-32 Encoding for Human-Readable Fingerprints
 * Integrates with SCBE-AETHERMOORE output encoding
 */
export class ZBase32 {
  private static readonly ALPHABET = "ybndrfg8ejkmcpqxot1uwisza345h769";
  
  static encode(buffer: Buffer): string {
    let result = '';
    let val = 0;
    let bits = 0;

    for (let i = 0; i < buffer.length; i++) {
      val = (val << 8) | buffer[i];
      bits += 8;

      while (bits >= 5) {
        const index = (val >>> (bits - 5)) & 0x1F;
        result += this.ALPHABET[index];
        bits -= 5;
      }
    }

    if (bits > 0) {
      const index = (val << (5 - bits)) & 0x1F;
      result += this.ALPHABET[index];
    }

    return result;
  }

  static decode(input: string): Buffer {
    const result: number[] = [];
    let val = 0;
    let bits = 0;

    for (let i = 0; i < input.length; i++) {
      const char = input[i];
      const index = this.ALPHABET.indexOf(char);
      if (index === -1) {
        throw new Error(`Invalid Z-Base-32 character: ${char}`);
      }

      val = (val << 5) | index;
      bits += 5;

      while (bits >= 8) {
        const byte = (val >>> (bits - 8)) & 0xFF;
        result.push(byte);
        bits -= 8;
      }
    }
    
    return Buffer.from(result);
  }
}
