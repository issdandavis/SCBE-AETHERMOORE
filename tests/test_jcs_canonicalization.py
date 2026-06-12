"""RFC 8785 (JCS) conformance locks, pinned to the spec's own test vectors.

Number vectors are the IEEE-754 bit patterns from RFC 8785 Appendix B; the
end-to-end object vector is from the cyberphone/json-canonicalization README.
"""

from __future__ import annotations

import struct

import pytest

from python.scbe.reaction_state import jcs_dumps

# (IEEE-754 hex bit pattern, expected JCS serialization) — RFC 8785 Appendix B.
RFC8785_NUMBER_VECTORS = [
    ("0000000000000000", "0"),  # zero
    ("8000000000000000", "0"),  # minus zero
    ("0000000000000001", "5e-324"),  # min positive subnormal
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),  # max double
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),  # 2^53
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),  # ~2^68, still plain notation
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),  # below 10^21 stays plain
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),  # 10^21 boundary flips to exponent
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),  # below 10^-6 is exponent
    ("3eb0c6f7a0b5ed8d", "0.000001"),  # 10^-6 boundary is decimal
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),  # round-to-even case
]


def _double(hex_bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(hex_bits))[0]


@pytest.mark.parametrize("hex_bits,expected", RFC8785_NUMBER_VECTORS)
def test_rfc8785_number_vectors(hex_bits: str, expected: str):
    assert jcs_dumps(_double(hex_bits)) == expected


def test_nan_and_infinity_are_rejected():
    for bits in ("7fffffffffffffff", "7ff0000000000000"):
        with pytest.raises(ValueError):
            jcs_dumps(_double(bits))


def test_readme_end_to_end_vector():
    """The cyberphone/json-canonicalization README vector: exercises lowercase
    \\u escapes, predefined escapes, raw UTF-8 passthrough, unescaped solidus,
    number normalization, and key sorting in one object."""
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 0.000000000000000000000000001],
        "string": '€$\x0f\nA\'B"\\\\"/',
        "literals": [None, True, False],
    }
    expected = (
        '{"literals":[null,true,false],'
        '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
    )
    assert jcs_dumps(value) == expected


def test_keys_sort_by_utf16_code_units_not_code_points():
    """U+1D306 (surrogate pair, first unit 0xD834) sorts BEFORE U+FF61 in
    UTF-16 code-unit order even though its code point is larger — the exact
    case where naive code-point sorting diverges from RFC 8785."""
    serialized = jcs_dumps({"｡": 1, "\U0001d306": 2})
    assert serialized.index("\U0001d306") < serialized.index("｡")


def test_integers_and_nesting_are_stable():
    assert jcs_dumps({"b": [1, 2], "a": {"y": None, "x": -7}}) == '{"a":{"x":-7,"y":null},"b":[1,2]}'
