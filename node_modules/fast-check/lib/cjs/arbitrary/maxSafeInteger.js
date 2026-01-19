"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.maxSafeInteger = maxSafeInteger;
const IntegerArbitrary_js_1 = require("./_internals/IntegerArbitrary.js");
const safeMinSafeInteger = Number.MIN_SAFE_INTEGER;
const safeMaxSafeInteger = Number.MAX_SAFE_INTEGER;
/**@__NO_SIDE_EFFECTS__*/function maxSafeInteger() {
    return new IntegerArbitrary_js_1.IntegerArbitrary(safeMinSafeInteger, safeMaxSafeInteger);
}
