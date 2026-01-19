"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.bigUint64Array = bigUint64Array;
const globals_js_1 = require("../utils/globals.js");
const bigInt_js_1 = require("./bigInt.js");
const TypedIntArrayArbitraryBuilder_js_1 = require("./_internals/builders/TypedIntArrayArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function bigUint64Array(constraints = {}) {
    return (0, TypedIntArrayArbitraryBuilder_js_1.typedIntArrayArbitraryArbitraryBuilder)(constraints, (0, globals_js_1.BigInt)(0), (0, globals_js_1.BigInt)('18446744073709551615'), globals_js_1.BigUint64Array, bigInt_js_1.bigInt);
}
