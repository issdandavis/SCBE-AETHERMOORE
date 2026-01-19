"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.string = string;
const array_js_1 = require("./array.js");
const SlicesForStringBuilder_js_1 = require("./_internals/helpers/SlicesForStringBuilder.js");
const StringUnitArbitrary_js_1 = require("./_internals/StringUnitArbitrary.js");
const PatternsToString_js_1 = require("./_internals/mappers/PatternsToString.js");
function extractUnitArbitrary(constraints) {
    if (typeof constraints.unit === 'object') {
        return constraints.unit;
    }
    switch (constraints.unit) {
        case 'grapheme':
            return (0, StringUnitArbitrary_js_1.stringUnit)('grapheme', 'full');
        case 'grapheme-composite':
            return (0, StringUnitArbitrary_js_1.stringUnit)('composite', 'full');
        case 'grapheme-ascii':
        case undefined:
            return (0, StringUnitArbitrary_js_1.stringUnit)('grapheme', 'ascii');
        case 'binary':
            return (0, StringUnitArbitrary_js_1.stringUnit)('binary', 'full');
        case 'binary-ascii':
            return (0, StringUnitArbitrary_js_1.stringUnit)('binary', 'ascii');
    }
}
/**@__NO_SIDE_EFFECTS__*/function string(constraints = {}) {
    const charArbitrary = extractUnitArbitrary(constraints);
    const unmapper = (0, PatternsToString_js_1.patternsToStringUnmapperFor)(charArbitrary, constraints);
    const experimentalCustomSlices = (0, SlicesForStringBuilder_js_1.createSlicesForString)(charArbitrary, constraints);
    const enrichedConstraints = { ...constraints, experimentalCustomSlices };
    return (0, array_js_1.array)(charArbitrary, enrichedConstraints).map(PatternsToString_js_1.patternsToStringMapper, unmapper);
}
