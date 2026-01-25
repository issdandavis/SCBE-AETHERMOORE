"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.double = double;
const DoubleHelpers_js_1 = require("./_internals/helpers/DoubleHelpers.js");
const DoubleOnlyHelpers_js_1 = require("./_internals/helpers/DoubleOnlyHelpers.js");
const bigInt_js_1 = require("./bigInt.js");
const globals_js_1 = require("../utils/globals.js");
const safeNumberIsInteger = Number.isInteger;
const safeNumberIsNaN = Number.isNaN;
const safeNegativeInfinity = Number.NEGATIVE_INFINITY;
const safePositiveInfinity = Number.POSITIVE_INFINITY;
const safeMaxValue = Number.MAX_VALUE;
const safeNaN = Number.NaN;
function safeDoubleToIndex(d, constraintsLabel) {
    if (safeNumberIsNaN(d)) {
        throw new Error('fc.double constraints.' + constraintsLabel + ' must be a 64-bit float');
    }
    return (0, DoubleHelpers_js_1.doubleToIndex)(d);
}
function unmapperDoubleToIndex(value) {
    if (typeof value !== 'number')
        throw new Error('Unsupported type');
    return (0, DoubleHelpers_js_1.doubleToIndex)(value);
}
function numberIsNotInteger(value) {
    return !safeNumberIsInteger(value);
}
function anyDouble(constraints) {
    const { noDefaultInfinity = false, noNaN = false, minExcluded = false, maxExcluded = false, min = noDefaultInfinity ? -safeMaxValue : safeNegativeInfinity, max = noDefaultInfinity ? safeMaxValue : safePositiveInfinity, } = constraints;
    const minIndexRaw = safeDoubleToIndex(min, 'min');
    const minIndex = minExcluded ? minIndexRaw + (0, globals_js_1.BigInt)(1) : minIndexRaw;
    const maxIndexRaw = safeDoubleToIndex(max, 'max');
    const maxIndex = maxExcluded ? maxIndexRaw - (0, globals_js_1.BigInt)(1) : maxIndexRaw;
    if (maxIndex < minIndex) {
        throw new Error('fc.double constraints.min must be smaller or equal to constraints.max');
    }
    if (noNaN) {
        return (0, bigInt_js_1.bigInt)({ min: minIndex, max: maxIndex }).map(DoubleHelpers_js_1.indexToDouble, unmapperDoubleToIndex);
    }
    const positiveMaxIdx = maxIndex > (0, globals_js_1.BigInt)(0);
    const minIndexWithNaN = positiveMaxIdx ? minIndex : minIndex - (0, globals_js_1.BigInt)(1);
    const maxIndexWithNaN = positiveMaxIdx ? maxIndex + (0, globals_js_1.BigInt)(1) : maxIndex;
    return (0, bigInt_js_1.bigInt)({ min: minIndexWithNaN, max: maxIndexWithNaN }).map((index) => {
        if (maxIndex < index || index < minIndex)
            return safeNaN;
        else
            return (0, DoubleHelpers_js_1.indexToDouble)(index);
    }, (value) => {
        if (typeof value !== 'number')
            throw new Error('Unsupported type');
        if (safeNumberIsNaN(value))
            return maxIndex !== maxIndexWithNaN ? maxIndexWithNaN : minIndexWithNaN;
        return (0, DoubleHelpers_js_1.doubleToIndex)(value);
    });
}
/**@__NO_SIDE_EFFECTS__*/function double(constraints = {}) {
    if (!constraints.noInteger) {
        return anyDouble(constraints);
    }
    return anyDouble((0, DoubleOnlyHelpers_js_1.refineConstraintsForDoubleOnly)(constraints))
        .map(DoubleOnlyHelpers_js_1.doubleOnlyMapper, DoubleOnlyHelpers_js_1.doubleOnlyUnmapper)
        .filter(numberIsNotInteger);
}
