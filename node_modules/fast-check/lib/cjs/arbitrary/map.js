"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.map = map;
const tuple_js_1 = require("./tuple.js");
const uniqueArray_js_1 = require("./uniqueArray.js");
const ArrayToMap_js_1 = require("./_internals/mappers/ArrayToMap.js");
function mapKeyExtractor(entry) {
    return entry[0];
}
/**@__NO_SIDE_EFFECTS__*/function map(keyArb, valueArb, constraints = {}) {
    return (0, uniqueArray_js_1.uniqueArray)((0, tuple_js_1.tuple)(keyArb, valueArb), {
        minLength: constraints.minKeys,
        maxLength: constraints.maxKeys,
        size: constraints.size,
        selector: mapKeyExtractor,
        depthIdentifier: constraints.depthIdentifier,
        comparator: 'SameValueZero',
    }).map(ArrayToMap_js_1.arrayToMapMapper, ArrayToMap_js_1.arrayToMapUnmapper);
}
