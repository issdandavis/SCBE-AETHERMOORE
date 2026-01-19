"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createSlicesForStringLegacy = createSlicesForStringLegacy;
exports.createSlicesForString = createSlicesForString;
const globals_js_1 = require("../../../utils/globals.js");
const PatternsToString_js_1 = require("../mappers/PatternsToString.js");
const MaxLengthFromMinLength_js_1 = require("./MaxLengthFromMinLength.js");
const TokenizeString_js_1 = require("./TokenizeString.js");
const dangerousStrings = [
    '__defineGetter__',
    '__defineSetter__',
    '__lookupGetter__',
    '__lookupSetter__',
    '__proto__',
    'constructor',
    'hasOwnProperty',
    'isPrototypeOf',
    'propertyIsEnumerable',
    'toLocaleString',
    'toString',
    'valueOf',
    'apply',
    'arguments',
    'bind',
    'call',
    'caller',
    'length',
    'name',
    'prototype',
    'key',
    'ref',
];
function computeCandidateStringLegacy(dangerous, charArbitrary, stringSplitter) {
    let candidate;
    try {
        candidate = stringSplitter(dangerous);
    }
    catch {
        return undefined;
    }
    for (const entry of candidate) {
        if (!charArbitrary.canShrinkWithoutContext(entry)) {
            return undefined;
        }
    }
    return candidate;
}
function createSlicesForStringLegacy(charArbitrary, stringSplitter) {
    const slicesForString = [];
    for (const dangerous of dangerousStrings) {
        const candidate = computeCandidateStringLegacy(dangerous, charArbitrary, stringSplitter);
        if (candidate !== undefined) {
            (0, globals_js_1.safePush)(slicesForString, candidate);
        }
    }
    return slicesForString;
}
const slicesPerArbitrary = new WeakMap();
function createSlicesForStringNoConstraints(charArbitrary) {
    const slicesForString = [];
    for (const dangerous of dangerousStrings) {
        const candidate = (0, TokenizeString_js_1.tokenizeString)(charArbitrary, dangerous, 0, MaxLengthFromMinLength_js_1.MaxLengthUpperBound);
        if (candidate !== undefined) {
            (0, globals_js_1.safePush)(slicesForString, candidate);
        }
    }
    return slicesForString;
}
function createSlicesForString(charArbitrary, constraints) {
    let slices = (0, globals_js_1.safeGet)(slicesPerArbitrary, charArbitrary);
    if (slices === undefined) {
        slices = createSlicesForStringNoConstraints(charArbitrary);
        (0, globals_js_1.safeSet)(slicesPerArbitrary, charArbitrary, slices);
    }
    const slicesForConstraints = [];
    for (const slice of slices) {
        if ((0, PatternsToString_js_1.patternsToStringUnmapperIsValidLength)(slice, constraints)) {
            (0, globals_js_1.safePush)(slicesForConstraints, slice);
        }
    }
    return slicesForConstraints;
}
