"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.initialPoolForEntityGraph = initialPoolForEntityGraph;
const array_js_1 = require("../array.js");
const tuple_js_1 = require("../tuple.js");
const constant_js_1 = require("../constant.js");
const globals_js_1 = require("../../utils/globals.js");
function canHaveAtLeastOneItem(keys, constraints) {
    for (const key of keys) {
        const constraintsOnKey = constraints[key] || {};
        if (constraintsOnKey.maxLength === undefined || constraintsOnKey.maxLength > 0) {
            return true;
        }
    }
    return false;
}
function initialPoolForEntityGraph(keys, constraints) {
    if (keys.length === 0) {
        return (0, constant_js_1.constant)([]);
    }
    if (!canHaveAtLeastOneItem(keys, constraints)) {
        throw new globals_js_1.Error('Contraints on pool must accept at least one entity, maxLength cannot sum to 0');
    }
    const arbitraries = keys.map((key) => (0, array_js_1.array)((0, constant_js_1.constant)(key), constraints[key]));
    return ((0, tuple_js_1.tuple)(...arbitraries)
        .map((values) => (0, globals_js_1.safeFlat)(values))
        .filter((names) => names.length > 0));
}
