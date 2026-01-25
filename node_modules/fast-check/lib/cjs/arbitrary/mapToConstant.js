"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.mapToConstant = mapToConstant;
const nat_js_1 = require("./nat.js");
const IndexToMappedConstant_js_1 = require("./_internals/mappers/IndexToMappedConstant.js");
const globals_js_1 = require("../utils/globals.js");
function computeNumChoices(options) {
    if (options.length === 0)
        throw new globals_js_1.Error(`fc.mapToConstant expects at least one option`);
    let numChoices = 0;
    for (let idx = 0; idx !== options.length; ++idx) {
        if (options[idx].num < 0)
            throw new globals_js_1.Error(`fc.mapToConstant expects all options to have a number of entries greater or equal to zero`);
        numChoices += options[idx].num;
    }
    if (numChoices === 0)
        throw new globals_js_1.Error(`fc.mapToConstant expects at least one choice among options`);
    return numChoices;
}
/**@__NO_SIDE_EFFECTS__*/function mapToConstant(...entries) {
    const numChoices = computeNumChoices(entries);
    return (0, nat_js_1.nat)({ max: numChoices - 1 }).map((0, IndexToMappedConstant_js_1.indexToMappedConstantMapperFor)(entries), (0, IndexToMappedConstant_js_1.indexToMappedConstantUnmapperFor)(entries));
}
