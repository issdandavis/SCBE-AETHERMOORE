"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildPaddedNumberArbitrary = buildPaddedNumberArbitrary;
const integer_js_1 = require("../../integer.js");
const NumberToPaddedEight_js_1 = require("../mappers/NumberToPaddedEight.js");
function buildPaddedNumberArbitrary(min, max) {
    return (0, integer_js_1.integer)({ min, max }).map(NumberToPaddedEight_js_1.numberToPaddedEightMapper, NumberToPaddedEight_js_1.numberToPaddedEightUnmapper);
}
