"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.mixedCase = mixedCase;
const globals_js_1 = require("../utils/globals.js");
const MixedCaseArbitrary_js_1 = require("./_internals/MixedCaseArbitrary.js");
function defaultToggleCase(rawChar) {
    const upper = (0, globals_js_1.safeToUpperCase)(rawChar);
    if (upper !== rawChar)
        return upper;
    return (0, globals_js_1.safeToLowerCase)(rawChar);
}
/**@__NO_SIDE_EFFECTS__*/function mixedCase(stringArb, constraints) {
    const toggleCase = (constraints && constraints.toggleCase) || defaultToggleCase;
    const untoggleAll = constraints && constraints.untoggleAll;
    return new MixedCaseArbitrary_js_1.MixedCaseArbitrary(stringArb, toggleCase, untoggleAll);
}
