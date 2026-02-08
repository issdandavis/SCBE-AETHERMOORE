"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ZBase32 = void 0;
/**
 * Z-Base-32 Encoding for Human-Readable Fingerprints
 * Integrates with SCBE-AETHERMOORE output encoding
 */
class ZBase32 {
    static ALPHABET = 'ybndrfg8ejkmcpqxot1uwisza345h769';
    static encode(buffer) {
        let result = '';
        let val = 0;
        let bits = 0;
        for (let i = 0; i < buffer.length; i++) {
            val = (val << 8) | buffer[i];
            bits += 8;
            while (bits >= 5) {
                const index = (val >>> (bits - 5)) & 0x1f;
                result += this.ALPHABET[index];
                bits -= 5;
            }
        }
        if (bits > 0) {
            const index = (val << (5 - bits)) & 0x1f;
            result += this.ALPHABET[index];
        }
        return result;
    }
    static decode(input) {
        const result = [];
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
                const byte = (val >>> (bits - 8)) & 0xff;
                result.push(byte);
                bits -= 8;
            }
        }
        return Buffer.from(result);
    }
}
exports.ZBase32 = ZBase32;
//# sourceMappingURL=ZBase32.js.map