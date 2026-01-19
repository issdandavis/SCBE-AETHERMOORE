"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.webUrl = webUrl;
const constantFrom_js_1 = require("./constantFrom.js");
const constant_js_1 = require("./constant.js");
const option_js_1 = require("./option.js");
const tuple_js_1 = require("./tuple.js");
const webQueryParameters_js_1 = require("./webQueryParameters.js");
const webFragments_js_1 = require("./webFragments.js");
const webAuthority_js_1 = require("./webAuthority.js");
const PartsToUrl_js_1 = require("./_internals/mappers/PartsToUrl.js");
const MaxLengthFromMinLength_js_1 = require("./_internals/helpers/MaxLengthFromMinLength.js");
const webPath_js_1 = require("./webPath.js");
/**@__NO_SIDE_EFFECTS__*/function webUrl(constraints) {
    const c = constraints || {};
    const resolvedSize = (0, MaxLengthFromMinLength_js_1.resolveSize)(c.size);
    const resolvedAuthoritySettingsSize = c.authoritySettings !== undefined && c.authoritySettings.size !== undefined
        ? (0, MaxLengthFromMinLength_js_1.relativeSizeToSize)(c.authoritySettings.size, resolvedSize)
        : resolvedSize;
    const resolvedAuthoritySettings = { ...c.authoritySettings, size: resolvedAuthoritySettingsSize };
    const validSchemes = c.validSchemes || ['http', 'https'];
    const schemeArb = (0, constantFrom_js_1.constantFrom)(...validSchemes);
    const authorityArb = (0, webAuthority_js_1.webAuthority)(resolvedAuthoritySettings);
    return (0, tuple_js_1.tuple)(schemeArb, authorityArb, (0, webPath_js_1.webPath)({ size: resolvedSize }), c.withQueryParameters === true ? (0, option_js_1.option)((0, webQueryParameters_js_1.webQueryParameters)({ size: resolvedSize })) : (0, constant_js_1.constant)(null), c.withFragments === true ? (0, option_js_1.option)((0, webFragments_js_1.webFragments)({ size: resolvedSize })) : (0, constant_js_1.constant)(null)).map(PartsToUrl_js_1.partsToUrlMapper, PartsToUrl_js_1.partsToUrlUnmapper);
}
