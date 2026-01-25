"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.dictionary = dictionary;
const tuple_js_1 = require("./tuple.js");
const uniqueArray_js_1 = require("./uniqueArray.js");
const KeyValuePairsToObject_js_1 = require("./_internals/mappers/KeyValuePairsToObject.js");
const constant_js_1 = require("./constant.js");
const boolean_js_1 = require("./boolean.js");
function dictionaryKeyExtractor(entry) {
    return entry[0];
}
/**@__NO_SIDE_EFFECTS__*/function dictionary(keyArb, valueArb, constraints = {}) {
    const noNullPrototype = !!constraints.noNullPrototype;
    return (0, tuple_js_1.tuple)((0, uniqueArray_js_1.uniqueArray)((0, tuple_js_1.tuple)(keyArb, valueArb), {
        minLength: constraints.minKeys,
        maxLength: constraints.maxKeys,
        size: constraints.size,
        selector: dictionaryKeyExtractor,
        depthIdentifier: constraints.depthIdentifier,
    }), noNullPrototype ? (0, constant_js_1.constant)(false) : (0, boolean_js_1.boolean)()).map(KeyValuePairsToObject_js_1.keyValuePairsToObjectMapper, KeyValuePairsToObject_js_1.keyValuePairsToObjectUnmapper);
}
