"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.object = object;
const dictionary_js_1 = require("./dictionary.js");
const AnyArbitraryBuilder_js_1 = require("./_internals/builders/AnyArbitraryBuilder.js");
const QualifiedObjectConstraints_js_1 = require("./_internals/helpers/QualifiedObjectConstraints.js");
function objectInternal(constraints) {
    return (0, dictionary_js_1.dictionary)(constraints.key, (0, AnyArbitraryBuilder_js_1.anyArbitraryBuilder)(constraints), {
        maxKeys: constraints.maxKeys,
        noNullPrototype: !constraints.withNullPrototype,
        size: constraints.size,
    });
}
/**@__NO_SIDE_EFFECTS__*/function object(constraints) {
    return objectInternal((0, QualifiedObjectConstraints_js_1.toQualifiedObjectConstraints)(constraints));
}
