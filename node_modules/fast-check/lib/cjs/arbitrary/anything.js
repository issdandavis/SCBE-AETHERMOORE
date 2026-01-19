"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.anything = anything;
const AnyArbitraryBuilder_js_1 = require("./_internals/builders/AnyArbitraryBuilder.js");
const QualifiedObjectConstraints_js_1 = require("./_internals/helpers/QualifiedObjectConstraints.js");
/**@__NO_SIDE_EFFECTS__*/function anything(constraints) {
    return (0, AnyArbitraryBuilder_js_1.anyArbitraryBuilder)((0, QualifiedObjectConstraints_js_1.toQualifiedObjectConstraints)(constraints));
}
