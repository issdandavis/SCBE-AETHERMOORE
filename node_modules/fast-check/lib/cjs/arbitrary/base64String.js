"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.base64String = base64String;
const array_js_1 = require("./array.js");
const MaxLengthFromMinLength_js_1 = require("./_internals/helpers/MaxLengthFromMinLength.js");
const CodePointsToString_js_1 = require("./_internals/mappers/CodePointsToString.js");
const StringToBase64_js_1 = require("./_internals/mappers/StringToBase64.js");
const SlicesForStringBuilder_js_1 = require("./_internals/helpers/SlicesForStringBuilder.js");
const integer_js_1 = require("./integer.js");
const globals_js_1 = require("../utils/globals.js");
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
        throw new globals_js_1.Error('Invalid entry');
    }
    const v = (0, globals_js_1.safeCharCodeAt)(s, 0);
    if (v >= 65 && v <= 90)
        return v - 65;
    if (v >= 97 && v <= 122)
        return v - 97 + 26;
    if (v >= 48 && v <= 57)
        return v - 48 + 52;
    return v === 43 ? 62 : v === 47 ? 63 : -1;
}
function base64() {
    return (0, integer_js_1.integer)({ min: 0, max: 63 }).map(base64Mapper, base64Unmapper);
}
/**@__NO_SIDE_EFFECTS__*/function base64String(constraints = {}) {
    const { minLength: unscaledMinLength = 0, maxLength: unscaledMaxLength = MaxLengthFromMinLength_js_1.MaxLengthUpperBound, size } = constraints;
    const minLength = unscaledMinLength + 3 - ((unscaledMinLength + 3) % 4);
    const maxLength = unscaledMaxLength - (unscaledMaxLength % 4);
    const requestedSize = constraints.maxLength === undefined && size === undefined ? '=' : size;
    if (minLength > maxLength)
        throw new globals_js_1.Error('Minimal length should be inferior or equal to maximal length');
    if (minLength % 4 !== 0)
        throw new globals_js_1.Error('Minimal length of base64 strings must be a multiple of 4');
    if (maxLength % 4 !== 0)
        throw new globals_js_1.Error('Maximal length of base64 strings must be a multiple of 4');
    const charArbitrary = base64();
    const experimentalCustomSlices = (0, SlicesForStringBuilder_js_1.createSlicesForStringLegacy)(charArbitrary, CodePointsToString_js_1.codePointsToStringUnmapper);
    const enrichedConstraints = {
        minLength,
        maxLength,
        size: requestedSize,
        experimentalCustomSlices,
    };
    return (0, array_js_1.array)(charArbitrary, enrichedConstraints)
        .map(CodePointsToString_js_1.codePointsToStringMapper, CodePointsToString_js_1.codePointsToStringUnmapper)
        .map(StringToBase64_js_1.stringToBase64Mapper, StringToBase64_js_1.stringToBase64Unmapper);
}
