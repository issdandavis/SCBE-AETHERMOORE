"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.webPath = webPath;
const MaxLengthFromMinLength_js_1 = require("./_internals/helpers/MaxLengthFromMinLength.js");
const UriPathArbitraryBuilder_js_1 = require("./_internals/builders/UriPathArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function webPath(constraints) {
    const c = constraints || {};
    const resolvedSize = (0, MaxLengthFromMinLength_js_1.resolveSize)(c.size);
    return (0, UriPathArbitraryBuilder_js_1.buildUriPathArbitrary)(resolvedSize);
}
