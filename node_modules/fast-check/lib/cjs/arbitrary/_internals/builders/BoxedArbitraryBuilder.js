"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.boxedArbitraryBuilder = boxedArbitraryBuilder;
const UnboxedToBoxed_js_1 = require("../mappers/UnboxedToBoxed.js");
function boxedArbitraryBuilder(arb) {
    return arb.map(UnboxedToBoxed_js_1.unboxedToBoxedMapper, UnboxedToBoxed_js_1.unboxedToBoxedUnmapper);
}
