"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildUriQueryOrFragmentArbitrary = buildUriQueryOrFragmentArbitrary;
const CharacterRangeArbitraryBuilder_js_1 = require("./CharacterRangeArbitraryBuilder.js");
const string_js_1 = require("../../string.js");
function buildUriQueryOrFragmentArbitrary(size) {
    return (0, string_js_1.string)({ unit: (0, CharacterRangeArbitraryBuilder_js_1.getOrCreateAlphaNumericPercentArbitrary)("-._~!$&'()*+,;=:@/?"), size });
}
