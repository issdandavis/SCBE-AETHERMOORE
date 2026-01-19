"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ipV4Extended = ipV4Extended;
const globals_js_1 = require("../utils/globals.js");
const oneof_js_1 = require("./oneof.js");
const tuple_js_1 = require("./tuple.js");
const StringifiedNatArbitraryBuilder_js_1 = require("./_internals/builders/StringifiedNatArbitraryBuilder.js");
function dotJoinerMapper(data) {
    return (0, globals_js_1.safeJoin)(data, '.');
}
function dotJoinerUnmapper(value) {
    if (typeof value !== 'string') {
        throw new Error('Invalid type');
    }
    return (0, globals_js_1.safeSplit)(value, '.');
}
/**@__NO_SIDE_EFFECTS__*/function ipV4Extended() {
    return (0, oneof_js_1.oneof)((0, tuple_js_1.tuple)((0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(255), (0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(255), (0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(255), (0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(255)).map(dotJoinerMapper, dotJoinerUnmapper), (0, tuple_js_1.tuple)((0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(255), (0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(255), (0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(65535)).map(dotJoinerMapper, dotJoinerUnmapper), (0, tuple_js_1.tuple)((0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(255), (0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(16777215)).map(dotJoinerMapper, dotJoinerUnmapper), (0, StringifiedNatArbitraryBuilder_js_1.buildStringifiedNatArbitrary)(4294967295));
}
