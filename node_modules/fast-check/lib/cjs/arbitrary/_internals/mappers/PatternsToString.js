"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.patternsToStringMapper = patternsToStringMapper;
exports.patternsToStringUnmapperIsValidLength = patternsToStringUnmapperIsValidLength;
exports.patternsToStringUnmapperFor = patternsToStringUnmapperFor;
const MaxLengthFromMinLength_js_1 = require("../helpers/MaxLengthFromMinLength.js");
const globals_js_1 = require("../../../utils/globals.js");
const TokenizeString_js_1 = require("../helpers/TokenizeString.js");
function patternsToStringMapper(tab) {
    return (0, globals_js_1.safeJoin)(tab, '');
}
function minLengthFrom(constraints) {
    return constraints.minLength !== undefined ? constraints.minLength : 0;
}
function maxLengthFrom(constraints) {
    return constraints.maxLength !== undefined ? constraints.maxLength : MaxLengthFromMinLength_js_1.MaxLengthUpperBound;
}
function patternsToStringUnmapperIsValidLength(tokens, constraints) {
    return minLengthFrom(constraints) <= tokens.length && tokens.length <= maxLengthFrom(constraints);
}
function patternsToStringUnmapperFor(patternsArb, constraints) {
    return function patternsToStringUnmapper(value) {
        if (typeof value !== 'string') {
            throw new globals_js_1.Error('Unsupported value');
        }
        const tokens = (0, TokenizeString_js_1.tokenizeString)(patternsArb, value, minLengthFrom(constraints), maxLengthFrom(constraints));
        if (tokens === undefined) {
            throw new globals_js_1.Error('Unable to unmap received string');
        }
        return tokens;
    };
}
