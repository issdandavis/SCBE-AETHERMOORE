"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.tuple = tuple;
const TupleArbitrary_js_1 = require("./_internals/TupleArbitrary.js");
/**@__NO_SIDE_EFFECTS__*/function tuple(...arbs) {
    return new TupleArbitrary_js_1.TupleArbitrary(arbs);
}
