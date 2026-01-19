import { BigInt, Number } from '../../../utils/globals.js';
const safeNegativeInfinity = Number.NEGATIVE_INFINITY;
const safePositiveInfinity = Number.POSITIVE_INFINITY;
const safeEpsilon = Number.EPSILON;
const INDEX_POSITIVE_INFINITY = BigInt(2146435072) * BigInt(4294967296);
const INDEX_NEGATIVE_INFINITY = -INDEX_POSITIVE_INFINITY - BigInt(1);
const num2Pow52 = 0x10000000000000;
const big2Pow52Mask = BigInt(0xfffffffffffff);
const big2Pow53 = BigInt('9007199254740992');
const f64 = new Float64Array(1);
const u32 = new Uint32Array(f64.buffer, f64.byteOffset);
function bitCastDoubleToUInt64(f) {
    f64[0] = f;
    return [u32[1], u32[0]];
}
export function decomposeDouble(d) {
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
        return BigInt(significand * num2Pow52);
    }
    const rescaledSignificand = BigInt((significand - 1) * num2Pow52);
    const exponentOnlyHigh = BigInt(exponent + 1023) << BigInt(52);
    return rescaledSignificand + exponentOnlyHigh;
}
export function doubleToIndex(d) {
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
        return -indexInDoubleFromDecomp(exponent, -significand) - BigInt(1);
    }
}
export function indexToDouble(index) {
    if (index < 0) {
        return -indexToDouble(-index - BigInt(1));
    }
    if (index === INDEX_POSITIVE_INFINITY) {
        return safePositiveInfinity;
    }
    if (index < big2Pow53) {
        return Number(index) * 2 ** -1074;
    }
    const postIndex = index - big2Pow53;
    const exponent = -1021 + Number(postIndex >> BigInt(52));
    const significand = 1 + Number(postIndex & big2Pow52Mask) * safeEpsilon;
    return significand * 2 ** exponent;
}
