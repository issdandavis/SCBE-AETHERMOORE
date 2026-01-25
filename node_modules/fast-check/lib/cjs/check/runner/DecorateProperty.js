"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.decorateProperty = decorateProperty;
const SkipAfterProperty_js_1 = require("../property/SkipAfterProperty.js");
const TimeoutProperty_js_1 = require("../property/TimeoutProperty.js");
const UnbiasedProperty_js_1 = require("../property/UnbiasedProperty.js");
const IgnoreEqualValuesProperty_js_1 = require("../property/IgnoreEqualValuesProperty.js");
const safeDateNow = Date.now;
const safeSetTimeout = setTimeout;
const safeClearTimeout = clearTimeout;
function decorateProperty(rawProperty, qParams) {
    let prop = rawProperty;
    if (rawProperty.isAsync() && qParams.timeout !== undefined) {
        prop = new TimeoutProperty_js_1.TimeoutProperty(prop, qParams.timeout, safeSetTimeout, safeClearTimeout);
    }
    if (qParams.unbiased) {
        prop = new UnbiasedProperty_js_1.UnbiasedProperty(prop);
    }
    if (qParams.skipAllAfterTimeLimit !== undefined) {
        prop = new SkipAfterProperty_js_1.SkipAfterProperty(prop, safeDateNow, qParams.skipAllAfterTimeLimit, false, safeSetTimeout, safeClearTimeout);
    }
    if (qParams.interruptAfterTimeLimit !== undefined) {
        prop = new SkipAfterProperty_js_1.SkipAfterProperty(prop, safeDateNow, qParams.interruptAfterTimeLimit, true, safeSetTimeout, safeClearTimeout);
    }
    if (qParams.skipEqualValues) {
        prop = new IgnoreEqualValuesProperty_js_1.IgnoreEqualValuesProperty(prop, true);
    }
    if (qParams.ignoreEqualValues) {
        prop = new IgnoreEqualValuesProperty_js_1.IgnoreEqualValuesProperty(prop, false);
    }
    return prop;
}
