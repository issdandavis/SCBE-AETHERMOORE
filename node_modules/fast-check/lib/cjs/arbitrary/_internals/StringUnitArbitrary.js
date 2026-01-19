"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.stringUnit = stringUnit;
const globals_js_1 = require("../../utils/globals.js");
const mapToConstant_js_1 = require("../mapToConstant.js");
const GraphemeRanges_js_1 = require("./data/GraphemeRanges.js");
const GraphemeRangesHelpers_js_1 = require("./helpers/GraphemeRangesHelpers.js");
const registeredStringUnitInstancesMap = Object.create(null);
function getAlphabetRanges(alphabet) {
    switch (alphabet) {
        case 'full':
            return GraphemeRanges_js_1.fullAlphabetRanges;
        case 'ascii':
            return GraphemeRanges_js_1.asciiAlphabetRanges;
    }
}
function getOrCreateStringUnitInstance(type, alphabet) {
    const key = `${type}:${alphabet}`;
    const registered = registeredStringUnitInstancesMap[key];
    if (registered !== undefined) {
        return registered;
    }
    const alphabetRanges = getAlphabetRanges(alphabet);
    const ranges = type === 'binary' ? alphabetRanges : (0, GraphemeRangesHelpers_js_1.intersectGraphemeRanges)(alphabetRanges, GraphemeRanges_js_1.autonomousGraphemeRanges);
    const entries = [];
    for (const range of ranges) {
        (0, globals_js_1.safePush)(entries, (0, GraphemeRangesHelpers_js_1.convertGraphemeRangeToMapToConstantEntry)(range));
    }
    if (type === 'grapheme') {
        const decomposedRanges = (0, GraphemeRangesHelpers_js_1.intersectGraphemeRanges)(alphabetRanges, GraphemeRanges_js_1.autonomousDecomposableGraphemeRanges);
        for (const range of decomposedRanges) {
            const rawEntry = (0, GraphemeRangesHelpers_js_1.convertGraphemeRangeToMapToConstantEntry)(range);
            (0, globals_js_1.safePush)(entries, {
                num: rawEntry.num,
                build: (idInGroup) => (0, globals_js_1.safeNormalize)(rawEntry.build(idInGroup), 'NFD'),
            });
        }
    }
    const stringUnitInstance = (0, mapToConstant_js_1.mapToConstant)(...entries);
    registeredStringUnitInstancesMap[key] = stringUnitInstance;
    return stringUnitInstance;
}
function stringUnit(type, alphabet) {
    return getOrCreateStringUnitInstance(type, alphabet);
}
