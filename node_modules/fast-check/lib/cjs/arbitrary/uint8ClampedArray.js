"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.uint8ClampedArray = uint8ClampedArray;
const globals_js_1 = require("../utils/globals.js");
const integer_js_1 = require("./integer.js");
const TypedIntArrayArbitraryBuilder_js_1 = require("./_internals/builders/TypedIntArrayArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function uint8ClampedArray(constraints = {}) {
    return (0, TypedIntArrayArbitraryBuilder_js_1.typedIntArrayArbitraryArbitraryBuilder)(constraints, 0, 255, globals_js_1.Uint8ClampedArray, integer_js_1.integer);
}
