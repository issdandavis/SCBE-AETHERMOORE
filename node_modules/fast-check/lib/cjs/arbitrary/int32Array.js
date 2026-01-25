"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.int32Array = int32Array;
const globals_js_1 = require("../utils/globals.js");
const integer_js_1 = require("./integer.js");
const TypedIntArrayArbitraryBuilder_js_1 = require("./_internals/builders/TypedIntArrayArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function int32Array(constraints = {}) {
    return (0, TypedIntArrayArbitraryBuilder_js_1.typedIntArrayArbitraryArbitraryBuilder)(constraints, -0x80000000, 0x7fffffff, globals_js_1.Int32Array, integer_js_1.integer);
}
