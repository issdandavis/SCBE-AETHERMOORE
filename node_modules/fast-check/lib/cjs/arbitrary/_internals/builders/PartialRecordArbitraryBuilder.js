"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildPartialRecordArbitrary = buildPartialRecordArbitrary;
const globals_js_1 = require("../../../utils/globals.js");
const boolean_js_1 = require("../../boolean.js");
const constant_js_1 = require("../../constant.js");
const option_js_1 = require("../../option.js");
const tuple_js_1 = require("../../tuple.js");
const EnumerableKeysExtractor_js_1 = require("../helpers/EnumerableKeysExtractor.js");
const ValuesAndSeparateKeysToObject_js_1 = require("../mappers/ValuesAndSeparateKeysToObject.js");
const noKeyValue = Symbol('no-key');
function buildPartialRecordArbitrary(recordModel, requiredKeys, noNullPrototype) {
    const keys = (0, EnumerableKeysExtractor_js_1.extractEnumerableKeys)(recordModel);
    const arbs = [];
    for (let index = 0; index !== keys.length; ++index) {
        const k = keys[index];
        const requiredArbitrary = recordModel[k];
        if (requiredKeys === undefined || (0, globals_js_1.safeIndexOf)(requiredKeys, k) !== -1) {
            (0, globals_js_1.safePush)(arbs, requiredArbitrary);
        }
        else {
            (0, globals_js_1.safePush)(arbs, (0, option_js_1.option)(requiredArbitrary, { nil: noKeyValue }));
        }
    }
    return (0, tuple_js_1.tuple)((0, tuple_js_1.tuple)(...arbs), noNullPrototype ? (0, constant_js_1.constant)(false) : (0, boolean_js_1.boolean)()).map((0, ValuesAndSeparateKeysToObject_js_1.buildValuesAndSeparateKeysToObjectMapper)(keys, noKeyValue), (0, ValuesAndSeparateKeysToObject_js_1.buildValuesAndSeparateKeysToObjectUnmapper)(keys, noKeyValue));
}
