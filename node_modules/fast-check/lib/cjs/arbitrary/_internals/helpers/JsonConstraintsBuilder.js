"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.jsonConstraintsBuilder = jsonConstraintsBuilder;
const boolean_js_1 = require("../../boolean.js");
const constant_js_1 = require("../../constant.js");
const double_js_1 = require("../../double.js");
function jsonConstraintsBuilder(stringArbitrary, constraints) {
    const { depthSize, maxDepth } = constraints;
    const key = stringArbitrary;
    const values = [
        (0, boolean_js_1.boolean)(),
        (0, double_js_1.double)({ noDefaultInfinity: true, noNaN: true }),
        stringArbitrary,
        (0, constant_js_1.constant)(null),
    ];
    return { key, values, depthSize, maxDepth };
}
