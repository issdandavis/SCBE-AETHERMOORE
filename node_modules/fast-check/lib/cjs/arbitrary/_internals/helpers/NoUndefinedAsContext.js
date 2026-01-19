"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.UndefinedContextPlaceholder = void 0;
exports.noUndefinedAsContext = noUndefinedAsContext;
const Value_js_1 = require("../../../check/arbitrary/definition/Value.js");
exports.UndefinedContextPlaceholder = Symbol('UndefinedContextPlaceholder');
function noUndefinedAsContext(value) {
    if (value.context !== undefined) {
        return value;
    }
    if (value.hasToBeCloned) {
        return new Value_js_1.Value(value.value_, exports.UndefinedContextPlaceholder, () => value.value);
    }
    return new Value_js_1.Value(value.value_, exports.UndefinedContextPlaceholder);
}
