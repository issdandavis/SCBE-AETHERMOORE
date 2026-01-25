"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.clone = clone;
const CloneArbitrary_js_1 = require("./_internals/CloneArbitrary.js");
/**@__NO_SIDE_EFFECTS__*/function clone(arb, numValues) {
    return new CloneArbitrary_js_1.CloneArbitrary(arb, numValues);
}
