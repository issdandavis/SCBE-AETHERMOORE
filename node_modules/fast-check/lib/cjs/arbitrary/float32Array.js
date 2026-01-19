"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.float32Array = float32Array;
const float_js_1 = require("./float.js");
const array_js_1 = require("./array.js");
const globals_js_1 = require("../utils/globals.js");
function toTypedMapper(data) {
    return globals_js_1.Float32Array.from(data);
}
function fromTypedUnmapper(value) {
    if (!(value instanceof globals_js_1.Float32Array))
        throw new Error('Unexpected type');
    return [...value];
}
/**@__NO_SIDE_EFFECTS__*/function float32Array(constraints = {}) {
    return (0, array_js_1.array)((0, float_js_1.float)(constraints), constraints).map(toTypedMapper, fromTypedUnmapper);
}
