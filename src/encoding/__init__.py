"""SCBE encoding primitives.

Dense data bundles: one input, many parallel encodings, all lossless.
The swarm bus can route on the encoding-form hint.
"""

from src.encoding.dense_bundle import DenseBundle, route_lane_for_bundle

__all__ = ["DenseBundle", "route_lane_for_bundle"]
