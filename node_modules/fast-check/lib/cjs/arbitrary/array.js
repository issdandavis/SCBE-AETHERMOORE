"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.array = array;
const ArrayArbitrary_js_1 = require("./_internals/ArrayArbitrary.js");
const MaxLengthFromMinLength_js_1 = require("./_internals/helpers/MaxLengthFromMinLength.js");
/**@__NO_SIDE_EFFECTS__*/function array(arb, constraints = {}) {
    const size = constraints.size;
    const minLength = constraints.minLength || 0;
    const maxLengthOrUnset = constraints.maxLength;
    const depthIdentifier = constraints.depthIdentifier;
    const maxLength = maxLengthOrUnset !== undefined ? maxLengthOrUnset : MaxLengthFromMinLength_js_1.MaxLengthUpperBound;
    const specifiedMaxLength = maxLengthOrUnset !== undefined;
    const maxGeneratedLength = (0, MaxLengthFromMinLength_js_1.maxGeneratedLengthFromSizeForArbitrary)(size, minLength, maxLength, specifiedMaxLength);
    const customSlices = constraints.experimentalCustomSlices || [];
    return new ArrayArbitrary_js_1.ArrayArbitrary(arb, minLength, maxGeneratedLength, maxLength, depthIdentifier, undefined, customSlices);
}
