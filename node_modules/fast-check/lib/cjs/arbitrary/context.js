"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.context = context;
const symbols_js_1 = require("../check/symbols.js");
const constant_js_1 = require("./constant.js");
class ContextImplem {
    constructor() {
        this.receivedLogs = [];
    }
    log(data) {
        this.receivedLogs.push(data);
    }
    size() {
        return this.receivedLogs.length;
    }
    toString() {
        return JSON.stringify({ logs: this.receivedLogs });
    }
    [symbols_js_1.cloneMethod]() {
        return new ContextImplem();
    }
}
/**@__NO_SIDE_EFFECTS__*/function context() {
    return (0, constant_js_1.constant)(new ContextImplem());
}
