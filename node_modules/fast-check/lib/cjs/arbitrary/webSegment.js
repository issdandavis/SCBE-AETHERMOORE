"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.webSegment = webSegment;
const CharacterRangeArbitraryBuilder_js_1 = require("./_internals/builders/CharacterRangeArbitraryBuilder.js");
const string_js_1 = require("./string.js");
/**@__NO_SIDE_EFFECTS__*/function webSegment(constraints = {}) {
    return (0, string_js_1.string)({ unit: (0, CharacterRangeArbitraryBuilder_js_1.getOrCreateAlphaNumericPercentArbitrary)("-._~!$&'()*+,;=:@"), size: constraints.size });
}
