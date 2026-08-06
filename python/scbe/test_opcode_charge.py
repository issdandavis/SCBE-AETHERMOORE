from __future__ import annotations

import unittest
from collections import Counter

from scbe.ca_opcode_table import get_ca_opcode
from scbe.opcode_charge import (
    ARM64_TO_ISA,
    N_OPCODES,
    REALM_NAMES,
    X86_TO_ISA,
    charge_distance,
    lift_mnemonics,
    opcode_charge,
    opcode_negabinary,
    opcode_number,
    opcode_realm,
    render_charge,
    signature,
)


class LosslessnessTests(unittest.TestCase):
    """The whole reason this module exists."""

    def test_charge_is_injective_over_all_64_opcodes(self) -> None:
        codes = {opcode_charge(i) for i in range(N_OPCODES)}
        self.assertEqual(len(codes), N_OPCODES)

    def test_trit_vectors_are_NOT_injective(self) -> None:
        """Pins the defect. If this ever passes, the trit table changed and the
        charge encoding may no longer be needed for identity."""
        trits = {tuple(int(t) for t in get_ca_opcode(i).trit) for i in range(N_OPCODES)}
        self.assertLess(len(trits), N_OPCODES)
        self.assertEqual(len(trits), 21)  # measured 2026-08-06

    def test_known_collisions_are_separated_by_charge(self) -> None:
        """add/max and and/gte share a trit vector. They must not share a charge."""
        ids = {get_ca_opcode(i).name: i for i in range(N_OPCODES)}
        for a, b in (("add", "max"), ("and", "gte"), ("inc", "dec")):
            ta = tuple(int(t) for t in get_ca_opcode(ids[a]).trit)
            tb = tuple(int(t) for t in get_ca_opcode(ids[b]).trit)
            self.assertEqual(ta, tb, "%s/%s no longer collide under trits" % (a, b))
            self.assertNotEqual(opcode_charge(ids[a]), opcode_charge(ids[b]))


class StructureTests(unittest.TestCase):
    def test_realm_is_the_top_two_signs(self) -> None:
        for r, nm in enumerate(REALM_NAMES):
            for off in range(16):
                self.assertEqual(opcode_realm(r * 16 + off), nm)

    def test_each_realm_spans_a_binomial_on_the_other_four_positions(self) -> None:
        """C(4,k) = 1,4,6,4,1 within every realm."""
        for r in range(4):
            counts = Counter(opcode_number(i) for i in range(r * 16, (r + 1) * 16))
            self.assertEqual(sorted(counts.values()), [1, 1, 4, 4, 6])

    def test_whole_isa_spans_the_full_binomial(self) -> None:
        counts = Counter(opcode_number(i) for i in range(N_OPCODES))
        self.assertEqual(sorted(counts.values()), [1, 1, 6, 6, 15, 15, 20])

    def test_bits_and_judge_are_charge_conjugate(self) -> None:
        """Prefixes -+ and +- both net zero, so the two realms have identical shells."""
        b = Counter(opcode_number(i) for i in range(0x10, 0x20))
        j = Counter(opcode_number(i) for i in range(0x20, 0x30))
        self.assertEqual(b, j)

    def test_the_alternating_pair_is_the_extreme(self) -> None:
        """nor / within are the size-2 rotation orbit AND the negabinary bounds."""
        vals = {i: opcode_negabinary(i) for i in range(N_OPCODES)}
        self.assertEqual(render_charge(0x15), "-+-+-+")
        self.assertEqual(render_charge(0x2A), "+-+-+-")
        self.assertEqual(vals[0x15], max(vals.values()))
        self.assertEqual(vals[0x2A], min(vals.values()))


class NegabinaryTests(unittest.TestCase):
    def test_bijective_onto_exactly_64_consecutive_integers(self) -> None:
        vals = [opcode_negabinary(i) for i in range(N_OPCODES)]
        self.assertEqual(len(set(vals)), N_OPCODES)
        self.assertEqual(min(vals), -42)
        self.assertEqual(max(vals), 21)
        self.assertEqual(sorted(vals), list(range(-42, 22)))

    def test_realms_are_contiguous_non_overlapping_bands(self) -> None:
        bands = []
        for r in range(4):
            vs = [opcode_negabinary(i) for i in range(r * 16, (r + 1) * 16)]
            self.assertEqual(sorted(vs), list(range(min(vs), min(vs) + 16)))
            bands.append((min(vs), max(vs)))
        bands.sort()
        for (_, hi), (lo, _) in zip(bands, bands[1:]):
            self.assertEqual(lo, hi + 1)  # touching, no gaps and no overlap


class LiftTests(unittest.TestCase):
    def test_x86_and_arm64_same_computation_same_signature(self) -> None:
        """The interlingua claim, as a test rather than an assertion.

        The mnemonics must be GENUINELY equivalent. An earlier version of this paired
        x86 `popcnt` with ARM64 `clz` and reported a perfect L1 = 0 match -- but those
        are different operations, and the only reason it matched is that the trit table
        collides popcount/clz/ctz/sign into one code. The charge encoding correctly
        scored that pair 0.4 apart, which is how the overclaim was caught. ARM64's
        popcount is `cnt`.
        """
        x86 = ["shl", "shr", "xor", "and", "popcnt"]
        arm = ["lsl", "lsr", "eor", "and", "cnt"]
        sx, _ = lift_mnemonics(x86, "x86")
        sa, _ = lift_mnemonics(arm, "arm64")
        self.assertEqual(len(sx), 5)
        self.assertEqual(len(sa), 5)
        self.assertAlmostEqual(charge_distance(signature(sx), signature(sa)), 0.0, places=12)

    def test_charge_catches_what_trits_merge_across_architectures(self) -> None:
        """popcnt vs clz is a REAL difference. Charge must see it; trits do not."""
        sx, _ = lift_mnemonics(["popcnt"], "x86")
        sa, _ = lift_mnemonics(["clz"], "arm64")
        self.assertGreater(charge_distance(signature(sx), signature(sa)), 0.0)

    def test_different_computation_separates_on_the_same_machine(self) -> None:
        bits, _ = lift_mnemonics(["shl", "shr", "xor", "and", "popcnt"], "x86")
        arith, _ = lift_mnemonics(["add", "sub", "imul", "idiv"], "x86")
        self.assertGreater(charge_distance(signature(bits), signature(arith)), 0.5)

    def test_control_flow_is_reported_not_silently_dropped(self) -> None:
        """Coverage honesty: unmapped instructions come back, they do not vanish."""
        mapped, unmapped = lift_mnemonics(["add", "mov", "jmp", "xor", "int3", "ret", "lea"], "x86")
        self.assertEqual(len(mapped), 2)
        self.assertEqual(unmapped, ["mov", "jmp", "int3", "ret", "lea"])

    def test_every_mapped_mnemonic_resolves_to_a_real_opcode(self) -> None:
        for table, arch in ((X86_TO_ISA, "x86"), (ARM64_TO_ISA, "arm64")):
            mapped, unmapped = lift_mnemonics(sorted(table), arch)
            self.assertEqual(unmapped, [], "%s has mnemonics with no opcode" % arch)
            self.assertEqual(len(mapped), len(table))


class SignatureTests(unittest.TestCase):
    def test_signature_is_scale_free(self) -> None:
        ops = [0x00, 0x16, 0x2A]
        self.assertEqual(signature(ops), signature(ops * 7))

    def test_empty_stream_does_not_divide_by_zero(self) -> None:
        self.assertEqual(signature([]), [0.0] * 6)


if __name__ == "__main__":
    unittest.main()
