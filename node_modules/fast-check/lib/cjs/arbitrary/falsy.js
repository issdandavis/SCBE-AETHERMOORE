"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.falsy = falsy;
const globals_js_1 = require("../utils/globals.js");
const constantFrom_js_1 = require("./constantFrom.js");
/**@__NO_SIDE_EFFECTS__*/function falsy(constraints) {
    if (!constraints || !constraints.withBigInt) {
        return (0, constantFrom_js_1.constantFrom)(false, null, undefined, 0, '', NaN);
    }
    return (0, constantFrom_js_1.constantFrom)(false, null, undefined, 0, '', NaN, (0, globals_js_1.BigInt)(0));
}
