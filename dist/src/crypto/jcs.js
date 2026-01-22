"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.canonicalize = canonicalize;
/**
 * Minimal JCS (RFC 8785-like) canonicalization: UTF-8, lexicographic sorting of keys,
 * no insignificant whitespace, stable numbers.
 */
function canonicalize(value) {
    return JSON.stringify(sort(value));
}
function sort(x) {
    if (x === null || typeof x !== 'object')
        return normalizeNumber(x);
    if (Array.isArray(x))
        return x.map(sort);
    const out = {};
    for (const k of Object.keys(x).sort())
        out[k] = sort(x[k]);
    return out;
}
function normalizeNumber(x) {
    if (typeof x !== 'number')
        return x;
    // Ensure JSON number normalization: finite -> as-is, otherwise stringify
    if (!Number.isFinite(x))
        return String(x);
    return x;
}
//# sourceMappingURL=jcs.js.map