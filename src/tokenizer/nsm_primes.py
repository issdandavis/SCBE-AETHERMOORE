"""
NSM Prime Anchors for the Sacred Tongues Alphabet.

Wierzbicka's ~65 Natural Semantic Metalanguage primes mapped to the six
Sacred Tongue dimensions, each assigned a radial position in the Poincaré
ball and a confidence score.

The phi-extrapolation engine uses the Riemannian exponential map on the
Poincaré ball to derive new prime candidates from known anchors.  Anchor a
known prime at (r, θ) and apply:

    exp_x(v)  where  ‖v‖ = φ · r,  direction = next tongue's phase

to walk the geodesic one phi-step.  If the resulting position in semantic
space maps to a real concept, it's a derived prime.  If not, it's an empty
lattice site — a predicted concept that may not exist in natural language.

Tongue order by phi-weight:
    KO (φ^0, 0°)  AV (φ^1, 60°)  RU (φ^2, 120°)
    CA (φ^3, 180°)  UM (φ^4, 240°)  DR (φ^5, 300°)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI: float = 1.618033988749895
TONGUE_ORDER: list[str] = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_PHASE: dict[str, float] = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}
TONGUE_WEIGHT: dict[str, float] = {t: PHI**i for i, t in enumerate(TONGUE_ORDER)}
POINCARE_EPSILON: float = 1e-6  # keep r strictly inside the open ball

# Grid positions: 16×16 per tongue.  Primary NSM primes occupy rows 0–3,
# derived primes rows 4–7, compound primes rows 8–11, domain tokens 12–15.
GRID_SIZE: int = 16

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

TongueCode = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
CoverageLabel = Literal["primary", "secondary", "cross", "unspanned"]


@dataclass(frozen=True)
class PrimeSpan:
    """Tongue assignment with confidence for one NSM prime."""

    tongue: TongueCode
    confidence: float  # [0, 1]
    note: str = ""


@dataclass(frozen=True)
class NSMPrime:
    """
    One Wierzbicka semantic prime with geometric positioning.

    r         — radial position in the Poincaré ball (0 < r < 1).
                 Fundamental primes sit near r ≈ 0.15–0.35.
                 Derived primes sit further out along the geodesic.
    phi_order — which φ^n level this prime occupies (0 = most atomic).
    grid_row  — row in the 16×16 tongue grid (0–15).
    grid_col  — col in the 16×16 tongue grid (0–15).
    spans     — ordered list of tongue assignments, highest confidence first.
    """

    id: str
    label: str  # canonical Wierzbicka form, e.g. "WANT"
    surface_forms: tuple[str, ...]  # natural language variants
    phi_order: int  # 0 = most atomic
    r: float  # radial Poincaré position in primary tongue's dimension
    grid_row: int
    grid_col: int
    spans: tuple[PrimeSpan, ...]
    note: str = ""

    @property
    def primary_tongue(self) -> TongueCode:
        return self.spans[0].tongue  # type: ignore[return-value]

    @property
    def primary_confidence(self) -> float:
        return self.spans[0].confidence

    @property
    def is_cross_tongue(self) -> bool:
        return len(self.spans) > 1 and self.spans[1].confidence >= 0.25

    @property
    def poincare_theta(self) -> float:
        """Phase angle of the primary tongue in radians."""
        return TONGUE_PHASE[self.primary_tongue]


# ---------------------------------------------------------------------------
# Prime table
# ---------------------------------------------------------------------------

# fmt: off
NSM_PRIMES: tuple[NSMPrime, ...] = (
    # ── KO: Kor'aelin — Control / Intent ────────────────────────────────
    NSMPrime("ko.i",        "I",           ("I", "me", "myself"),                    0, 0.18, 0,  0,
             (PrimeSpan("KO", 1.00, "self-reference is pure intent"),)),
    NSMPrime("ko.you",      "YOU",         ("you", "thou"),                           0, 0.18, 0,  1,
             (PrimeSpan("KO", 1.00, "second-person is pure address"),)),
    NSMPrime("ko.want",     "WANT",        ("want", "desire", "wish"),                0, 0.22, 0,  2,
             (PrimeSpan("KO", 1.00, "want is the pure intent prime"),)),
    NSMPrime("ko.can",      "CAN",         ("can", "be able to"),                     0, 0.24, 0,  3,
             (PrimeSpan("KO", 0.90, "possibility under agent control"),
              PrimeSpan("RU", 0.10, "policy permits"))),
    NSMPrime("ko.not",      "NOT",         ("not", "no", "un-"),                      0, 0.20, 0,  4,
             (PrimeSpan("KO", 0.50, "logical negation of intent"),
              PrimeSpan("RU", 0.30, "policy violation"),
              PrimeSpan("UM", 0.20, "containment / absence")),
             note="hardest to span — genuinely cross-tongue"),
    NSMPrime("ko.maybe",    "MAYBE",       ("maybe", "perhaps", "possibly"),          1, 0.26, 0,  5,
             (PrimeSpan("KO", 0.80, "uncertain intent"),
              PrimeSpan("RU", 0.20, "unresolved policy state"))),
    NSMPrime("ko.if",       "IF",          ("if", "when-conditional"),                1, 0.28, 0,  6,
             (PrimeSpan("KO", 0.60, "conditional intent"),
              PrimeSpan("RU", 0.40, "conditional policy binding"))),
    NSMPrime("ko.do",       "DO",          ("do", "act", "perform"),                  1, 0.30, 0,  7,
             (PrimeSpan("KO", 0.60, "intentional act"),
              PrimeSpan("CA", 0.40, "computational operation")),
             note="cross-tongue: DO-as-agency vs DO-as-computation"),
    NSMPrime("ko.think",    "THINK",       ("think", "believe", "consider"),          1, 0.28, 0,  8,
             (PrimeSpan("KO", 0.70, "thinking as intentional mental act"),
              PrimeSpan("DR", 0.30, "thinking as record of internal states"))),
    NSMPrime("ko.this",     "THIS",        ("this", "here-thing"),                    1, 0.24, 0,  9,
             (PrimeSpan("KO", 0.70, "deictic pointing — intent directed at object"),
              PrimeSpan("UM", 0.30, "this specific contained thing"))),
    NSMPrime("ko.because",  "BECAUSE",     ("because", "therefore", "hence"),         1, 0.30, 0, 10,
             (PrimeSpan("RU", 0.70, "causal binding rule"),
              PrimeSpan("KO", 0.30, "reason for intentional act")),
             note="primary is RU but listed under KO for intent adjacency"),

    # ── AV: Avali — Transport / Messaging ───────────────────────────────
    NSMPrime("av.say",      "SAY",         ("say", "speak", "utter", "tell"),         0, 0.18, 1,  0,
             (PrimeSpan("AV", 0.80, "speech as message transport"),
              PrimeSpan("KO", 0.20, "saying has intentional origin"))),
    NSMPrime("av.words",    "WORDS",       ("words", "language", "speech"),           0, 0.20, 1,  1,
             (PrimeSpan("AV", 0.70, "words are the medium of transport"),
              PrimeSpan("DR", 0.30, "words as record / witness"))),
    NSMPrime("av.see",      "SEE",         ("see", "perceive visually"),              0, 0.18, 1,  2,
             (PrimeSpan("AV", 0.80, "visual information transport"),
              PrimeSpan("DR", 0.20, "seeing as witnessing / record"))),
    NSMPrime("av.hear",     "HEAR",        ("hear", "listen"),                        0, 0.18, 1,  3,
             (PrimeSpan("AV", 1.00, "auditory transport — pure AV"),)),
    NSMPrime("av.move",     "MOVE",        ("move", "go", "travel"),                  0, 0.22, 1,  4,
             (PrimeSpan("AV", 1.00, "movement is core transport"),)),
    NSMPrime("av.touch",    "TOUCH",       ("touch", "contact", "reach"),             0, 0.24, 1,  5,
             (PrimeSpan("AV", 0.60, "physical contact as transport endpoint"),
              PrimeSpan("KO", 0.40, "touch as intentional act"))),
    NSMPrime("av.happen",   "HAPPEN",      ("happen", "occur", "take place"),         1, 0.26, 1,  6,
             (PrimeSpan("AV", 0.70, "event as something transported through time"),
              PrimeSpan("CA", 0.30, "event as state transformation"))),
    NSMPrime("av.here",     "HERE",        ("here", "at this place"),                 1, 0.24, 1,  7,
             (PrimeSpan("AV", 0.80, "reference point in transit space"),
              PrimeSpan("KO", 0.20, "self-located deixis"))),
    NSMPrime("av.where",    "WHERE/PLACE", ("where", "place", "location"),            1, 0.26, 1,  8,
             (PrimeSpan("AV", 0.80, "location in transit space"),
              PrimeSpan("CA", 0.20, "location as coordinate / transform input"))),
    NSMPrime("av.near",     "NEAR",        ("near", "close", "next to"),              1, 0.28, 1,  9,
             (PrimeSpan("AV", 0.80, "proximity in transit space"),
              PrimeSpan("CA", 0.20, "small distance transform"))),
    NSMPrime("av.far",      "FAR",         ("far", "distant", "away"),                1, 0.28, 1, 10,
             (PrimeSpan("AV", 0.80, "distance in transit space"),
              PrimeSpan("CA", 0.20, "large distance transform"))),
    NSMPrime("av.side",     "SIDE",        ("side", "beside", "adjacent"),            2, 0.30, 1, 11,
             (PrimeSpan("AV", 0.60, "lateral adjacency in transit space"),
              PrimeSpan("CA", 0.40, "spatial relative transform"))),
    NSMPrime("av.above",    "ABOVE",       ("above", "over", "on top"),               2, 0.32, 1, 12,
             (PrimeSpan("CA", 0.70, "vertical spatial transform"),
              PrimeSpan("AV", 0.30, "elevation in transit space"))),
    NSMPrime("av.below",    "BELOW",       ("below", "under", "beneath"),             2, 0.32, 1, 13,
             (PrimeSpan("CA", 0.70, "vertical spatial transform"),
              PrimeSpan("AV", 0.30, "descent in transit space"))),

    # ── RU: Runethic — Policy / Binding ─────────────────────────────────
    NSMPrime("ru.good",     "GOOD",        ("good", "right", "correct"),              0, 0.18, 2,  0,
             (PrimeSpan("RU", 0.90, "evaluative policy — what is permitted"),
              PrimeSpan("KO", 0.10, "good as intentionally chosen"))),
    NSMPrime("ru.bad",      "BAD",         ("bad", "wrong", "harmful"),               0, 0.18, 2,  1,
             (PrimeSpan("RU", 0.90, "evaluative policy violation"),
              PrimeSpan("KO", 0.10, "bad as intentionally avoided"))),
    NSMPrime("ru.true",     "TRUE",        ("true", "real", "actual"),                0, 0.20, 2,  2,
             (PrimeSpan("DR", 0.90, "authenticated state — DR, not RU"),
              PrimeSpan("RU", 0.10, "policy of truth-telling")),
             note="primary tongue is DR despite listing position"),
    NSMPrime("ru.all",      "ALL",         ("all", "every", "entire"),                0, 0.22, 2,  3,
             (PrimeSpan("RU", 0.80, "universal binding — all are bound"),
              PrimeSpan("CA", 0.20, "total count / aggregation"))),
    NSMPrime("ru.some",     "SOME",        ("some", "a few", "several"),              0, 0.24, 2,  4,
             (PrimeSpan("RU", 0.60, "partial policy — some are bound"),
              PrimeSpan("CA", 0.40, "partial count"))),
    NSMPrime("ru.because",  "BECAUSE",     ("because", "therefore", "hence"),         1, 0.26, 2,  5,
             (PrimeSpan("RU", 0.70, "causal binding rule"),
              PrimeSpan("KO", 0.30, "causal intent"))),
    NSMPrime("ru.kind_of",  "KIND OF",     ("kind of", "type of", "sort of"),         1, 0.28, 2,  6,
             (PrimeSpan("RU", 0.80, "taxonomic policy — binding of type"),
              PrimeSpan("CA", 0.20, "classification transform"))),
    NSMPrime("ru.part_of",  "PART OF",     ("part of", "component of", "piece of"),   1, 0.28, 2,  7,
             (PrimeSpan("RU", 0.70, "mereological binding"),
              PrimeSpan("AV", 0.30, "part as contained transit node"))),
    NSMPrime("ru.like",     "LIKE/AS/WAY", ("like", "as", "way", "similar"),          2, 0.30, 2,  8,
             (PrimeSpan("CA", 0.90, "similarity transform — core compute"),
              PrimeSpan("RU", 0.10, "similarity as binding rule")),
             note="primary tongue is CA"),

    # ── CA: Cassisivadan — Compute / Transforms ──────────────────────────
    NSMPrime("ca.one",      "ONE",         ("one", "a", "single"),                    0, 0.18, 3,  0,
             (PrimeSpan("CA", 1.00, "unit — the atomic count"),)),
    NSMPrime("ca.two",      "TWO",         ("two", "pair", "both"),                   0, 0.20, 3,  1,
             (PrimeSpan("CA", 1.00, "binary count"),)),
    NSMPrime("ca.much",     "MUCH/MANY",   ("much", "many", "a lot"),                 0, 0.22, 3,  2,
             (PrimeSpan("CA", 0.80, "large quantity transform"),
              PrimeSpan("RU", 0.20, "many as binding over large set"))),
    NSMPrime("ca.little",   "LITTLE/FEW",  ("little", "few", "not much"),             0, 0.22, 3,  3,
             (PrimeSpan("CA", 0.80, "small quantity transform"),
              PrimeSpan("RU", 0.20, "few as minimal binding"))),
    NSMPrime("ca.big",      "BIG",         ("big", "large", "great"),                 0, 0.24, 3,  4,
             (PrimeSpan("CA", 1.00, "size as spatial transform magnitude"),)),
    NSMPrime("ca.small",    "SMALL",       ("small", "little", "tiny"),               0, 0.24, 3,  5,
             (PrimeSpan("CA", 1.00, "small size transform"),)),
    NSMPrime("ca.more",     "MORE",        ("more", "additional", "further"),         0, 0.26, 3,  6,
             (PrimeSpan("CA", 1.00, "increment transform"),)),
    NSMPrime("ca.very",     "VERY",        ("very", "extremely", "so"),               1, 0.28, 3,  7,
             (PrimeSpan("CA", 0.80, "intensity amplification transform"),
              PrimeSpan("KO", 0.20, "very as emphasis of intent"))),
    NSMPrime("ca.same",     "THE SAME",    ("same", "identical", "equal"),            1, 0.28, 3,  8,
             (PrimeSpan("CA", 0.80, "identity transform — no change"),
              PrimeSpan("RU", 0.20, "sameness as binding equivalence"))),
    NSMPrime("ca.other",    "OTHER",       ("other", "different", "else"),            1, 0.30, 3,  9,
             (PrimeSpan("CA", 0.70, "difference / differentiation transform"),
              PrimeSpan("RU", 0.30, "otherness as policy of exclusion"))),
    NSMPrime("ca.thing",    "SOMETHING",   ("something", "thing", "object"),          1, 0.26, 3, 10,
             (PrimeSpan("CA", 0.70, "a thing that can be operated on"),
              PrimeSpan("UM", 0.30, "a thing that can be contained"))),

    # ── UM: Umbroth — Redaction / Privacy / Containment ──────────────────
    NSMPrime("um.inside",   "INSIDE",      ("inside", "within", "interior"),          0, 0.18, 4,  0,
             (PrimeSpan("UM", 1.00, "containment — the pure UM prime"),)),
    NSMPrime("um.have",     "HAVE",        ("have", "possess", "own"),                0, 0.22, 4,  1,
             (PrimeSpan("UM", 0.80, "possession as containment relation"),
              PrimeSpan("DR", 0.20, "have as authenticated ownership record"))),
    NSMPrime("um.there_is", "THERE IS",    ("there is", "exists", "is present"),      0, 0.24, 4,  2,
             (PrimeSpan("UM", 0.70, "existence as presence in the container"),
              PrimeSpan("CA", 0.30, "existence as computable fact"))),
    NSMPrime("um.live",     "LIVE",        ("live", "alive", "exist"),                0, 0.26, 4,  3,
             (PrimeSpan("UM", 0.70, "living as contained biological existence"),
              PrimeSpan("DR", 0.30, "living as temporally continuous record"))),
    NSMPrime("um.die",      "DIE",         ("die", "dead", "cease"),                  0, 0.26, 4,  4,
             (PrimeSpan("UM", 0.70, "death as containment ending"),
              PrimeSpan("DR", 0.30, "death as temporal record termination"))),
    NSMPrime("um.body",     "BODY",        ("body", "physical form", "flesh"),        1, 0.28, 4,  5,
             (PrimeSpan("UM", 0.80, "body as the container of experience"),
              PrimeSpan("AV", 0.20, "body as physical mover in space"))),
    NSMPrime("um.feel",     "FEEL",        ("feel", "sense", "experience"),           1, 0.30, 4,  6,
             (PrimeSpan("UM", 0.70, "feeling as contained inner experience"),
              PrimeSpan("KO", 0.30, "feeling as mental-intentional state")),
             note="genuinely hard to place — inner experience resists externalization"),
    NSMPrime("um.someone",  "SOMEONE",     ("someone", "a person", "somebody"),       1, 0.28, 4,  7,
             (PrimeSpan("KO", 0.80, "someone as intentional agent"),
              PrimeSpan("AV", 0.20, "someone as addressable node")),
             note="primary tongue is KO — listed here for cross-coverage audit"),
    NSMPrime("um.people",   "PEOPLE",      ("people", "persons", "humans"),           1, 0.30, 4,  8,
             (PrimeSpan("DR", 0.70, "people as collective record / witness"),
              PrimeSpan("AV", 0.30, "people as social transit network")),
             note="primary tongue is DR"),

    # ── DR: Draumric — Authentication / Integrity / Record ───────────────
    NSMPrime("dr.know",     "KNOW",        ("know", "knowledge", "aware"),            0, 0.18, 5,  0,
             (PrimeSpan("DR", 0.90, "knowledge as authenticated internal record"),
              PrimeSpan("KO", 0.10, "knowing as intentional mental state"))),
    NSMPrime("dr.true",     "TRUE",        ("true", "real", "actual"),                0, 0.18, 5,  1,
             (PrimeSpan("DR", 0.90, "truth as authenticated state"),
              PrimeSpan("RU", 0.10, "truth as policy requirement"))),
    NSMPrime("dr.words_r",  "WORDS",       ("words", "record", "testimony"),          0, 0.20, 5,  2,
             (PrimeSpan("DR", 0.70, "words as the medium of record / witness"),
              PrimeSpan("AV", 0.30, "words as transport medium")),
             note="DR isotope of WORDS — same surface, different tongue aspect"),
    NSMPrime("dr.now",      "NOW",         ("now", "at this moment", "currently"),    0, 0.22, 5,  3,
             (PrimeSpan("DR", 0.80, "present moment as temporal anchor"),
              PrimeSpan("KO", 0.20, "now as deictic self-reference in time"))),
    NSMPrime("dr.before",   "BEFORE",      ("before", "prior to", "earlier"),        0, 0.24, 5,  4,
             (PrimeSpan("DR", 1.00, "temporal order — pure DR"),)),
    NSMPrime("dr.after",    "AFTER",       ("after", "following", "later"),           0, 0.24, 5,  5,
             (PrimeSpan("DR", 1.00, "temporal sequence — pure DR"),)),
    NSMPrime("dr.when",     "WHEN/TIME",   ("when", "time", "temporal"),              0, 0.26, 5,  6,
             (PrimeSpan("DR", 0.90, "time as the domain of record"),
              PrimeSpan("CA", 0.10, "time as measurable quantity"))),
    NSMPrime("dr.long_time","A LONG TIME", ("a long time", "for ages", "long"),       1, 0.28, 5,  7,
             (PrimeSpan("DR", 0.80, "extended temporal record"),
              PrimeSpan("CA", 0.20, "large time quantity"))),
    NSMPrime("dr.short_time","A SHORT TIME",("a short time", "briefly", "quickly"),   1, 0.28, 5,  8,
             (PrimeSpan("DR", 0.80, "brief temporal record"),
              PrimeSpan("CA", 0.20, "small time quantity"))),
    NSMPrime("dr.for_time", "FOR SOME TIME",("for some time", "a while", "some time"),1, 0.30, 5,  9,
             (PrimeSpan("DR", 0.80, "bounded temporal record"),
              PrimeSpan("RU", 0.20, "time-bound policy"))),
    NSMPrime("dr.moment",   "MOMENT",      ("moment", "instant", "point in time"),    1, 0.26, 5, 10,
             (PrimeSpan("DR", 0.90, "minimal temporal record unit"),
              PrimeSpan("AV", 0.10, "moment as event point"))),
    NSMPrime("dr.people_r", "PEOPLE",      ("people", "folk", "witnesses"),           1, 0.30, 5, 11,
             (PrimeSpan("DR", 0.70, "people as collective witness / record"),
              PrimeSpan("AV", 0.30, "people as social graph"))),
)
# fmt: on

# ---------------------------------------------------------------------------
# Index and lookup
# ---------------------------------------------------------------------------

_BY_ID: dict[str, NSMPrime] = {p.id: p for p in NSM_PRIMES}
_BY_LABEL: dict[str, list[NSMPrime]] = {}
for _p in NSM_PRIMES:
    _BY_LABEL.setdefault(_p.label, []).append(_p)

_BY_TONGUE: dict[str, list[NSMPrime]] = {t: [] for t in TONGUE_ORDER}
for _p in NSM_PRIMES:
    _BY_TONGUE[_p.primary_tongue].append(_p)


def get_prime(prime_id: str) -> NSMPrime | None:
    return _BY_ID.get(prime_id)


def primes_for_tongue(tongue: TongueCode) -> list[NSMPrime]:
    return list(_BY_TONGUE[tongue])


def all_primes() -> tuple[NSMPrime, ...]:
    return NSM_PRIMES


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------


@dataclass
class CoverageReport:
    total: int
    primary_only: int  # confidence >= 0.75 in one tongue
    cross_tongue: int  # meaningful presence in 2+ tongues
    unspanned: int  # no tongue with confidence >= 0.25
    by_tongue: dict[str, int]  # count of primaries per tongue
    cross_pairs: list[tuple[str, str, str]]  # (prime_label, t1, t2)
    unspanned_primes: list[str]
    notes: list[str]


def coverage_report() -> CoverageReport:
    by_tongue: dict[str, int] = {t: 0 for t in TONGUE_ORDER}
    cross_pairs: list[tuple[str, str, str]] = []
    unspanned: list[str] = []
    primary_only = 0
    cross = 0

    for p in NSM_PRIMES:
        by_tongue[p.primary_tongue] = by_tongue.get(p.primary_tongue, 0) + 1
        if p.is_cross_tongue:
            cross += 1
            tongues = [s.tongue for s in p.spans if s.confidence >= 0.25]
            for i in range(len(tongues)):
                for j in range(i + 1, len(tongues)):
                    cross_pairs.append((p.label, tongues[i], tongues[j]))
        elif p.primary_confidence < 0.25:
            unspanned.append(p.label)
        else:
            primary_only += 1

    notes: list[str] = []
    if "NOT" in [p.label for p in NSM_PRIMES if p.is_cross_tongue]:
        notes.append("NOT spans KO/RU/UM — may be a meta-prime above the alphabet level")
    if "FEEL" in [p.label for p in NSM_PRIMES if p.is_cross_tongue]:
        notes.append("FEEL and THINK resist clean assignment — inner experience is genuinely cross-tongue")
    notes.append(
        f"BECAUSE appears under both KO and RU — causal relation is intent AND policy; " f"both isotopes needed"
    )

    return CoverageReport(
        total=len(NSM_PRIMES),
        primary_only=primary_only,
        cross_tongue=cross,
        unspanned=len(unspanned),
        by_tongue=by_tongue,
        cross_pairs=cross_pairs,
        unspanned_primes=unspanned,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Grid position utilities
# ---------------------------------------------------------------------------


def grid_index(row: int, col: int) -> int:
    """Row-major index into a 16×16 tongue grid."""
    assert 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE
    return row * GRID_SIZE + col


def prime_grid_index(prime: NSMPrime) -> int:
    return grid_index(prime.grid_row, prime.grid_col)


def grid_position_for_tongue(tongue: TongueCode) -> dict[int, NSMPrime]:
    """Map grid index → prime for all primaries of a tongue."""
    return {prime_grid_index(p): p for p in primes_for_tongue(tongue)}


# ---------------------------------------------------------------------------
# Phi-extrapolation on the Poincaré ball (Riemannian exponential map)
# ---------------------------------------------------------------------------


def _poincare_exp_map(x: tuple[float, float], v: tuple[float, float]) -> tuple[float, float]:
    """
    Riemannian exponential map on the 2D Poincaré disk.

    exp_x(v) maps tangent vector v at base point x to a point on the disk.
    Uses the formula from hyperbolic neural networks (Ganea et al. 2018):

        exp_x(v) = tanh(tanh⁻¹(‖x‖) + ‖v‖/(1-‖x‖²)) · (x + v·α) / ‖x + v·α‖

    Simplified to 2D polar coordinates for efficiency:
        r_new = tanh(arctanh(r_x) + ‖v‖)
        θ_new = θ_v   (walk in the direction of v)
    """
    x_r = math.sqrt(x[0] ** 2 + x[1] ** 2)
    x_r = min(x_r, 1.0 - POINCARE_EPSILON)

    v_r = math.sqrt(v[0] ** 2 + v[1] ** 2)
    if v_r < POINCARE_EPSILON:
        return x

    # Walk in direction of v by geodesic distance ‖v‖
    new_r = math.tanh(math.atanh(x_r) + v_r)
    new_r = min(new_r, 1.0 - POINCARE_EPSILON)

    # Direction: use v's angle
    v_theta = math.atan2(v[1], v[0])
    return (new_r * math.cos(v_theta), new_r * math.sin(v_theta))


def _proximity_confidence(
    tongue: TongueCode,
    r: float,
    grid_row: int,
    grid_col: int,
    *,
    scale: float = 0.18,
) -> float:
    """Soft confidence for an empty lattice site: exp(-d/scale) to nearest known primary."""
    best = math.inf
    for p in NSM_PRIMES:
        if p.primary_tongue != tongue:
            continue
        dr = abs(p.r - r)
        drow = abs(p.grid_row - grid_row)
        dcol = min(abs(p.grid_col - grid_col), GRID_SIZE - abs(p.grid_col - grid_col))
        dist = dr + (drow + dcol) / GRID_SIZE
        if dist < best:
            best = dist
    return math.exp(-best / scale) if math.isfinite(best) else 0.0


@dataclass(frozen=True)
class PhiExtrapolation:
    """
    One step of geodesic extrapolation from a known prime.

    source_id       — the prime this was derived from
    n               — which phi step (1 = first extrapolation, 2 = second, ...)
    derived_tongue  — tongue at this lattice site
    derived_r       — radial Poincaré position
    derived_theta   — phase angle in radians
    grid_row        — predicted row in derived tongue's 16×16 grid
    grid_col        — predicted col
    candidate_label — human-readable hypothesis for what concept sits here
    confidence      — model confidence in candidate (0 = unknown, 1 = known prime)
    is_known_prime  — True if this position matches an existing NSM prime
    matched_prime   — prime ID if is_known_prime
    """

    source_id: str
    n: int
    derived_tongue: TongueCode
    derived_r: float
    derived_theta: float
    grid_row: int
    grid_col: int
    candidate_label: str
    confidence: float
    is_known_prime: bool = False
    matched_prime: str | None = None


def phi_extrapolate(prime: NSMPrime, steps: int = 3) -> list[PhiExtrapolation]:
    """
    Walk the geodesic from `prime` for `steps` phi-scaled steps.

    At each step:
      - Tongue advances one position in the phi-order cycle (KO→AV→RU→CA→UM→DR→KO)
      - Radial distance scales by phi (in arctanh space = additive)
      - Direction points at the new tongue's phase angle

    After each step, checks whether the derived position matches a known
    NSM prime.  If it does, marks is_known_prime=True.
    """
    results: list[PhiExtrapolation] = []

    tongue_idx = TONGUE_ORDER.index(prime.primary_tongue)
    r = prime.r
    theta = prime.poincare_theta

    # Current position in Cartesian Poincaré disk coordinates
    x = (r * math.cos(theta), r * math.sin(theta))

    for step in range(1, steps + 1):
        # Advance tongue
        tongue_idx = (tongue_idx + 1) % len(TONGUE_ORDER)
        next_tongue: TongueCode = TONGUE_ORDER[tongue_idx]  # type: ignore[assignment]
        next_theta = TONGUE_PHASE[next_tongue]

        # Tangent vector: direction = next tongue's phase, magnitude = phi * r
        step_magnitude = PHI * r
        v = (step_magnitude * math.cos(next_theta), step_magnitude * math.sin(next_theta))

        # Riemannian exponential map
        new_x = _poincare_exp_map(x, v)
        new_r = math.sqrt(new_x[0] ** 2 + new_x[1] ** 2)
        new_theta = math.atan2(new_x[1], new_x[0])

        # Grid position in derived tongue (row = phi_order, col = position within row)
        grid_row = min(int(new_r * GRID_SIZE), GRID_SIZE - 1)
        grid_col = int((new_theta % (2 * math.pi)) / (2 * math.pi) * GRID_SIZE) % GRID_SIZE

        # Check if this matches a known prime
        known_match: NSMPrime | None = None
        for candidate in primes_for_tongue(next_tongue):
            if candidate.grid_row == grid_row and abs(candidate.r - new_r) < 0.08:
                known_match = candidate
                break

        cand_label = known_match.label if known_match else f"[CANDIDATE: {next_tongue}·{step}]"

        results.append(
            PhiExtrapolation(
                source_id=prime.id,
                n=step,
                derived_tongue=next_tongue,
                derived_r=new_r,
                derived_theta=new_theta,
                grid_row=grid_row,
                grid_col=grid_col,
                candidate_label=cand_label,
                confidence=(
                    known_match.primary_confidence
                    if known_match
                    else _proximity_confidence(next_tongue, new_r, grid_row, grid_col)
                ),
                is_known_prime=known_match is not None,
                matched_prime=known_match.id if known_match else None,
            )
        )

        # Update current position for next step
        x = new_x
        r = new_r
        theta = new_theta

    return results


def phi_extrapolate_all(steps: int = 2) -> dict[str, list[PhiExtrapolation]]:
    """Run phi-extrapolation from every NSM prime and return results keyed by prime ID."""
    return {p.id: phi_extrapolate(p, steps=steps) for p in NSM_PRIMES}


def find_empty_lattice_sites(steps: int = 2) -> list[PhiExtrapolation]:
    """
    Return all extrapolated positions that do NOT match a known NSM prime.
    These are predicted semantic concepts not in Wierzbicka's list.
    """
    empty: list[PhiExtrapolation] = []
    for extrapolations in phi_extrapolate_all(steps=steps).values():
        for ex in extrapolations:
            if not ex.is_known_prime:
                empty.append(ex)
    return empty


# ---------------------------------------------------------------------------
# Sub-prime anchors — ratioed phi entry points along a root prime's axis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubPrimeAnchor:
    """
    A semantic position derived from a root prime by φⁿ-ratioed radial scaling.

    Unlike PhiExtrapolation (which cycles tongues), sub-prime anchors stay on
    the root prime's own tongue axis and walk radially outward by powers of φ
    in arctanh space:

        r_n = tanh(arctanh(r₀) × φⁿ)

    This generates a family of deeper primes sharing the root's intentional axis.
    Example from WANT (r₀=0.22, KO tongue):
        n=1 → r≈0.35  (NEED — desire with urgency)
        n=2 → r≈0.53  (COMPEL — drive beyond preference)
        n=3 → r≈0.74  (MUST — drive approaching necessity)
        n=4 → r≈0.91  (INEVITABILITY — boundary of representable desire)

    The "ratioed" framing means sub-prime n is always measured relative to the
    root, not the previous step — making the series a single generative formula.
    """

    root_id: str
    n: int
    tongue: TongueCode
    r: float
    theta: float
    grid_row: int
    grid_col: int
    candidate_label: str
    proximity_confidence: float
    is_known_prime: bool = False
    matched_prime: str | None = None


def generate_subprime_anchors(prime: NSMPrime, steps: int = 4) -> list[SubPrimeAnchor]:
    """
    Generate sub-prime anchors by φⁿ-ratioed scaling from a root prime.

    Each anchor n sits at r_n = tanh(arctanh(r₀) × φⁿ), staying on the root's
    own tongue axis (same θ = tongue phase angle).  The series predicts semantic
    concepts that are "more of the same prime" — stronger, deeper, or more
    abstract versions of the root concept.

    Args:
        prime: The root NSM prime to extrapolate from.
        steps: How many φⁿ sub-prime anchors to generate (default 4).

    Returns:
        List of SubPrimeAnchor, one per step.
    """
    anchors: list[SubPrimeAnchor] = []
    r0 = prime.r
    theta = prime.poincare_theta
    root_arctanh = math.atanh(min(r0, 1.0 - POINCARE_EPSILON))

    for n in range(1, steps + 1):
        scaled_arctanh = root_arctanh * (PHI**n)
        r_n = math.tanh(min(scaled_arctanh, 10.0))
        r_n = min(r_n, 1.0 - POINCARE_EPSILON)

        grid_row = min(int(r_n * GRID_SIZE), GRID_SIZE - 1)
        grid_col = int((theta % (2 * math.pi)) / (2 * math.pi) * GRID_SIZE) % GRID_SIZE

        known_match: NSMPrime | None = None
        for candidate in primes_for_tongue(prime.primary_tongue):
            if candidate.grid_row == grid_row and abs(candidate.r - r_n) < 0.08:
                known_match = candidate
                break

        prox = (
            known_match.primary_confidence
            if known_match
            else _proximity_confidence(prime.primary_tongue, r_n, grid_row, grid_col)
        )

        anchors.append(
            SubPrimeAnchor(
                root_id=prime.id,
                n=n,
                tongue=prime.primary_tongue,
                r=r_n,
                theta=theta,
                grid_row=grid_row,
                grid_col=grid_col,
                candidate_label=known_match.label if known_match else f"[SUB: {prime.label}.phi{n}]",
                proximity_confidence=prox,
                is_known_prime=known_match is not None,
                matched_prime=known_match.id if known_match else None,
            )
        )

    return anchors


__all__ = [
    # Types
    "NSMPrime",
    "PrimeSpan",
    "PhiExtrapolation",
    "SubPrimeAnchor",
    "CoverageReport",
    "TongueCode",
    # Data
    "NSM_PRIMES",
    "TONGUE_ORDER",
    "TONGUE_PHASE",
    "TONGUE_WEIGHT",
    "PHI",
    # Lookups
    "get_prime",
    "primes_for_tongue",
    "all_primes",
    # Analysis
    "coverage_report",
    "grid_position_for_tongue",
    "grid_index",
    "prime_grid_index",
    # Extrapolation
    "phi_extrapolate",
    "phi_extrapolate_all",
    "find_empty_lattice_sites",
    "generate_subprime_anchors",
]
