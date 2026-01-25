"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.set = set;
const uniqueArray_js_1 = require("./uniqueArray.js");
const ArrayToSet_js_1 = require("./_internals/mappers/ArrayToSet.js");
/**@__NO_SIDE_EFFECTS__*/function set(arb, constraints = {}) {
    return (0, uniqueArray_js_1.uniqueArray)(arb, {
        minLength: constraints.minLength,
        maxLength: constraints.maxLength,
        size: constraints.size,
        depthIdentifier: constraints.depthIdentifier,
        comparator: 'SameValueZero',
    }).map(ArrayToSet_js_1.arrayToSetMapper, ArrayToSet_js_1.arrayToSetUnmapper);
}
