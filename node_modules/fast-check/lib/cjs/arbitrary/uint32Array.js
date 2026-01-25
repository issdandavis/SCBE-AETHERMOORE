"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.uint32Array = uint32Array;
const globals_js_1 = require("../utils/globals.js");
const integer_js_1 = require("./integer.js");
const TypedIntArrayArbitraryBuilder_js_1 = require("./_internals/builders/TypedIntArrayArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function uint32Array(constraints = {}) {
    return (0, TypedIntArrayArbitraryBuilder_js_1.typedIntArrayArbitraryArbitraryBuilder)(constraints, 0, 0xffffffff, globals_js_1.Uint32Array, integer_js_1.integer);
}
