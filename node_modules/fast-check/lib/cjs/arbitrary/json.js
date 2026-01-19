"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.json = json;
const jsonValue_js_1 = require("./jsonValue.js");
const safeJsonStringify = JSON.stringify;
/**@__NO_SIDE_EFFECTS__*/function json(constraints = {}) {
    const arb = (0, jsonValue_js_1.jsonValue)(constraints);
    return arb.map(safeJsonStringify);
}
