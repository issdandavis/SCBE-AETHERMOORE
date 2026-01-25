"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.shuffledSubarray = shuffledSubarray;
const SubarrayArbitrary_js_1 = require("./_internals/SubarrayArbitrary.js");
/**@__NO_SIDE_EFFECTS__*/function shuffledSubarray(originalArray, constraints = {}) {
    const { minLength = 0, maxLength = originalArray.length } = constraints;
    return new SubarrayArbitrary_js_1.SubarrayArbitrary(originalArray, false, minLength, maxLength);
}
