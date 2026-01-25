"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildStringifiedNatArbitrary = buildStringifiedNatArbitrary;
const constantFrom_js_1 = require("../../constantFrom.js");
const nat_js_1 = require("../../nat.js");
const tuple_js_1 = require("../../tuple.js");
const NatToStringifiedNat_js_1 = require("../mappers/NatToStringifiedNat.js");
function buildStringifiedNatArbitrary(maxValue) {
    return (0, tuple_js_1.tuple)((0, constantFrom_js_1.constantFrom)('dec', 'oct', 'hex'), (0, nat_js_1.nat)(maxValue)).map(NatToStringifiedNat_js_1.natToStringifiedNatMapper, NatToStringifiedNat_js_1.natToStringifiedNatUnmapper);
}
