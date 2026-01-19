"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.compareFunc = compareFunc;
const CompareFunctionArbitraryBuilder_js_1 = require("./_internals/builders/CompareFunctionArbitraryBuilder.js");
const safeObjectAssign = Object.assign;
/**@__NO_SIDE_EFFECTS__*/function compareFunc() {
    return (0, CompareFunctionArbitraryBuilder_js_1.buildCompareFunctionArbitrary)(safeObjectAssign((hA, hB) => hA - hB, {
        toString() {
            return '(hA, hB) => hA - hB';
        },
    }));
}
