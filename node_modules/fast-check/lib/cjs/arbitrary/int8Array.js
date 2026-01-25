"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.int8Array = int8Array;
const globals_js_1 = require("../utils/globals.js");
const integer_js_1 = require("./integer.js");
const TypedIntArrayArbitraryBuilder_js_1 = require("./_internals/builders/TypedIntArrayArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function int8Array(constraints = {}) {
    return (0, TypedIntArrayArbitraryBuilder_js_1.typedIntArrayArbitraryArbitraryBuilder)(constraints, -128, 127, globals_js_1.Int8Array, integer_js_1.integer);
}
