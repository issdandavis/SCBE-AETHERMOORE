"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.pre = pre;
const PreconditionFailure_js_1 = require("./PreconditionFailure.js");
function pre(expectTruthy) {
    if (!expectTruthy) {
        throw new PreconditionFailure_js_1.PreconditionFailure();
    }
}
