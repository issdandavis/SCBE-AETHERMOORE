import { doubleToIndex, indexToDouble } from './_internals/helpers/DoubleHelpers.js';
import { doubleOnlyMapper, doubleOnlyUnmapper, refineConstraintsForDoubleOnly, } from './_internals/helpers/DoubleOnlyHelpers.js';
import { bigInt } from './bigInt.js';
import { BigInt } from '../utils/globals.js';
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
    return doubleToIndex(d);
}
function unmapperDoubleToIndex(value) {
    if (typeof value !== 'number')
        throw new Error('Unsupported type');
    return doubleToIndex(value);
}
function numberIsNotInteger(value) {
    return !safeNumberIsInteger(value);
}
function anyDouble(constraints) {
    const { noDefaultInfinity = false, noNaN = false, minExcluded = false, maxExcluded = false, min = noDefaultInfinity ? -safeMaxValue : safeNegativeInfinity, max = noDefaultInfinity ? safeMaxValue : safePositiveInfinity, } = constraints;
    const minIndexRaw = safeDoubleToIndex(min, 'min');
    const minIndex = minExcluded ? minIndexRaw + BigInt(1) : minIndexRaw;
    const maxIndexRaw = safeDoubleToIndex(max, 'max');
    const maxIndex = maxExcluded ? maxIndexRaw - BigInt(1) : maxIndexRaw;
    if (maxIndex < minIndex) {
        throw new Error('fc.double constraints.min must be smaller or equal to constraints.max');
    }
    if (noNaN) {
        return bigInt({ min: minIndex, max: maxIndex }).map(indexToDouble, unmapperDoubleToIndex);
    }
    const positiveMaxIdx = maxIndex > BigInt(0);
    const minIndexWithNaN = positiveMaxIdx ? minIndex : minIndex - BigInt(1);
    const maxIndexWithNaN = positiveMaxIdx ? maxIndex + BigInt(1) : maxIndex;
    return bigInt({ min: minIndexWithNaN, max: maxIndexWithNaN }).map((index) => {
        if (maxIndex < index || index < minIndex)
            return safeNaN;
        else
            return indexToDouble(index);
    }, (value) => {
        if (typeof value !== 'number')
            throw new Error('Unsupported type');
        if (safeNumberIsNaN(value))
            return maxIndex !== maxIndexWithNaN ? maxIndexWithNaN : minIndexWithNaN;
        return doubleToIndex(value);
    });
}
export /**@__NO_SIDE_EFFECTS__*/function double(constraints = {}) {
    if (!constraints.noInteger) {
        return anyDouble(constraints);
    }
    return anyDouble(refineConstraintsForDoubleOnly(constraints))
        .map(doubleOnlyMapper, doubleOnlyUnmapper)
        .filter(numberIsNotInteger);
}
