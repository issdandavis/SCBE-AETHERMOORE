"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.webFragments = webFragments;
const UriQueryOrFragmentArbitraryBuilder_js_1 = require("./_internals/builders/UriQueryOrFragmentArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function webFragments(constraints = {}) {
    return (0, UriQueryOrFragmentArbitraryBuilder_js_1.buildUriQueryOrFragmentArbitrary)(constraints.size);
}
