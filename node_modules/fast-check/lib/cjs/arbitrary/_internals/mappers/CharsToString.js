"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.charsToStringMapper = charsToStringMapper;
exports.charsToStringUnmapper = charsToStringUnmapper;
const globals_js_1 = require("../../../utils/globals.js");
function charsToStringMapper(tab) {
    return (0, globals_js_1.safeJoin)(tab, '');
}
function charsToStringUnmapper(value) {
    if (typeof value !== 'string') {
        throw new Error('Cannot unmap the passed value');
    }
    return (0, globals_js_1.safeSplit)(value, '');
}
