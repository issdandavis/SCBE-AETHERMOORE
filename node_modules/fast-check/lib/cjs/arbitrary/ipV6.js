"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ipV6 = ipV6;
const array_js_1 = require("./array.js");
const oneof_js_1 = require("./oneof.js");
const string_js_1 = require("./string.js");
const tuple_js_1 = require("./tuple.js");
const ipV4_js_1 = require("./ipV4.js");
const EntitiesToIPv6_js_1 = require("./_internals/mappers/EntitiesToIPv6.js");
const integer_js_1 = require("./integer.js");
const globals_js_1 = require("../utils/globals.js");
function h16sTol32Mapper([a, b]) {
    return `${a}:${b}`;
}
function h16sTol32Unmapper(value) {
    if (typeof value !== 'string')
        throw new globals_js_1.Error('Invalid type');
    if (!value.includes(':'))
        throw new globals_js_1.Error('Invalid value');
    return value.split(':', 2);
}
const items = '0123456789abcdef';
let cachedHexa = undefined;
function hexa() {
    if (cachedHexa === undefined) {
        cachedHexa = (0, integer_js_1.integer)({ min: 0, max: 15 }).map((n) => items[n], (c) => {
            if (typeof c !== 'string') {
                throw new globals_js_1.Error('Not a string');
            }
            if (c.length !== 1) {
                throw new globals_js_1.Error('Invalid length');
            }
            const code = (0, globals_js_1.safeCharCodeAt)(c, 0);
            if (code <= 57) {
                return code - 48;
            }
            if (code < 97) {
                throw new globals_js_1.Error('Invalid character');
            }
            return code - 87;
        });
    }
    return cachedHexa;
}
/**@__NO_SIDE_EFFECTS__*/function ipV6() {
    const h16Arb = (0, string_js_1.string)({ unit: hexa(), minLength: 1, maxLength: 4, size: 'max' });
    const ls32Arb = (0, oneof_js_1.oneof)((0, tuple_js_1.tuple)(h16Arb, h16Arb).map(h16sTol32Mapper, h16sTol32Unmapper), (0, ipV4_js_1.ipV4)());
    return (0, oneof_js_1.oneof)((0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 6, maxLength: 6, size: 'max' }), ls32Arb).map(EntitiesToIPv6_js_1.fullySpecifiedMapper, EntitiesToIPv6_js_1.fullySpecifiedUnmapper), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 5, maxLength: 5, size: 'max' }), ls32Arb).map(EntitiesToIPv6_js_1.onlyTrailingMapper, EntitiesToIPv6_js_1.onlyTrailingUnmapper), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 0, maxLength: 1, size: 'max' }), (0, array_js_1.array)(h16Arb, { minLength: 4, maxLength: 4, size: 'max' }), ls32Arb).map(EntitiesToIPv6_js_1.multiTrailingMapper, EntitiesToIPv6_js_1.multiTrailingUnmapper), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 0, maxLength: 2, size: 'max' }), (0, array_js_1.array)(h16Arb, { minLength: 3, maxLength: 3, size: 'max' }), ls32Arb).map(EntitiesToIPv6_js_1.multiTrailingMapper, EntitiesToIPv6_js_1.multiTrailingUnmapper), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 0, maxLength: 3, size: 'max' }), (0, array_js_1.array)(h16Arb, { minLength: 2, maxLength: 2, size: 'max' }), ls32Arb).map(EntitiesToIPv6_js_1.multiTrailingMapper, EntitiesToIPv6_js_1.multiTrailingUnmapper), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 0, maxLength: 4, size: 'max' }), h16Arb, ls32Arb).map(EntitiesToIPv6_js_1.multiTrailingMapperOne, EntitiesToIPv6_js_1.multiTrailingUnmapperOne), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 0, maxLength: 5, size: 'max' }), ls32Arb).map(EntitiesToIPv6_js_1.singleTrailingMapper, EntitiesToIPv6_js_1.singleTrailingUnmapper), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 0, maxLength: 6, size: 'max' }), h16Arb).map(EntitiesToIPv6_js_1.singleTrailingMapper, EntitiesToIPv6_js_1.singleTrailingUnmapper), (0, tuple_js_1.tuple)((0, array_js_1.array)(h16Arb, { minLength: 0, maxLength: 7, size: 'max' })).map(EntitiesToIPv6_js_1.noTrailingMapper, EntitiesToIPv6_js_1.noTrailingUnmapper));
}
