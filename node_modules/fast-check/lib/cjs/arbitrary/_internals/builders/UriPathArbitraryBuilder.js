"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildUriPathArbitrary = buildUriPathArbitrary;
const webSegment_js_1 = require("../../webSegment.js");
const array_js_1 = require("../../array.js");
const SegmentsToPath_js_1 = require("../mappers/SegmentsToPath.js");
const oneof_js_1 = require("../../oneof.js");
function sqrtSize(size) {
    switch (size) {
        case 'xsmall':
            return ['xsmall', 'xsmall'];
        case 'small':
            return ['small', 'xsmall'];
        case 'medium':
            return ['small', 'small'];
        case 'large':
            return ['medium', 'small'];
        case 'xlarge':
            return ['medium', 'medium'];
    }
}
function buildUriPathArbitraryInternal(segmentSize, numSegmentSize) {
    return (0, array_js_1.array)((0, webSegment_js_1.webSegment)({ size: segmentSize }), { size: numSegmentSize }).map(SegmentsToPath_js_1.segmentsToPathMapper, SegmentsToPath_js_1.segmentsToPathUnmapper);
}
function buildUriPathArbitrary(resolvedSize) {
    const [segmentSize, numSegmentSize] = sqrtSize(resolvedSize);
    if (segmentSize === numSegmentSize) {
        return buildUriPathArbitraryInternal(segmentSize, numSegmentSize);
    }
    return (0, oneof_js_1.oneof)(buildUriPathArbitraryInternal(segmentSize, numSegmentSize), buildUriPathArbitraryInternal(numSegmentSize, segmentSize));
}
