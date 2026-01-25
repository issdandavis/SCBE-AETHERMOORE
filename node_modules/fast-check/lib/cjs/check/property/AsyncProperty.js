"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.asyncProperty = asyncProperty;
const Arbitrary_js_1 = require("../arbitrary/definition/Arbitrary.js");
const tuple_js_1 = require("../../arbitrary/tuple.js");
const AsyncProperty_generic_js_1 = require("./AsyncProperty.generic.js");
const AlwaysShrinkableArbitrary_js_1 = require("../../arbitrary/_internals/AlwaysShrinkableArbitrary.js");
const globals_js_1 = require("../../utils/globals.js");
function asyncProperty(...args) {
    if (args.length < 2) {
        throw new Error('asyncProperty expects at least two parameters');
    }
    const arbs = (0, globals_js_1.safeSlice)(args, 0, args.length - 1);
    const p = args[args.length - 1];
    (0, globals_js_1.safeForEach)(arbs, Arbitrary_js_1.assertIsArbitrary);
    const mappedArbs = (0, globals_js_1.safeMap)(arbs, (arb) => new AlwaysShrinkableArbitrary_js_1.AlwaysShrinkableArbitrary(arb));
    return new AsyncProperty_generic_js_1.AsyncProperty((0, tuple_js_1.tuple)(...mappedArbs), (t) => p(...t));
}
