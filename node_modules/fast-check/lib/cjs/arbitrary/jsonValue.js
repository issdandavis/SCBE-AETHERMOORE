"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.jsonValue = jsonValue;
const string_js_1 = require("./string.js");
const JsonConstraintsBuilder_js_1 = require("./_internals/helpers/JsonConstraintsBuilder.js");
const anything_js_1 = require("./anything.js");
/**@__NO_SIDE_EFFECTS__*/function jsonValue(constraints = {}) {
    const noUnicodeString = constraints.noUnicodeString === undefined || constraints.noUnicodeString === true;
    const stringArbitrary = 'stringUnit' in constraints
        ? (0, string_js_1.string)({ unit: constraints.stringUnit })
        : noUnicodeString
            ? (0, string_js_1.string)()
            : (0, string_js_1.string)({ unit: 'binary' });
    return (0, anything_js_1.anything)((0, JsonConstraintsBuilder_js_1.jsonConstraintsBuilder)(stringArbitrary, constraints));
}
