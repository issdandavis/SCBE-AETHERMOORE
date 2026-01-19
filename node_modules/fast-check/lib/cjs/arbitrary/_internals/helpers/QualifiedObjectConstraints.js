"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.toQualifiedObjectConstraints = toQualifiedObjectConstraints;
const boolean_js_1 = require("../../boolean.js");
const constant_js_1 = require("../../constant.js");
const double_js_1 = require("../../double.js");
const maxSafeInteger_js_1 = require("../../maxSafeInteger.js");
const oneof_js_1 = require("../../oneof.js");
const string_js_1 = require("../../string.js");
const BoxedArbitraryBuilder_js_1 = require("../builders/BoxedArbitraryBuilder.js");
function defaultValues(constraints, stringArbitrary) {
    return [
        (0, boolean_js_1.boolean)(),
        (0, maxSafeInteger_js_1.maxSafeInteger)(),
        (0, double_js_1.double)(),
        stringArbitrary(constraints),
        (0, oneof_js_1.oneof)(stringArbitrary(constraints), (0, constant_js_1.constant)(null), (0, constant_js_1.constant)(undefined)),
    ];
}
function boxArbitraries(arbs) {
    return arbs.map((arb) => (0, BoxedArbitraryBuilder_js_1.boxedArbitraryBuilder)(arb));
}
function boxArbitrariesIfNeeded(arbs, boxEnabled) {
    return boxEnabled ? boxArbitraries(arbs).concat(arbs) : arbs;
}
function toQualifiedObjectConstraints(settings = {}) {
    const valueConstraints = {
        size: settings.size,
        unit: 'stringUnit' in settings ? settings.stringUnit : settings.withUnicodeString ? 'binary' : undefined,
    };
    return {
        key: settings.key !== undefined ? settings.key : (0, string_js_1.string)(valueConstraints),
        values: boxArbitrariesIfNeeded(settings.values !== undefined ? settings.values : defaultValues(valueConstraints, string_js_1.string), settings.withBoxedValues === true),
        depthSize: settings.depthSize,
        maxDepth: settings.maxDepth,
        maxKeys: settings.maxKeys,
        size: settings.size,
        withSet: settings.withSet === true,
        withMap: settings.withMap === true,
        withObjectString: settings.withObjectString === true,
        withNullPrototype: settings.withNullPrototype === true,
        withBigInt: settings.withBigInt === true,
        withDate: settings.withDate === true,
        withTypedArray: settings.withTypedArray === true,
        withSparseArray: settings.withSparseArray === true,
    };
}
