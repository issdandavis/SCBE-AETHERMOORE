"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.float64Array = float64Array;
const double_js_1 = require("./double.js");
const array_js_1 = require("./array.js");
const globals_js_1 = require("../utils/globals.js");
function toTypedMapper(data) {
    return globals_js_1.Float64Array.from(data);
}
function fromTypedUnmapper(value) {
    if (!(value instanceof globals_js_1.Float64Array))
        throw new Error('Unexpected type');
    return [...value];
}
/**@__NO_SIDE_EFFECTS__*/function float64Array(constraints = {}) {
    return (0, array_js_1.array)((0, double_js_1.double)(constraints), constraints).map(toTypedMapper, fromTypedUnmapper);
}
