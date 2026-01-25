"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.webAuthority = webAuthority;
const CharacterRangeArbitraryBuilder_js_1 = require("./_internals/builders/CharacterRangeArbitraryBuilder.js");
const constant_js_1 = require("./constant.js");
const domain_js_1 = require("./domain.js");
const ipV4_js_1 = require("./ipV4.js");
const ipV4Extended_js_1 = require("./ipV4Extended.js");
const ipV6_js_1 = require("./ipV6.js");
const nat_js_1 = require("./nat.js");
const oneof_js_1 = require("./oneof.js");
const option_js_1 = require("./option.js");
const string_js_1 = require("./string.js");
const tuple_js_1 = require("./tuple.js");
function hostUserInfo(size) {
    return (0, string_js_1.string)({ unit: (0, CharacterRangeArbitraryBuilder_js_1.getOrCreateAlphaNumericPercentArbitrary)("-._~!$&'()*+,;=:"), size });
}
function userHostPortMapper([u, h, p]) {
    return (u === null ? '' : `${u}@`) + h + (p === null ? '' : `:${p}`);
}
function userHostPortUnmapper(value) {
    if (typeof value !== 'string') {
        throw new Error('Unsupported');
    }
    const atPosition = value.indexOf('@');
    const user = atPosition !== -1 ? value.substring(0, atPosition) : null;
    const portRegex = /:(\d+)$/;
    const m = portRegex.exec(value);
    const port = m !== null ? Number(m[1]) : null;
    const host = m !== null ? value.substring(atPosition + 1, value.length - m[1].length - 1) : value.substring(atPosition + 1);
    return [user, host, port];
}
function bracketedMapper(s) {
    return `[${s}]`;
}
function bracketedUnmapper(value) {
    if (typeof value !== 'string' || value[0] !== '[' || value[value.length - 1] !== ']') {
        throw new Error('Unsupported');
    }
    return value.substring(1, value.length - 1);
}
/**@__NO_SIDE_EFFECTS__*/function webAuthority(constraints) {
    const c = constraints || {};
    const size = c.size;
    const hostnameArbs = [
        (0, domain_js_1.domain)({ size }),
        ...(c.withIPv4 === true ? [(0, ipV4_js_1.ipV4)()] : []),
        ...(c.withIPv6 === true ? [(0, ipV6_js_1.ipV6)().map(bracketedMapper, bracketedUnmapper)] : []),
        ...(c.withIPv4Extended === true ? [(0, ipV4Extended_js_1.ipV4Extended)()] : []),
    ];
    return (0, tuple_js_1.tuple)(c.withUserInfo === true ? (0, option_js_1.option)(hostUserInfo(size)) : (0, constant_js_1.constant)(null), (0, oneof_js_1.oneof)(...hostnameArbs), c.withPort === true ? (0, option_js_1.option)((0, nat_js_1.nat)(65535)) : (0, constant_js_1.constant)(null)).map(userHostPortMapper, userHostPortUnmapper);
}
