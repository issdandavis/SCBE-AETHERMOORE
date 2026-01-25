"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.boolean = boolean;
const integer_js_1 = require("./integer.js");
const noBias_js_1 = require("./noBias.js");
function booleanMapper(v) {
    return v === 1;
}
function booleanUnmapper(v) {
    if (typeof v !== 'boolean')
        throw new Error('Unsupported input type');
    return v === true ? 1 : 0;
}
/**@__NO_SIDE_EFFECTS__*/function boolean() {
    return (0, noBias_js_1.noBias)((0, integer_js_1.integer)({ min: 0, max: 1 }).map(booleanMapper, booleanUnmapper));
}
