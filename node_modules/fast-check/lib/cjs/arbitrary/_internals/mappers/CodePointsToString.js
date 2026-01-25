"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.codePointsToStringMapper = codePointsToStringMapper;
exports.codePointsToStringUnmapper = codePointsToStringUnmapper;
const globals_js_1 = require("../../../utils/globals.js");
function codePointsToStringMapper(tab) {
    return (0, globals_js_1.safeJoin)(tab, '');
}
function codePointsToStringUnmapper(value) {
    if (typeof value !== 'string') {
        throw new Error('Cannot unmap the passed value');
    }
    return [...value];
}
