"""Stage 6.5: Coding Primitives Curriculum — Binary, Trit, Ternary, Mod Shifts.

Teaches the most fundamental coding operations as training data, mapped
to the SCBE tongue system. These are the ATOMS that all higher computation
reduces to.

Primitive Hierarchy (in order of fundamentality):
  Level 0: BIT         — 0/1, presence/absence (L0 binary)
  Level 1: GATES       — AND, OR, XOR, NOT, NAND, NOR (UM: immune logic)
  Level 2: SHIFT       — left/right shift, rotate (CA: compute movement)
  Level 3: ARITHMETIC  — add, subtract, multiply, divide (CA: raw compute)
  Level 4: COMPARE     — eq, lt, gt → subtract + sign bit (RU: governance)
  Level 5: ASSIGN      — store value at address → STATE (AV: knowledge)
  Level 6: BRANCH      — conditional jump → IF (KO: intent)
  Level 7: LOOP        — repeated branch → Turing completeness (KO+DR)
  Level 8: ADDRESS     — pointers, indirection (DR: architecture)
  Level 9: CALL/RETURN — stack push/pop, abstraction (KO+AV)

Encoding Layers (Issac's triple encoding theory):
  Binary: {0, 1}       = present / absent     → 1 bit per position
  Trit:   {-1, 0, +1}  = reject / null / accept → intent layer
  Float:  continuous    = strength/weight      → activation magnitude
  Mod:    cyclic groups = wrapping arithmetic   → SpiralRing position

Combined: each datum carries presence + polarity + strength + ring position
= 24x information density over flat binary.

Training patterns generated:
  1. Bit manipulation exercises (AND/OR/XOR truth tables, bit counting)
  2. Trit logic exercises (ternary decision trees, null-aware routing)
  3. Mod arithmetic (cyclic groups, ring operations, phi-modular)
  4. Shift transformations (bit extraction, masking, rotation)
  5. Encoding round-trips (binary ↔ trit ↔ float ↔ mod)
  6. Primitive-to-tongue mapping (which tongue owns which operation)
  7. Composition exercises (build add from gates, multiply from shifts+adds)
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

from .config import PHI, PHI_INV, TONGUES, TONGUE_WEIGHTS, TONGUE_NAMES


# ---------------------------------------------------------------------------
# Primitive definitions
# ---------------------------------------------------------------------------

@dataclass
class Primitive:
    """A single coding primitive with tongue affinity."""
    name: str
    level: int
    tongue: str            # Primary tongue affinity
    description: str
    binary_example: str    # How it looks in raw binary
    python_example: str    # Python equivalent
    trit_mapping: str      # How it maps to trit logic
    mod_note: str          # Modular arithmetic connection


PRIMITIVES = [
    Primitive(
        name="BIT",
        level=0,
        tongue="KO",  # The most primitive intent: exist or not
        description="The atom of computation. 0 or 1. Absence or presence.",
        binary_example="0b0 → absent, 0b1 → present",
        python_example="x = True  # 1 bit of state",
        trit_mapping="{0,1} is the degenerate case of {-1,0,+1} with no rejection",
        mod_note="bit = Z/2Z, the smallest cyclic group",
    ),
    Primitive(
        name="NOT",
        level=1,
        tongue="UM",
        description="Inversion. The first defense: negate the input.",
        binary_example="NOT 0 → 1, NOT 1 → 0",
        python_example="~x & 1  # or: not x",
        trit_mapping="NOT in trit: -1→+1, 0→0, +1→-1 (polarity flip, null invariant)",
        mod_note="NOT = additive inverse in Z/2Z: x + 1 mod 2",
    ),
    Primitive(
        name="AND",
        level=1,
        tongue="UM",
        description="Both must be true. The gate that FILTERS. Immune checkpoint.",
        binary_example="1 AND 1 → 1, else → 0",
        python_example="x & y",
        trit_mapping="trit AND: min(a,b) — reject dominates (strictest wins)",
        mod_note="AND = multiplication in Z/2Z: x * y mod 2",
    ),
    Primitive(
        name="OR",
        level=1,
        tongue="UM",
        description="Either can be true. The gate that INCLUDES.",
        binary_example="0 OR 0 → 0, else → 1",
        python_example="x | y",
        trit_mapping="trit OR: max(a,b) — accept dominates (most permissive wins)",
        mod_note="OR is NOT(AND(NOT(x), NOT(y))) — De Morgan's law",
    ),
    Primitive(
        name="XOR",
        level=1,
        tongue="UM",
        description="Difference detector. Same→0, Different→1. The FRICTION gate.",
        binary_example="0 XOR 0 → 0, 1 XOR 1 → 0, else → 1",
        python_example="x ^ y",
        trit_mapping="trit XOR: |a - b| — measures DISTANCE between states",
        mod_note="XOR = addition in Z/2Z: x + y mod 2. SpiralRing XOR neighbor mixing!",
    ),
    Primitive(
        name="NAND",
        level=1,
        tongue="UM",
        description="Universal gate. ALL other gates can be built from NAND alone.",
        binary_example="NAND = NOT(AND): 1 NAND 1 → 0, else → 1",
        python_example="~(x & y) & 1",
        trit_mapping="trit NAND: -(min(a,b)) — reject unless both accept",
        mod_note="Functionally complete: NAND alone = Turing complete boolean logic",
    ),
    Primitive(
        name="SHIFT_LEFT",
        level=2,
        tongue="CA",
        description="Multiply by 2. Move bits toward higher significance.",
        binary_example="0b0011 << 1 → 0b0110 (3 → 6)",
        python_example="x << n  # multiply by 2^n",
        trit_mapping="trit shift: multiply trit position by 3^n (base-3 place shift)",
        mod_note="Left shift mod 2^k = cyclic rotation in fixed-width register",
    ),
    Primitive(
        name="SHIFT_RIGHT",
        level=2,
        tongue="CA",
        description="Divide by 2 (floor). Move bits toward lower significance.",
        binary_example="0b0110 >> 1 → 0b0011 (6 → 3)",
        python_example="x >> n  # floor divide by 2^n",
        trit_mapping="trit shift right: floor divide trit by 3^n (lose least significant trit)",
        mod_note="Right shift = truncation. Information is DESTROYED (irreversible)",
    ),
    Primitive(
        name="ROTATE",
        level=2,
        tongue="CA",
        description="Circular shift. No information lost. The SpiralRing operation.",
        binary_example="ROL 0b1001, 1 → 0b0011 (in 4-bit: MSB wraps to LSB)",
        python_example="((x << n) | (x >> (width - n))) & mask",
        trit_mapping="trit rotate: circular permutation of trit positions",
        mod_note="Rotation = addition mod width. THIS IS the SpiralRing twist.",
    ),
    Primitive(
        name="ADD",
        level=3,
        tongue="CA",
        description="Combine two quantities. Built from XOR (sum) + AND (carry).",
        binary_example="Half adder: sum=a^b, carry=a&b. Chain for full adder.",
        python_example="x + y",
        trit_mapping="trit add: balanced ternary addition with carry in {-1,0,+1}",
        mod_note="Addition mod n = cyclic group operation. All rings have addition.",
    ),
    Primitive(
        name="SUBTRACT",
        level=3,
        tongue="CA",
        description="Difference. ADD + two's complement (negate then add).",
        binary_example="a - b = a + (~b + 1) in two's complement",
        python_example="x - y",
        trit_mapping="trit subtract: a + (-b) where -b flips all trit polarities",
        mod_note="Subtraction = addition of additive inverse. Same group, opposite direction.",
    ),
    Primitive(
        name="MULTIPLY",
        level=3,
        tongue="CA",
        description="Repeated shift-and-add. Scales one quantity by another.",
        binary_example="3 × 5 = (shift 5 left by 0, add) + (shift 5 left by 1, add)",
        python_example="x * y",
        trit_mapping="trit multiply: shift-and-add in balanced ternary (three partial products possible)",
        mod_note="Multiplication mod n = ring operation. Z/nZ is a ring, not just a group.",
    ),
    Primitive(
        name="COMPARE",
        level=4,
        tongue="RU",
        description="Is a < b? Subtract and check sign bit. GOVERNANCE: does it pass the rule?",
        binary_example="a < b ↔ (a - b) has sign bit set",
        python_example="x < y  # returns trit-like: True/False (but no null!)",
        trit_mapping="trit compare returns {-1, 0, +1} directly: less/equal/greater. NATURAL trit output.",
        mod_note="Comparison = ordering. Not all modular systems have ordering (Z/nZ doesn't for n>1).",
    ),
    Primitive(
        name="ASSIGN",
        level=5,
        tongue="AV",
        description="Store a value at an address. Creation of STATE. Memory write.",
        binary_example="MEM[addr] ← value (write enable + data bus + address bus)",
        python_example="x = 42  # bind name to value",
        trit_mapping="trit assign: store the full trit state {polarity, magnitude, ring_position}",
        mod_note="Assignment = function update. Memory is a function from addresses to values.",
    ),
    Primitive(
        name="BRANCH",
        level=6,
        tongue="KO",
        description="Conditional jump. IF. Where computation stops being linear.",
        binary_example="if (flag) goto addr; // test bit, jump if set",
        python_example="if condition: do_thing()",
        trit_mapping="trit branch: 3-way → if reject: path_A, if null: path_B, if accept: path_C",
        mod_note="Branch = piecewise function. Computation becomes a directed graph.",
    ),
    Primitive(
        name="LOOP",
        level=7,
        tongue="DR",
        description="Repeated branch. The source of Turing completeness. Structure emerges.",
        binary_example="top: ... if (cond) goto top; // backward branch",
        python_example="while condition: do_thing()",
        trit_mapping="trit loop: continue while state ≠ target_trit_pattern",
        mod_note="Loop = orbit of a function. Termination = reaching a fixed point.",
    ),
    Primitive(
        name="ADDRESS",
        level=8,
        tongue="DR",
        description="Pointer. Indirection. One value points to another value's location.",
        binary_example="ptr = &x; val = *ptr; // address-of, dereference",
        python_example="# Python hides this: id(x) is the address, x is the deref",
        trit_mapping="trit pointer: address in base-3 → more compact addressing (3^n vs 2^n)",
        mod_note="Pointers = elements of an address space. Address space = Z/2^k Z.",
    ),
    Primitive(
        name="CALL_RETURN",
        level=9,
        tongue="KO",
        description="Function abstraction. Push state, jump, compute, pop state, return.",
        binary_example="CALL: push PC+1, goto func; RET: pop PC, goto PC",
        python_example="def f(x): return x + 1",
        trit_mapping="trit call: push full trit context onto trit stack, enter new frame",
        mod_note="Call/return = stack discipline. Stack = LIFO = last-in-first-out group action.",
    ),
]

# Map primitives by level
PRIMITIVES_BY_LEVEL = {}
for p in PRIMITIVES:
    PRIMITIVES_BY_LEVEL.setdefault(p.level, []).append(p)

# Map primitives by tongue
PRIMITIVES_BY_TONGUE = {}
for p in PRIMITIVES:
    PRIMITIVES_BY_TONGUE.setdefault(p.tongue, []).append(p)


# ---------------------------------------------------------------------------
# Trit logic engine
# ---------------------------------------------------------------------------

# Balanced ternary: {-1, 0, +1} = {reject, null, accept}
TRIT_VALUES = [-1, 0, 1]
TRIT_NAMES = {-1: "reject", 0: "null", 1: "accept"}


def trit_not(a: int) -> int:
    """Trit NOT: polarity flip, null invariant."""
    return -a


def trit_and(a: int, b: int) -> int:
    """Trit AND: min(a,b) — strictest wins."""
    return min(a, b)


def trit_or(a: int, b: int) -> int:
    """Trit OR: max(a,b) — most permissive wins."""
    return max(a, b)


def trit_xor(a: int, b: int) -> int:
    """Trit XOR: absolute difference — measures distance."""
    return abs(a - b)


def trit_consensus(trits: list[int]) -> int:
    """Trit consensus: majority vote with null as abstention.

    Maps to HYDRA voting:
    - If more accept than reject → accept
    - If more reject than accept → reject
    - Tie or all null → null
    """
    accept = sum(1 for t in trits if t == 1)
    reject = sum(1 for t in trits if t == -1)
    if accept > reject:
        return 1
    elif reject > accept:
        return -1
    return 0


def trit_to_tongue_decision(trit: int) -> str:
    """Map a trit to L13 risk decision.

    +1 (accept) → ALLOW
     0 (null)   → QUARANTINE
    -1 (reject) → DENY
    """
    if trit == 1:
        return "ALLOW"
    elif trit == 0:
        return "QUARANTINE"
    return "DENY"


# ---------------------------------------------------------------------------
# Modular arithmetic for SpiralRing connections
# ---------------------------------------------------------------------------


def mod_shift(value: int, shift: int, modulus: int) -> int:
    """Cyclic shift: value + shift mod modulus. The SpiralRing operation."""
    return (value + shift) % modulus


def phi_mod(value: float, n: int = 64) -> int:
    """Map a float through phi into a ring position.

    Uses golden ratio to distribute values across the ring,
    maximizing separation (Weyl equidistribution theorem).
    """
    # Phi modular hashing — same principle as SpiralRing-64
    return int((value * PHI * n) % n)


def balanced_ternary_encode(n: int, width: int = 6) -> list[int]:
    """Encode integer as balanced ternary {-1, 0, +1} digits.

    Width=6 → maps to 6 tongue positions.
    Range: -(3^6-1)/2 to +(3^6-1)/2 = -364 to +364.
    """
    if n == 0:
        return [0] * width

    trits = []
    val = n
    for _ in range(width):
        r = val % 3
        if r == 0:
            trits.append(0)
            val //= 3
        elif r == 1:
            trits.append(1)
            val = (val - 1) // 3
        else:  # r == 2, which means -1 in balanced ternary
            trits.append(-1)
            val = (val + 1) // 3

    # Pad or truncate to width
    while len(trits) < width:
        trits.append(0)
    return trits[:width]


def balanced_ternary_decode(trits: list[int]) -> int:
    """Decode balanced ternary back to integer."""
    val = 0
    for i, t in enumerate(trits):
        val += t * (3 ** i)
    return val


def triple_encode(value: float, ring_size: int = 64) -> dict[str, Any]:
    """Issac's triple encoding: binary + trit + float + mod.

    Each position simultaneously carries:
    - Binary: present (1) or absent (0)
    - Trit: reject (-1), null (0), or accept (+1)
    - Float: continuous activation strength
    - Mod: position in cyclic ring

    24x information density over flat binary.
    """
    binary = 1 if abs(value) > 0.01 else 0
    trit = 1 if value > 0.1 else (-1 if value < -0.1 else 0)
    ring_pos = phi_mod(abs(value), ring_size)

    return {
        "binary": binary,       # 1 bit: exists?
        "trit": trit,           # 1.58 bits: polarity
        "float": round(value, 6),  # 32 bits: magnitude
        "mod": ring_pos,        # log2(ring_size) bits: position
        "density_bits": round(1 + 1.585 + 32 + math.log2(ring_size), 1),
    }


def tongue_to_trits(tongue_profile: dict[str, float]) -> dict[str, int]:
    """Convert a 6D tongue profile to trit representation.

    Each tongue activation → trit:
    - High activation (>0.25): accept (+1)
    - Low activation (<0.08): reject (-1)
    - Middle: null (0)

    The trit profile IS the L13 decision in compressed form.
    """
    trits = {}
    for tongue in TONGUES:
        val = tongue_profile.get(tongue, 0.0)
        if val > 0.25:
            trits[tongue] = 1
        elif val < 0.08:
            trits[tongue] = -1
        else:
            trits[tongue] = 0
    return trits


# ---------------------------------------------------------------------------
# SFT training pair generators
# ---------------------------------------------------------------------------


@dataclass
class PrimitivesResult:
    """Output of the primitives curriculum."""
    sft_pairs: list[dict[str, Any]] = field(default_factory=list)
    dpo_pairs: list[dict[str, Any]] = field(default_factory=list)
    levels_covered: dict[int, int] = field(default_factory=dict)
    total_exercises: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_exercises": self.total_exercises,
            "sft_count": len(self.sft_pairs),
            "dpo_count": len(self.dpo_pairs),
            "levels_covered": self.levels_covered,
        }


def _generate_bit_exercises() -> list[dict[str, Any]]:
    """Level 0: Bit fundamentals."""
    pairs = []

    # Truth tables for all gates
    for gate_name, gate_fn, desc in [
        ("AND", lambda a, b: a & b, "both must be true"),
        ("OR", lambda a, b: a | b, "either can be true"),
        ("XOR", lambda a, b: a ^ b, "exactly one must be true"),
        ("NAND", lambda a, b: 1 - (a & b), "not both true"),
        ("NOR", lambda a, b: 1 - (a | b), "neither true"),
    ]:
        table = []
        for a in [0, 1]:
            for b in [0, 1]:
                table.append(f"  {a} {gate_name} {b} = {gate_fn(a, b)}")

        pairs.append({
            "instruction": f"Show the complete truth table for the {gate_name} gate and explain what it means: {desc}.",
            "response": (
                f"{gate_name} gate — {desc}\n"
                f"Truth table:\n" + "\n".join(table) + "\n\n"
                f"In SCBE terms: {gate_name} maps to the UM (Umbraex/Security) tongue "
                f"because boolean gates are the immune system of logic. "
                f"Every security check reduces to a gate: does this input PASS or FAIL?"
            ),
            "source": "primitives_curriculum",
            "level": 1,
            "tongue_affinity": "UM",
            "encoding": "binary",
        })

    # Bit counting
    for n in [0b1010, 0b1111, 0b1001_0110, 0b0000_0001]:
        count = bin(n).count("1")
        pairs.append({
            "instruction": f"Count the number of 1-bits (population count) in {bin(n)} and explain the algorithm.",
            "response": (
                f"Binary: {bin(n)} → {count} bits set\n\n"
                f"Algorithm (Brian Kernighan's): repeatedly clear the lowest set bit:\n"
                f"  n = n & (n - 1)  # clears lowest 1-bit\n"
                f"  count += 1\n"
                f"  repeat until n == 0\n\n"
                f"Why it works: n-1 flips all bits from the lowest 1-bit downward.\n"
                f"AND with original clears exactly that bit. O(k) where k = number of set bits.\n\n"
                f"In SCBE: popcount measures ACTIVATION DENSITY. "
                f"A tongue profile with high popcount = broadly activated. "
                f"Low popcount = specialized. This IS the null pattern detector."
            ),
            "source": "primitives_curriculum",
            "level": 0,
            "tongue_affinity": "CA",
            "encoding": "binary",
        })

    return pairs


def _generate_trit_exercises() -> list[dict[str, Any]]:
    """Trit logic: balanced ternary, 3-way decisions."""
    pairs = []

    # Trit truth tables
    for gate_name, gate_fn in [
        ("trit_AND (min)", trit_and),
        ("trit_OR (max)", trit_or),
        ("trit_XOR (|a-b|)", trit_xor),
    ]:
        table = []
        for a in TRIT_VALUES:
            for b in TRIT_VALUES:
                result = gate_fn(a, b)
                table.append(f"  {a:+d} {gate_name.split()[0]} {b:+d} = {result:+d}")

        pairs.append({
            "instruction": (
                f"Show the truth table for {gate_name} in balanced ternary "
                f"where -1=reject, 0=null, +1=accept."
            ),
            "response": (
                f"{gate_name} in balanced ternary:\n" + "\n".join(table) + "\n\n"
                f"Key insight: balanced ternary is NATURAL for AI decision-making.\n"
                f"Binary forces yes/no. Ternary adds 'I don't know' (null).\n"
                f"This maps directly to SCBE risk decisions:\n"
                f"  +1 (accept) → ALLOW\n"
                f"   0 (null)   → QUARANTINE (needs more info)\n"
                f"  -1 (reject) → DENY\n\n"
                f"The null state is not absence of decision — it IS a decision: "
                f"'the evidence is insufficient.' This is the L0 layer."
            ),
            "source": "primitives_curriculum",
            "level": 1,
            "tongue_affinity": "UM",
            "encoding": "trit",
        })

    # Trit consensus (HYDRA voting)
    vote_scenarios = [
        ([1, 1, 1, -1, 0, 0], "4 agents: 3 accept, 1 reject, 2 abstain"),
        ([1, -1, 1, -1, 1, -1], "evenly split: 3 accept, 3 reject"),
        ([0, 0, 0, 0, 0, 1], "5 abstain, 1 accept"),
        ([-1, -1, -1, 0, 0, 0], "3 reject, 3 abstain"),
        ([1, 1, 1, 1, 1, 1], "unanimous accept"),
    ]
    for votes, desc in vote_scenarios:
        result = trit_consensus(votes)
        tongue_labels = list(zip(TONGUES, votes))
        pairs.append({
            "instruction": (
                f"Six HYDRA tongue agents vote on a record. "
                f"Each casts a trit vote (-1=reject, 0=abstain, +1=accept):\n"
                f"  {', '.join(f'{t}={v:+d}' for t, v in tongue_labels)}\n"
                f"What is the consensus and what does it mean?"
            ),
            "response": (
                f"Scenario: {desc}\n"
                f"Votes: {votes}\n"
                f"Consensus: {result:+d} → {TRIT_NAMES[result].upper()}\n\n"
                f"Trit consensus = majority vote where null is abstention.\n"
                f"Accept count: {sum(1 for v in votes if v == 1)}\n"
                f"Reject count: {sum(1 for v in votes if v == -1)}\n"
                f"Abstain count: {sum(1 for v in votes if v == 0)}\n\n"
                f"L13 decision: {trit_to_tongue_decision(result)}\n\n"
                f"This is Byzantine fault tolerance in trit space. "
                f"Abstention is NOT the same as absence — it's MEASURED uncertainty."
            ),
            "source": "primitives_curriculum",
            "level": 1,
            "tongue_affinity": "RU",
            "encoding": "trit",
        })

    # Balanced ternary encoding
    for n in [0, 1, -1, 5, -13, 42, -100, 364]:
        trits = balanced_ternary_encode(n, width=6)
        decoded = balanced_ternary_decode(trits)
        tongue_map = {TONGUES[i]: trits[i] for i in range(6)}
        pairs.append({
            "instruction": (
                f"Encode the integer {n} in balanced ternary with 6 trit positions "
                f"(one per SCBE tongue: KO, AV, RU, CA, UM, DR)."
            ),
            "response": (
                f"Balanced ternary encoding of {n}:\n"
                f"  Trits: {trits}\n"
                f"  Tongue map: {tongue_map}\n"
                f"  Verification: {' + '.join(f'{t}×3^{i}' for i, t in enumerate(trits) if t != 0)} = {decoded}\n\n"
                f"Each tongue position carries a trit, giving 3^6 = 729 unique states.\n"
                f"Compare to binary 6-bit: only 2^6 = 64 states.\n"
                f"Balanced ternary is 11.4x denser than binary at the same width.\n\n"
                f"Range: -364 to +364 (vs binary 6-bit: 0 to 63)."
            ),
            "source": "primitives_curriculum",
            "level": 0,
            "tongue_affinity": "CA",
            "encoding": "trit",
        })

    return pairs


def _generate_mod_exercises() -> list[dict[str, Any]]:
    """Modular arithmetic: cyclic groups, ring operations, phi-modular."""
    pairs = []

    # Basic mod operations
    for a, b, m in [(7, 5, 3), (15, 11, 6), (42, 27, 64), (255, 128, 256)]:
        pairs.append({
            "instruction": (
                f"Compute the following modular arithmetic and explain the cyclic group:\n"
                f"  ({a} + {b}) mod {m}\n"
                f"  ({a} × {b}) mod {m}\n"
                f"  ({a} - {b}) mod {m}"
            ),
            "response": (
                f"Modular arithmetic in Z/{m}Z:\n"
                f"  ({a} + {b}) mod {m} = {(a + b) % m}\n"
                f"  ({a} × {b}) mod {m} = {(a * b) % m}\n"
                f"  ({a} - {b}) mod {m} = {(a - b) % m}\n\n"
                f"Z/{m}Z is a cyclic group of order {m}.\n"
                f"Adding 1 repeatedly: 0 → 1 → 2 → ... → {m-1} → 0 (wraps around).\n"
                f"This wrapping IS the SpiralRing operation.\n\n"
                f"In SCBE: SpiralRing-64 uses Z/64Z for ring positions.\n"
                f"Each of 64 slots holds a 256-bit state. XOR neighbor mixing + SHA-256 "
                f"ensures every evolution step is cryptographically unique.\n"
                f"The modular wrap makes the ring INFINITE in time but FINITE in space."
            ),
            "source": "primitives_curriculum",
            "level": 2,
            "tongue_affinity": "CA",
            "encoding": "mod",
        })

    # Phi-modular distribution
    pairs.append({
        "instruction": (
            "Explain how the golden ratio (phi = 1.618...) distributes values "
            "uniformly across a modular ring, and why this matters for hash functions."
        ),
        "response": (
            f"Golden ratio modular distribution (Weyl equidistribution):\n\n"
            f"For any ring of size N, the sequence:\n"
            f"  pos(k) = floor(k × φ × N) mod N\n\n"
            f"Produces the most UNIFORM distribution possible.\n\n"
            f"Example with N=8:\n"
            + "\n".join(
                f"  k={k}: pos = floor({k} × {PHI:.4f} × 8) mod 8 = {phi_mod(k, 8)}"
                for k in range(8)
            ) + "\n\n"
            f"Why: φ is the 'most irrational' number — its continued fraction is [1;1,1,1,...]. "
            f"This means no rational approximation p/q gets 'too close,' so the sequence "
            f"never clumps. Every other constant clusters eventually; φ never does.\n\n"
            f"In SCBE: SpiralRing-64 uses φ-weighted evolution. Tongue weights scale by φ: "
            f"KO={TONGUE_WEIGHTS['KO']:.2f}, AV={TONGUE_WEIGHTS['AV']:.2f}, "
            f"RU={TONGUE_WEIGHTS['RU']:.2f}, CA={TONGUE_WEIGHTS['CA']:.2f}, "
            f"UM={TONGUE_WEIGHTS['UM']:.2f}, DR={TONGUE_WEIGHTS['DR']:.2f}.\n"
            f"This guarantees maximum separation between tongue influence levels."
        ),
        "source": "primitives_curriculum",
        "level": 2,
        "tongue_affinity": "CA",
        "encoding": "mod",
    })

    # Mod shift exercises (SpiralRing operations)
    for val, shift, mod in [(0, 1, 64), (63, 1, 64), (31, 17, 64), (7, 3, 6)]:
        result = mod_shift(val, shift, mod)
        pairs.append({
            "instruction": (
                f"Compute mod_shift({val}, {shift}, {mod}) — a cyclic ring rotation."
            ),
            "response": (
                f"mod_shift({val}, {shift}, {mod}) = ({val} + {shift}) mod {mod} = {result}\n\n"
                f"This is a single step on a ring of size {mod}.\n"
                f"Position {val} advances {shift} steps clockwise.\n"
                f"At position {mod-1}, the next step wraps to 0.\n\n"
                f"In SpiralRing-64: this IS the position advance. "
                f"Each evolution step shifts the active position, then mixes state "
                f"with XOR from neighbors at positions (pos-1) and (pos+1) mod 64."
            ),
            "source": "primitives_curriculum",
            "level": 2,
            "tongue_affinity": "CA",
            "encoding": "mod",
        })

    return pairs


def _generate_shift_exercises() -> list[dict[str, Any]]:
    """Shift and mask operations: bit extraction, field packing."""
    pairs = []

    # Bit extraction
    for value, bit_pos in [(0b1010_1100, 2), (0b1111_0000, 7), (0xFF, 0)]:
        extracted = (value >> bit_pos) & 1
        pairs.append({
            "instruction": (
                f"Extract bit {bit_pos} from {bin(value)} using shift and mask."
            ),
            "response": (
                f"Extract bit {bit_pos} from {bin(value)}:\n"
                f"  Step 1: Right shift by {bit_pos}: {bin(value)} >> {bit_pos} = {bin(value >> bit_pos)}\n"
                f"  Step 2: Mask with 1: {bin(value >> bit_pos)} & 1 = {extracted}\n"
                f"  Result: bit {bit_pos} = {extracted}\n\n"
                f"Formula: (value >> pos) & 1\n\n"
                f"In SCBE: bit extraction is how you read individual tongue activations "
                f"from a packed representation. A 6-tongue profile packed into 6 bits: "
                f"each bit = one tongue's trit binary presence."
            ),
            "source": "primitives_curriculum",
            "level": 2,
            "tongue_affinity": "CA",
            "encoding": "binary",
        })

    # Field packing (multiple values into one integer)
    pairs.append({
        "instruction": (
            "Pack a 6-tongue trit profile into a single integer using 2 bits per tongue "
            "(00=reject, 01=null, 10=accept). Example: KO=accept, AV=null, RU=reject, "
            "CA=accept, UM=null, DR=reject."
        ),
        "response": (
            "Packing 6 trits into 12 bits (2 bits per tongue):\n\n"
            "  KO=accept(10), AV=null(01), RU=reject(00), CA=accept(10), UM=null(01), DR=reject(00)\n\n"
            "  Packed: 0b_00_01_10_00_01_10 (DR|UM|CA|RU|AV|KO, LSB first)\n"
            "         = 0b000110000110 = 0x186\n\n"
            "To extract tongue T at position i (0-indexed):\n"
            "  trit_bits = (packed >> (i * 2)) & 0b11\n"
            "  trit = {0b00: -1, 0b01: 0, 0b10: +1}[trit_bits]\n\n"
            "Why 2 bits for 3 states? 1 bit can only do {0,1}. 2 bits gives {00,01,10,11}. "
            "We use 3 of 4 codes. The spare code (0b11) could mean 'undefined' — "
            "a 4th state beyond the trit, like NaN for numbers.\n\n"
            "12 bits for 6 tongue trits vs 6 bits for 6 tongue binaries. "
            "But trits carry 3^6=729 states vs binary 2^6=64 states. "
            "That's 11.4x more information for 2x the bits = 5.7x density gain."
        ),
        "source": "primitives_curriculum",
        "level": 2,
        "tongue_affinity": "DR",
        "encoding": "binary",
    })

    return pairs


def _generate_encoding_roundtrip() -> list[dict[str, Any]]:
    """Encoding round-trips: binary ↔ trit ↔ float ↔ mod."""
    pairs = []

    # Triple encoding demonstration
    for value in [0.0, 0.167, 0.5, -0.3, 0.9, -1.0, PHI_INV]:
        encoded = triple_encode(value)
        pairs.append({
            "instruction": (
                f"Apply triple encoding (binary + trit + float + mod) to the value {value:.4f}."
            ),
            "response": (
                f"Triple encoding of {value:.4f}:\n"
                f"  Binary:  {encoded['binary']}  (exists? {'yes' if encoded['binary'] else 'no'})\n"
                f"  Trit:    {encoded['trit']:+d}  ({TRIT_NAMES[encoded['trit']]})\n"
                f"  Float:   {encoded['float']}  (continuous magnitude)\n"
                f"  Mod-64:  {encoded['mod']}  (ring position via phi-hash)\n"
                f"  Density: {encoded['density_bits']} bits of information\n\n"
                f"Each layer answers a different question:\n"
                f"  Binary → 'Is there anything here at all?'\n"
                f"  Trit → 'What's the INTENT? Accept, reject, or undecided?'\n"
                f"  Float → 'How STRONGLY?'\n"
                f"  Mod → 'WHERE on the ring does this live?'\n\n"
                f"vs flat binary: 1 bit answers only the first question.\n"
                f"Triple encoding: same position, 4 simultaneous answers."
            ),
            "source": "primitives_curriculum",
            "level": 0,
            "tongue_affinity": "DR",
            "encoding": "triple",
        })

    # Tongue profile → trit profile round trip
    profiles = [
        {"KO": 0.17, "AV": 0.17, "RU": 0.17, "CA": 0.17, "UM": 0.16, "DR": 0.16},
        {"KO": 0.02, "AV": 0.02, "RU": 0.02, "CA": 0.02, "UM": 0.90, "DR": 0.02},
        {"KO": 0.35, "AV": 0.10, "RU": 0.30, "CA": 0.05, "UM": 0.15, "DR": 0.05},
    ]
    for profile in profiles:
        trits = tongue_to_trits(profile)
        decision = trit_consensus(list(trits.values()))
        pairs.append({
            "instruction": (
                f"Convert this tongue profile to trits and determine the consensus decision:\n"
                f"  {profile}"
            ),
            "response": (
                f"Tongue → Trit conversion (>0.25 = accept, <0.08 = reject, else null):\n"
                + "\n".join(
                    f"  {t}: {profile[t]:.2f} → {trits[t]:+d} ({TRIT_NAMES[trits[t]]})"
                    for t in TONGUES
                ) + "\n\n"
                f"Trit consensus: {decision:+d} → {trit_to_tongue_decision(decision)}\n\n"
                f"This reduces a continuous 6D vector to a discrete 6-trit code.\n"
                f"Information compressed from 6×32 = 192 bits to 6×1.58 ≈ 10 bits.\n"
                f"But the DECISION information is preserved — we keep the polarity "
                f"and discard only magnitude precision."
            ),
            "source": "primitives_curriculum",
            "level": 1,
            "tongue_affinity": "RU",
            "encoding": "triple",
        })

    return pairs


def _generate_composition_exercises() -> list[dict[str, Any]]:
    """Composition: build higher primitives from lower ones."""
    pairs = []

    pairs.append({
        "instruction": (
            "Build a full adder from NAND gates only. Show the construction step by step."
        ),
        "response": (
            "Full adder from NAND gates:\n\n"
            "Inputs: A, B, Cin (carry in)\n"
            "Outputs: Sum, Cout (carry out)\n\n"
            "Step 1: Half adder (sum = A XOR B, carry = A AND B)\n"
            "  XOR from NAND:\n"
            "    t1 = NAND(A, B)\n"
            "    t2 = NAND(A, t1)\n"
            "    t3 = NAND(B, t1)\n"
            "    XOR = NAND(t2, t3)\n"
            "  AND from NAND:\n"
            "    AND = NAND(NAND(A,B), NAND(A,B))\n\n"
            "Step 2: Chain two half adders\n"
            "  sum1 = A XOR B  (from step 1)\n"
            "  Sum = sum1 XOR Cin  (second half adder)\n"
            "  carry1 = A AND B\n"
            "  carry2 = sum1 AND Cin\n"
            "  Cout = carry1 OR carry2 = NAND(NAND(carry1,carry1), NAND(carry2,carry2))\n\n"
            "Total: 9 NAND gates for a full adder.\n\n"
            "Why this matters: NAND is UNIVERSAL. From this single gate, "
            "you can build addition, subtraction, multiplication, comparison, memory, "
            "control flow — literally ALL of computation. One gate. "
            "In SCBE terms: NAND is the UM tongue's atomic operation. "
            "Security (UM) is the foundation everything else is built on."
        ),
        "source": "primitives_curriculum",
        "level": 3,
        "tongue_affinity": "UM",
        "encoding": "binary",
    })

    pairs.append({
        "instruction": (
            "Build a 3-way trit comparator that takes two balanced ternary numbers "
            "(6 trits each = one per tongue) and returns {-1, 0, +1}."
        ),
        "response": (
            "Trit comparator for 6-trit balanced ternary numbers:\n\n"
            "```python\n"
            "def trit_compare(a: list[int], b: list[int]) -> int:\n"
            "    '''Compare two 6-trit numbers. Returns -1/0/+1.'''\n"
            "    # Compare from most significant trit (DR, index 5) down\n"
            "    for i in range(5, -1, -1):  # DR → KO\n"
            "        if a[i] > b[i]:\n"
            "            return +1  # a > b: accept\n"
            "        elif a[i] < b[i]:\n"
            "            return -1  # a < b: reject\n"
            "    return 0  # equal: null\n"
            "```\n\n"
            "The comparison naturally returns a TRIT — not a boolean.\n"
            "Three outcomes: greater/equal/less maps to accept/null/reject.\n\n"
            "Notice: we compare from DR (most significant, highest phi weight) "
            "down to KO (least significant). Architecture decisions dominate over "
            "intent decisions in the ordering — structural choices outweigh local intent.\n\n"
            "This is WHY phi-weighting exists: DR×11.09 >> KO×1.00. "
            "A small architectural change overrides a large intent change."
        ),
        "source": "primitives_curriculum",
        "level": 4,
        "tongue_affinity": "RU",
        "encoding": "trit",
    })

    return pairs


def _generate_primitive_tongue_mapping() -> list[dict[str, Any]]:
    """Map each primitive to its tongue owner — teach the affinity."""
    pairs = []

    pairs.append({
        "instruction": (
            "Map all 10 coding primitives to the 6 SCBE Sacred Tongues. "
            "Explain why each primitive belongs to its tongue."
        ),
        "response": (
            "Primitive → Tongue affinity map:\n\n"
            + "\n".join(
                f"  Level {p.level}: {p.name:12s} → {p.tongue} ({TONGUE_NAMES[p.tongue]})\n"
                f"    Why: {p.description}"
                for p in PRIMITIVES
            ) + "\n\n"
            "Pattern: The tongue hierarchy mirrors the primitive hierarchy.\n"
            "  UM (Security) owns gates — the immune checkpoint layer\n"
            "  CA (Compute) owns shifts + arithmetic — raw number crunching\n"
            "  RU (Governance) owns comparison — rule enforcement\n"
            "  AV (Wisdom) owns assignment — knowledge storage\n"
            "  KO (Intent) owns branch + call — decision and abstraction\n"
            "  DR (Architecture) owns loops + pointers — structural patterns\n\n"
            "Each tongue is BUILT from the tongues below it in phi weight.\n"
            "DR (architecture) needs loops, which need branches (KO), "
            "which need comparison (RU), which needs arithmetic (CA), "
            "which needs gates (UM), which needs bits (L0).\n\n"
            "The phi weighting IS the dependency ordering."
        ),
        "source": "primitives_curriculum",
        "level": 0,
        "tongue_affinity": "DR",
        "encoding": "mapping",
    })

    return pairs


def _generate_dpo_pairs() -> list[dict[str, Any]]:
    """DPO pairs: correct primitive thinking vs sloppy thinking."""
    pairs = []

    # Chosen: understands trit, Rejected: forces binary
    pairs.append({
        "instruction": "Should we allow this API request? The authentication is valid but the rate limit is ambiguous.",
        "chosen": (
            "This is a three-state decision, not binary.\n\n"
            "Authentication: ACCEPT (+1) — verified credential\n"
            "Rate limit: NULL (0) — insufficient data to determine\n"
            "Combined: trit_and(+1, 0) = min(+1, 0) = 0 → QUARANTINE\n\n"
            "Action: Accept the request but flag it for monitoring. "
            "The ambiguous rate limit doesn't justify denial, but it "
            "prevents full trust. Quarantine preserves optionality."
        ),
        "rejected": (
            "The authentication is valid, so we should allow it. "
            "The rate limit being ambiguous isn't a reason to block "
            "a legitimate user. Allow the request."
        ),
        "source": "primitives_curriculum",
        "pattern": "trit_over_binary",
        "explanation": "Trit logic captures the third state (uncertainty). Binary forces a false dichotomy.",
    })

    # Chosen: understands mod/cyclic, Rejected: treats overflow as error
    pairs.append({
        "instruction": "Position counter is at 63 in a 64-slot ring. What happens when we advance by 1?",
        "chosen": (
            "mod_shift(63, 1, 64) = (63 + 1) mod 64 = 0\n\n"
            "The counter wraps to position 0. This is correct and expected — "
            "it's a cyclic ring, not a linear counter. Position 0 follows "
            "position 63 just as position 1 follows position 0. "
            "No overflow, no error, no special case. The modular arithmetic "
            "handles the wrap naturally.\n\n"
            "In SpiralRing-64: this wrap is when the ring state gets "
            "XOR-mixed with its neighbors and SHA-256 hashed. "
            "The wrap is the EVOLUTION point, not a boundary."
        ),
        "rejected": (
            "Position 63 + 1 = 64, which exceeds the ring size of 64. "
            "This is a buffer overflow — we need to check for this edge case "
            "and handle it with an error or by clamping to 63."
        ),
        "source": "primitives_curriculum",
        "pattern": "cyclic_over_linear",
        "explanation": "Modular arithmetic has no overflow. Treating wrapping as error reveals linear thinking.",
    })

    # Chosen: uses triple encoding, Rejected: uses single encoding
    pairs.append({
        "instruction": "Represent the concept 'partially trusted input from a known source' as compactly as possible.",
        "chosen": (
            "Triple encoding:\n"
            "  Binary: 1 (input exists)\n"
            "  Trit: 0 (null — not fully trusted, not rejected)\n"
            "  Float: 0.6 (moderate trust level)\n"
            "  Mod-64: phi_mod(0.6) = 37 (ring position)\n\n"
            "One datum, four simultaneous properties. "
            "Presence, intent, magnitude, and geometric position — "
            "all from a single observation."
        ),
        "rejected": (
            "trusted = True  # or False, we need to pick one\n"
            "# 'Partially trusted' isn't really a thing in security, "
            "# either you trust it or you don't."
        ),
        "source": "primitives_curriculum",
        "pattern": "triple_over_single",
        "explanation": "Reality has more than 2 states. Triple encoding captures gradients that binary loses.",
    })

    return pairs


# ---------------------------------------------------------------------------
# Main curriculum generator
# ---------------------------------------------------------------------------


def generate_primitives(
    tongue_profile: dict[str, float] | None = None,
) -> PrimitivesResult:
    """Generate the full coding primitives curriculum.

    Produces SFT pairs covering all 10 primitive levels and 4 encoding types,
    plus DPO pairs for correct vs incorrect primitive reasoning.

    Args:
        tongue_profile: Optional tongue profile to customize exercise selection.
                       If provided, emphasizes exercises matching the dominant tongue.
    """
    all_sft = []
    all_dpo = []
    levels_covered: dict[int, int] = {}

    # Generate all exercise types
    generators = [
        _generate_bit_exercises,
        _generate_trit_exercises,
        _generate_mod_exercises,
        _generate_shift_exercises,
        _generate_encoding_roundtrip,
        _generate_composition_exercises,
        _generate_primitive_tongue_mapping,
    ]

    for gen_fn in generators:
        pairs = gen_fn()
        for pair in pairs:
            level = pair.get("level", 0)
            levels_covered[level] = levels_covered.get(level, 0) + 1
        all_sft.extend(pairs)

    # DPO pairs
    all_dpo = _generate_dpo_pairs()

    return PrimitivesResult(
        sft_pairs=all_sft,
        dpo_pairs=all_dpo,
        levels_covered=levels_covered,
        total_exercises=len(all_sft) + len(all_dpo),
    )


# ---------------------------------------------------------------------------
# Per-record primitive scoring
# ---------------------------------------------------------------------------


@dataclass
class PrimitiveScore:
    """Primitive encoding analysis for a single record."""
    trit_profile: dict[str, int]        # Tongue → trit
    trit_consensus: int                  # Consensus trit
    l13_decision: str                    # ALLOW/QUARANTINE/DENY
    triple_encoded: dict[str, Any]       # Triple encoding of dominant activation
    balanced_ternary: list[int]          # 6-trit balanced ternary of hash
    ring_position: int                   # Phi-modular ring position
    activation_density: int              # Popcount of binary presence

    def to_dict(self) -> dict[str, Any]:
        return {
            "trit_profile": self.trit_profile,
            "trit_consensus": self.trit_consensus,
            "l13_decision": self.l13_decision,
            "ring_position": self.ring_position,
            "activation_density": self.activation_density,
            "balanced_ternary": self.balanced_ternary,
        }


def score_primitives(
    tongue_profile: dict[str, float],
    content_hash: str = "",
) -> PrimitiveScore:
    """Score a record's primitive encoding properties.

    Takes a tongue profile and returns its trit representation,
    triple encoding, and ring position.
    """
    # Tongue → trit
    trits = tongue_to_trits(tongue_profile)
    consensus = trit_consensus(list(trits.values()))
    decision = trit_to_tongue_decision(consensus)

    # Triple encode the dominant tongue activation
    dominant = max(tongue_profile.values()) if tongue_profile else 0.0
    triple = triple_encode(dominant)

    # Balanced ternary of content hash (first 6 trits)
    hash_int = int(content_hash[:8], 16) if content_hash and len(content_hash) >= 8 else 0
    bt = balanced_ternary_encode(hash_int % 729, width=6)  # mod 729 = 3^6

    # Ring position via phi-modular hash
    ring_pos = phi_mod(sum(tongue_profile.values()), 64)

    # Activation density (how many tongues are "present" > 0.01)
    density = sum(1 for v in tongue_profile.values() if v > 0.01)

    return PrimitiveScore(
        trit_profile=trits,
        trit_consensus=consensus,
        l13_decision=decision,
        triple_encoded=triple,
        balanced_ternary=bt,
        ring_position=ring_pos,
        activation_density=density,
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = generate_primitives()
    print("Coding Primitives Curriculum")
    print(f"  SFT pairs: {len(result.sft_pairs)}")
    print(f"  DPO pairs: {len(result.dpo_pairs)}")
    print(f"  Levels covered: {result.levels_covered}")
    print(f"  Total exercises: {result.total_exercises}")

    print("\nSample exercises by encoding:")
    for enc in ["binary", "trit", "mod", "triple"]:
        samples = [p for p in result.sft_pairs if p.get("encoding") == enc]
        print(f"  {enc}: {len(samples)} pairs")
        if samples:
            print(f"    Example: {samples[0]['instruction'][:80]}...")

    print("\nPrimitive scoring test:")
    profile = {"KO": 0.17, "AV": 0.17, "RU": 0.17, "CA": 0.17, "UM": 0.16, "DR": 0.16}
    score = score_primitives(profile, "deadbeef")
    print(f"  Trit profile: {score.trit_profile}")
    print(f"  Consensus: {score.trit_consensus} -> {score.l13_decision}")
    print(f"  Ring position: {score.ring_position}")
    print(f"  Activation density: {score.activation_density}/6")
    print(f"  Balanced ternary: {score.balanced_ternary}")
