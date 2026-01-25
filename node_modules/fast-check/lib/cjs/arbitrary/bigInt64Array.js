"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.bigInt64Array = bigInt64Array;
const globals_js_1 = require("../utils/globals.js");
const bigInt_js_1 = require("./bigInt.js");
const TypedIntArrayArbitraryBuilder_js_1 = require("./_internals/builders/TypedIntArrayArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function bigInt64Array(constraints = {}) {
    return (0, TypedIntArrayArbitraryBuilder_js_1.typedIntArrayArbitraryArbitraryBuilder)(constraints, (0, globals_js_1.BigInt)('-9223372036854775808'), (0, globals_js_1.BigInt)('9223372036854775807'), globals_js_1.BigInt64Array, bigInt_js_1.bigInt);
}
