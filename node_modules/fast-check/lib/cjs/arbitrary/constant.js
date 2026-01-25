"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.constant = constant;
const ConstantArbitrary_js_1 = require("./_internals/ConstantArbitrary.js");
/**@__NO_SIDE_EFFECTS__*/function constant(value) {
    return new ConstantArbitrary_js_1.ConstantArbitrary([value]);
}
