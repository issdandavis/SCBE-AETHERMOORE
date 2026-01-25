"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ipV4 = ipV4;
const globals_js_1 = require("../utils/globals.js");
const nat_js_1 = require("./nat.js");
const tuple_js_1 = require("./tuple.js");
const NatToStringifiedNat_js_1 = require("./_internals/mappers/NatToStringifiedNat.js");
function dotJoinerMapper(data) {
    return (0, globals_js_1.safeJoin)(data, '.');
}
function dotJoinerUnmapper(value) {
    if (typeof value !== 'string') {
        throw new Error('Invalid type');
    }
    return (0, globals_js_1.safeMap)((0, globals_js_1.safeSplit)(value, '.'), (v) => (0, NatToStringifiedNat_js_1.tryParseStringifiedNat)(v, 10));
}
/**@__NO_SIDE_EFFECTS__*/function ipV4() {
    return (0, tuple_js_1.tuple)((0, nat_js_1.nat)(255), (0, nat_js_1.nat)(255), (0, nat_js_1.nat)(255), (0, nat_js_1.nat)(255)).map(dotJoinerMapper, dotJoinerUnmapper);
}
