"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.maxSafeNat = maxSafeNat;
const IntegerArbitrary_js_1 = require("./_internals/IntegerArbitrary.js");
const safeMaxSafeInteger = Number.MAX_SAFE_INTEGER;
/**@__NO_SIDE_EFFECTS__*/function maxSafeNat() {
    return new IntegerArbitrary_js_1.IntegerArbitrary(0, safeMaxSafeInteger);
}
