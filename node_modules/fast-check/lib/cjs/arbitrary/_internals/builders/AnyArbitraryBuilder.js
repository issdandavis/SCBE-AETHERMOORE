"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.anyArbitraryBuilder = anyArbitraryBuilder;
const stringify_js_1 = require("../../../utils/stringify.js");
const array_js_1 = require("../../array.js");
const oneof_js_1 = require("../../oneof.js");
const bigInt_js_1 = require("../../bigInt.js");
const date_js_1 = require("../../date.js");
const float32Array_js_1 = require("../../float32Array.js");
const float64Array_js_1 = require("../../float64Array.js");
const int16Array_js_1 = require("../../int16Array.js");
const int32Array_js_1 = require("../../int32Array.js");
const int8Array_js_1 = require("../../int8Array.js");
const uint16Array_js_1 = require("../../uint16Array.js");
const uint32Array_js_1 = require("../../uint32Array.js");
const uint8Array_js_1 = require("../../uint8Array.js");
const uint8ClampedArray_js_1 = require("../../uint8ClampedArray.js");
const sparseArray_js_1 = require("../../sparseArray.js");
const letrec_js_1 = require("../../letrec.js");
const DepthContext_js_1 = require("../helpers/DepthContext.js");
const dictionary_js_1 = require("../../dictionary.js");
const set_js_1 = require("../../set.js");
const map_js_1 = require("../../map.js");
function dictOf(ka, va, maxKeys, size, depthIdentifier, withNullPrototype) {
    return (0, dictionary_js_1.dictionary)(ka, va, {
        maxKeys,
        noNullPrototype: !withNullPrototype,
        size,
        depthIdentifier,
    });
}
function typedArray(constraints) {
    return (0, oneof_js_1.oneof)((0, int8Array_js_1.int8Array)(constraints), (0, uint8Array_js_1.uint8Array)(constraints), (0, uint8ClampedArray_js_1.uint8ClampedArray)(constraints), (0, int16Array_js_1.int16Array)(constraints), (0, uint16Array_js_1.uint16Array)(constraints), (0, int32Array_js_1.int32Array)(constraints), (0, uint32Array_js_1.uint32Array)(constraints), (0, float32Array_js_1.float32Array)(constraints), (0, float64Array_js_1.float64Array)(constraints));
}
function anyArbitraryBuilder(constraints) {
    const arbitrariesForBase = constraints.values;
    const depthSize = constraints.depthSize;
    const depthIdentifier = (0, DepthContext_js_1.createDepthIdentifier)();
    const maxDepth = constraints.maxDepth;
    const maxKeys = constraints.maxKeys;
    const size = constraints.size;
    const baseArb = (0, oneof_js_1.oneof)(...arbitrariesForBase, ...(constraints.withBigInt ? [(0, bigInt_js_1.bigInt)()] : []), ...(constraints.withDate ? [(0, date_js_1.date)()] : []));
    return (0, letrec_js_1.letrec)((tie) => ({
        anything: (0, oneof_js_1.oneof)({ maxDepth, depthSize, depthIdentifier }, baseArb, tie('array'), tie('object'), ...(constraints.withMap ? [tie('map')] : []), ...(constraints.withSet ? [tie('set')] : []), ...(constraints.withObjectString ? [tie('anything').map((o) => (0, stringify_js_1.stringify)(o))] : []), ...(constraints.withTypedArray ? [typedArray({ maxLength: maxKeys, size })] : []), ...(constraints.withSparseArray
            ? [(0, sparseArray_js_1.sparseArray)(tie('anything'), { maxNumElements: maxKeys, size, depthIdentifier })]
            : [])),
        keys: constraints.withObjectString
            ? (0, oneof_js_1.oneof)({ arbitrary: constraints.key, weight: 10 }, { arbitrary: tie('anything').map((o) => (0, stringify_js_1.stringify)(o)), weight: 1 })
            : constraints.key,
        array: (0, array_js_1.array)(tie('anything'), { maxLength: maxKeys, size, depthIdentifier }),
        set: (0, set_js_1.set)(tie('anything'), { maxLength: maxKeys, size, depthIdentifier }),
        map: (0, oneof_js_1.oneof)((0, map_js_1.map)(tie('keys'), tie('anything'), { maxKeys, size, depthIdentifier }), (0, map_js_1.map)(tie('anything'), tie('anything'), { maxKeys, size, depthIdentifier })),
        object: dictOf(tie('keys'), tie('anything'), maxKeys, size, depthIdentifier, constraints.withNullPrototype),
    })).anything;
}
