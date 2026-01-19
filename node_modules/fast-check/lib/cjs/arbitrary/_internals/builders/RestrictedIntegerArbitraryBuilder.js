"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.restrictedIntegerArbitraryBuilder = restrictedIntegerArbitraryBuilder;
const integer_js_1 = require("../../integer.js");
const WithShrinkFromOtherArbitrary_js_1 = require("../WithShrinkFromOtherArbitrary.js");
function restrictedIntegerArbitraryBuilder(min, maxGenerated, max) {
    const generatorArbitrary = (0, integer_js_1.integer)({ min, max: maxGenerated });
    if (maxGenerated === max) {
        return generatorArbitrary;
    }
    const shrinkerArbitrary = (0, integer_js_1.integer)({ min, max });
    return new WithShrinkFromOtherArbitrary_js_1.WithShrinkFromOtherArbitrary(generatorArbitrary, shrinkerArbitrary);
}
