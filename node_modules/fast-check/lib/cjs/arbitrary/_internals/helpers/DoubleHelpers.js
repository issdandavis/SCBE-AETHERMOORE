"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.decomposeDouble = decomposeDouble;
exports.doubleToIndex = doubleToIndex;
exports.indexToDouble = indexToDouble;
const globals_js_1 = require("../../../utils/globals.js");
const safeNegativeInfinity = globals_js_1.Number.NEGATIVE_INFINITY;
const safePositiveInfinity = globals_js_1.Number.POSITIVE_INFINITY;
const safeEpsilon = globals_js_1.Number.EPSILON;
const INDEX_POSITIVE_INFINITY = (0, globals_js_1.BigInt)(2146435072) * (0, globals_js_1.BigInt)(4294967296);
const INDEX_NEGATIVE_INFINITY = -INDEX_POSITIVE_INFINITY - (0, globals_js_1.BigInt)(1);
const num2Pow52 = 0x10000000000000;
const big2Pow52Mask = (0, globals_js_1.BigInt)(0xfffffffffffff);
const big2Pow53 = (0, globals_js_1.BigInt)('9007199254740992');
const f64 = new Float64Array(1);
const u32 = new Uint32Array(f64.buffer, f64.byteOffset);
function bitCastDoubleToUInt64(f) {
    f64[0] = f;
    return [u32[1], u32[0]];
}
function decomposeDouble(d) {
    const { 0: hi, 1: lo } = bitCastDoubleToUInt64(d);
    const signBit = hi >>> 31;
    const exponentBits = (hi >>> 20) & 0x7ff;
    const significandBits = (hi & 0xfffff) * 0x100000000 + lo;
    const exponent = exponentBits === 0 ? -1022 : exponentBits - 1023;
    let significand = exponentBits === 0 ? 0 : 1;
    significand += significandBits * safeEpsilon;
    significand *= signBit === 0 ? 1 : -1;
    return { exponent, significand };
}
function indexInDoubleFromDecomp(exponent, significand) {
    if (exponent === -1022) {
        return (0, globals_js_1.BigInt)(significand * num2Pow52);
    }
    const rescaledSignificand = (0, globals_js_1.BigInt)((significand - 1) * num2Pow52);
    const exponentOnlyHigh = (0, globals_js_1.BigInt)(exponent + 1023) << (0, globals_js_1.BigInt)(52);
    return rescaledSignificand + exponentOnlyHigh;
}
function doubleToIndex(d) {
    if (d === safePositiveInfinity) {
        return INDEX_POSITIVE_INFINITY;
    }
    if (d === safeNegativeInfinity) {
        return INDEX_NEGATIVE_INFINITY;
    }
    const decomp = decomposeDouble(d);
    const exponent = decomp.exponent;
    const significand = decomp.significand;
    if (d > 0 || (d === 0 && 1 / d === safePositiveInfinity)) {
        return indexInDoubleFromDecomp(exponent, significand);
    }
    else {
        return -indexInDoubleFromDecomp(exponent, -significand) - (0, globals_js_1.BigInt)(1);
    }
}
function indexToDouble(index) {
    if (index < 0) {
        return -indexToDouble(-index - (0, globals_js_1.BigInt)(1));
    }
    if (index === INDEX_POSITIVE_INFINITY) {
        return safePositiveInfinity;
    }
    if (index < big2Pow53) {
        return (0, globals_js_1.Number)(index) * 2 ** -1074;
    }
    const postIndex = index - big2Pow53;
    const exponent = -1021 + (0, globals_js_1.Number)(postIndex >> (0, globals_js_1.BigInt)(52));
    const significand = 1 + (0, globals_js_1.Number)(postIndex & big2Pow52Mask) * safeEpsilon;
    return significand * 2 ** exponent;
}
