import { array } from './array.js';
import { MaxLengthUpperBound } from './_internals/helpers/MaxLengthFromMinLength.js';
import { codePointsToStringMapper, codePointsToStringUnmapper } from './_internals/mappers/CodePointsToString.js';
import { stringToBase64Mapper, stringToBase64Unmapper } from './_internals/mappers/StringToBase64.js';
import { createSlicesForStringLegacy } from './_internals/helpers/SlicesForStringBuilder.js';
import { integer } from './integer.js';
import { Error, safeCharCodeAt } from '../utils/globals.js';
const safeStringFromCharCode = String.fromCharCode;
function base64Mapper(v) {
    if (v < 26)
        return safeStringFromCharCode(v + 65);
    if (v < 52)
        return safeStringFromCharCode(v + 97 - 26);
    if (v < 62)
        return safeStringFromCharCode(v + 48 - 52);
    return v === 62 ? '+' : '/';
}
function base64Unmapper(s) {
    if (typeof s !== 'string' || s.length !== 1) {
        throw new Error('Invalid entry');
    }
    const v = safeCharCodeAt(s, 0);
    if (v >= 65 && v <= 90)
        return v - 65;
    if (v >= 97 && v <= 122)
        return v - 97 + 26;
    if (v >= 48 && v <= 57)
        return v - 48 + 52;
    return v === 43 ? 62 : v === 47 ? 63 : -1;
}
function base64() {
    return integer({ min: 0, max: 63 }).map(base64Mapper, base64Unmapper);
}
/**@__NO_SIDE_EFFECTS__*/function base64String(constraints = {}) {
    const { minLength: unscaledMinLength = 0, maxLength: unscaledMaxLength = MaxLengthUpperBound, size } = constraints;
    const minLength = unscaledMinLength + 3 - ((unscaledMinLength + 3) % 4);
    const maxLength = unscaledMaxLength - (unscaledMaxLength % 4);
    const requestedSize = constraints.maxLength === undefined && size === undefined ? '=' : size;
    if (minLength > maxLength)
        throw new Error('Minimal length should be inferior or equal to maximal length');
    if (minLength % 4 !== 0)
        throw new Error('Minimal length of base64 strings must be a multiple of 4');
    if (maxLength % 4 !== 0)
        throw new Error('Maximal length of base64 strings must be a multiple of 4');
    const charArbitrary = base64();
    const experimentalCustomSlices = createSlicesForStringLegacy(charArbitrary, codePointsToStringUnmapper);
    const enrichedConstraints = {
        minLength,
        maxLength,
        size: requestedSize,
        experimentalCustomSlices,
    };
    return array(charArbitrary, enrichedConstraints)
        .map(codePointsToStringMapper, codePointsToStringUnmapper)
        .map(stringToBase64Mapper, stringToBase64Unmapper);
}
export { base64String };
