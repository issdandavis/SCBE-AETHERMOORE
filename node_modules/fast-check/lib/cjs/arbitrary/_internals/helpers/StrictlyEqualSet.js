"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.StrictlyEqualSet = void 0;
const globals_js_1 = require("../../../utils/globals.js");
const safeNumberIsNaN = Number.isNaN;
class StrictlyEqualSet {
    constructor(selector) {
        this.selector = selector;
        this.selectedItemsExceptNaN = new globals_js_1.Set();
        this.data = [];
    }
    tryAdd(value) {
        const selected = this.selector(value);
        if (safeNumberIsNaN(selected)) {
            (0, globals_js_1.safePush)(this.data, value);
            return true;
        }
        const sizeBefore = this.selectedItemsExceptNaN.size;
        (0, globals_js_1.safeAdd)(this.selectedItemsExceptNaN, selected);
        if (sizeBefore !== this.selectedItemsExceptNaN.size) {
            (0, globals_js_1.safePush)(this.data, value);
            return true;
        }
        return false;
    }
    size() {
        return this.data.length;
    }
    getData() {
        return this.data;
    }
}
exports.StrictlyEqualSet = StrictlyEqualSet;
