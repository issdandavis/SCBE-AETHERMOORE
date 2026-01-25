import { buildUriQueryOrFragmentArbitrary } from './_internals/builders/UriQueryOrFragmentArbitraryBuilder.js';
export /**@__NO_SIDE_EFFECTS__*/function webQueryParameters(constraints = {}) {
    return buildUriQueryOrFragmentArbitrary(constraints.size);
}
