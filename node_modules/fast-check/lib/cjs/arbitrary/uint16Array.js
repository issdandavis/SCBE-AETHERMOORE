"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.uint16Array = uint16Array;
const globals_js_1 = require("../utils/globals.js");
const integer_js_1 = require("./integer.js");
const TypedIntArrayArbitraryBuilder_js_1 = require("./_internals/builders/TypedIntArrayArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function uint16Array(constraints = {}) {
    return (0, TypedIntArrayArbitraryBuilder_js_1.typedIntArrayArbitraryArbitraryBuilder)(constraints, 0, 65535, globals_js_1.Uint16Array, integer_js_1.integer);
}
