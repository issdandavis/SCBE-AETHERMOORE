"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.constantFrom = constantFrom;
const ConstantArbitrary_js_1 = require("./_internals/ConstantArbitrary.js");
/**@__NO_SIDE_EFFECTS__*/function constantFrom(...values) {
    if (values.length === 0) {
        throw new Error('fc.constantFrom expects at least one parameter');
    }
    return new ConstantArbitrary_js_1.ConstantArbitrary(values);
}
