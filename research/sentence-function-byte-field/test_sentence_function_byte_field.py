"""Byte-field checks for the Essay 1 function codes."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from sentence_function_byte_field import (
    decode_sentence_byte_field,
    encode_sentence_byte_field,
    identity_bytes,
    matches_guide,
    permute_byte_field,
)

PLAIN = bytes.fromhex("53464231010101010101020102000a000000627974652d6669656c64" + "01" * 40 + "00" * 10)
SPANNED = bytes.fromhex(
    "53464231010101010101020102020000000004000000040000000a0000000a000000" "30313233343536373839" + "01" * 44 + "02" * 6
)
PERMUTED_SORT = bytes.fromhex(
    "53464231010101010401020102000a000000627974652d6669656c64" + "01" * 10 + "04" * 10 + "01" * 20 + "00" * 10
)

CATALOG = json.loads(Path(__file__).with_name("sentenceFunctionCatalog.json").read_text(encoding="utf-8"))


class SentenceFunctionByteFieldTest(unittest.TestCase):
    def test_plain_vector_matches_the_shared_hex(self) -> None:
        self.assertEqual(encode_sentence_byte_field(b"byte-field", 1), PLAIN)

    def test_spanned_vector_matches_the_shared_hex(self) -> None:
        encoded = encode_sentence_byte_field(b"0123456789", 1, [(0, 4), (4, 10)])
        self.assertEqual(encoded, SPANNED)
        decoded = decode_sentence_byte_field(encoded)
        self.assertEqual(decoded["channels"]["phrase"][:4], b"\x01\x01\x01\x01")
        self.assertEqual(decoded["channels"]["phrase"][4:], b"\x02" * 6)

    def test_identity_is_a_copy(self) -> None:
        source = bytearray(b"byte-field")
        encoded = encode_sentence_byte_field(source, 1)
        source[0] = 0
        self.assertEqual(identity_bytes(encoded), b"byte-field")
        self.assertTrue(matches_guide(decode_sentence_byte_field(encoded)))

    def test_sort_permutation_keeps_the_identity(self) -> None:
        encoded = encode_sentence_byte_field(b"byte-field", 1)
        permuted = permute_byte_field(encoded, "sort", 7)
        self.assertEqual(permuted, PERMUTED_SORT)
        self.assertEqual(identity_bytes(permuted), b"byte-field")
        self.assertFalse(matches_guide(decode_sentence_byte_field(permuted)))

    def test_every_guide_row_round_trips(self) -> None:
        self.assertEqual(len(CATALOG["sentences"]), 84)
        self.assertEqual(len(CATALOG["slots"]), 32)
        self.assertEqual(len(CATALOG["jobs"]), 32)
        self.assertEqual(len(CATALOG["phrases"]), 175)
        marker = b"id"
        for row in CATALOG["sentences"]:
            encoded = encode_sentence_byte_field(marker, row["id"])
            decoded = decode_sentence_byte_field(encoded)
            self.assertEqual(decoded["identity"], marker)
            self.assertTrue(matches_guide(decoded))

    def test_claim_rows_share_a_sort_and_keep_their_slots(self) -> None:
        claims = [row for row in CATALOG["sentences"] if row["sort"] == 2]
        self.assertGreaterEqual(len({row["slot"] for row in claims}), 2)
        self.assertTrue(all(row["sort"] == 2 for row in claims))

    def test_bad_spans_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            encode_sentence_byte_field(b"abcd", 1, [(0, 1)])
        with self.assertRaises(ValueError):
            encode_sentence_byte_field(b"abcd", 1, [(0, 3), (2, 4)])

    def test_catalog_has_no_essay_prose(self) -> None:
        text = Path(__file__).with_name("sentenceFunctionCatalog.json").read_text(encoding="utf-8")
        self.assertNotIn("Where I come from", text)
        self.assertEqual(CATALOG["prose"], "absent")


if __name__ == "__main__":
    unittest.main()
