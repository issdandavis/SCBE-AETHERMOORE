"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.oneof = oneof;
const Arbitrary_js_1 = require("../check/arbitrary/definition/Arbitrary.js");
const globals_js_1 = require("../utils/globals.js");
const FrequencyArbitrary_js_1 = require("./_internals/FrequencyArbitrary.js");
function isOneOfContraints(param) {
    return (param != null &&
        typeof param === 'object' &&
        !('generate' in param) &&
        !('arbitrary' in param) &&
        !('weight' in param));
}
function toWeightedArbitrary(maybeWeightedArbitrary) {
    if ((0, Arbitrary_js_1.isArbitrary)(maybeWeightedArbitrary)) {
        return { arbitrary: maybeWeightedArbitrary, weight: 1 };
    }
    return maybeWeightedArbitrary;
}
/**@__NO_SIDE_EFFECTS__*/function oneof(...args) {
    const constraints = args[0];
    if (isOneOfContraints(constraints)) {
        const weightedArbs = (0, globals_js_1.safeMap)((0, globals_js_1.safeSlice)(args, 1), toWeightedArbitrary);
        return FrequencyArbitrary_js_1.FrequencyArbitrary.from(weightedArbs, constraints, 'fc.oneof');
    }
    const weightedArbs = (0, globals_js_1.safeMap)(args, toWeightedArbitrary);
    return FrequencyArbitrary_js_1.FrequencyArbitrary.from(weightedArbs, {}, 'fc.oneof');
}
