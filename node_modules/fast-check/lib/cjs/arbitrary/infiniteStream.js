"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.infiniteStream = infiniteStream;
const StreamArbitrary_js_1 = require("./_internals/StreamArbitrary.js");
/**@__NO_SIDE_EFFECTS__*/function infiniteStream(arb, constraints) {
    const history = constraints !== undefined && typeof constraints === 'object' && 'noHistory' in constraints
        ? !constraints.noHistory
        : true;
    return new StreamArbitrary_js_1.StreamArbitrary(arb, history);
}
