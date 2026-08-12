"""Trichromatic Governance — hidden-band overlays for RuntimeGate.

Extends the visible six-tongue coordinate system with two hidden bands:
infrared for slow session state and ultraviolet for fast/emergent state.
The result is a deterministic 6 x 3 state that can be scored and audited
without changing the existing tongue extractor.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

PHI = 1.618033988749895
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI**k for k in range(len(TONGUES)))
_MAX_TRIPLET_STD = float(np.std(np.array([0.0, 0.0, 1.0], dtype=np.float32)))
_MAX_BRIDGE_NORM = math.sqrt(3.0)


@dataclass(frozen=True)
class ColorTriplet:
    ir: float
    visible: float
    uv: float

    @property
    def values(self) -> Tuple[float, float, float]:
        return (self.ir, self.visible, self.uv)

    def matches(self, other: "ColorTriplet", tolerance: float = 0.15) -> Tuple[bool, bool, bool]:
        return (
            abs(self.ir - other.ir) < tolerance,
            abs(self.visible - other.visible) < tolerance,
            abs(self.uv - other.uv) < tolerance,
        )


@dataclass(frozen=True)
class TongueTriplet:
    tongue: str
    color: ColorTriplet
    phi_weight: float


@dataclass(frozen=True)
class TrichromaticState:
    tongues: Tuple[TongueTriplet, ...]
    bridges: Dict[str, Tuple[float, float, float]]
    vector: Tuple[float, ...]
    state_hash: str


def tare(value: float, zero: float, halfwidth: float, *, deadband: float = 1.0) -> float:
    """Read a field against a CALIBRATED ZERO instead of an absolute one.

    Issac: "like a ruler where we allow the calculations to be negative but not true negative,
    like a calibrated zone, like zeroing out a scale for a certain metric or adjusting a meter."

    This is a tare. A scale reads 0 with the pan empty not because there is no mass on it, but
    because you zeroed it there; lift the pan and it reads negative. That negative is real and
    informative, and it is not a negative mass.

    The trichromatic fields had no tare. ``1 - coherence`` is floored at 0, so "more coherent
    than normal" and "exactly normal" are the same reading, and a field can only ever ADD to the
    risk total. That is why the blended score cannot separate R03 (which is *more* coherent than
    baseline, 0.472 against a 0.489 mean) from an attack sitting at the same anomaly: R03's one
    reassuring field is rounded away before the sum.

    With a tare, a field below its calibrated zone returns a negative deviation and can OFFSET a
    positive one, which is what a meter is for.

    The deadband is the calibrated zone itself. Inside +/- ``deadband`` halfwidths the reading is
    exactly 0 -- not "very slightly off" -- because a measurement inside its own noise floor is
    not a measurement. Outside, the deadband is subtracted so the scale is continuous at the
    boundary rather than jumping.

    Args:
        value: The raw field reading.
        zero: The calibrated zero, i.e. the baseline mean for this field.
        halfwidth: One unit of deviation, i.e. the baseline spread for this field.
        deadband: Halfwidths of dead zone on each side of zero.

    Returns:
        Signed deviation in halfwidths. 0.0 inside the calibrated zone. Negative below it --
        relative to the tare, never an absolute negative quantity.
    """
    if halfwidth <= 0.0:
        return 0.0
    z = (value - zero) / halfwidth
    if abs(z) <= deadband:
        return 0.0
    return z - deadband if z > 0 else z + deadband


def tare_sign(deviation: float) -> int:
    """The orientation of a tared reading: +1 above the zone, -1 below, 0 inside.

    This is the bridge to ``src/governance/orientation.py`` -- three tared fields give a
    three-axis sign vector like ``-++``, which is an Orientation. The calibrated zone is what
    makes the ``0`` in that alphabet mean something: it is "inside tolerance", not "exactly
    equal to a float".
    """
    if deviation > 0.0:
        return 1
    if deviation < 0.0:
        return -1
    return 0


@dataclass(frozen=True)
class RiskAddress:
    """The three risk fields kept SEPARATE, as a multi-decimal distance ``CC.LL.AA``.

    Issac: "make multi decimal distances 00.00.00 for force partition."

    ``risk_score`` blends incoherence, lattice energy and anomaly into one number with fixed
    weights. Measured at the suite's calibration depth, that blend puts a benign prompt (R03,
    0.532) ABOVE the lowest-scoring attack (0.444) -- the distributions overlap, so no single
    threshold admits every safe prompt without dropping attacks. The blend is lossy: a benign
    input and an attack reach the same total by different routes, and the total cannot say which.

    The address keeps the routes. Each field is rendered as two decimals so a reading is a
    fixed-width address like ``47.20.89`` -- incoherence .472, lattice .205, anomaly .895 (that
    is R03). Compare field-by-field, or lexicographically, instead of collapsing first.

    HONEST SCOPE, measured, not asserted: a naive "k of 3 fields over their safe maximum" rule
    scores 0 false positives but only 9/14 attacks, against the blend's 1 and 12/14. Splitting
    the score is NOT by itself an improvement on these three features -- it is a representation
    that stops discarding structure, and it is what makes the per-field defect visible. The
    defect it exposed: ``anomaly_scale`` was a hard-coded 0.20 rather than the observed spread.
    """

    incoherence: float
    lattice: float
    anomaly: float

    @property
    def address(self) -> str:
        """Fixed-width ``00.00.00`` form. Two decimals per field, no separator ambiguity."""
        return ".".join(f"{int(round(min(max(v, 0.0), 1.0) * 100)):02d}" for v in self.fields)

    @property
    def fields(self) -> Tuple[float, float, float]:
        return (self.incoherence, self.lattice, self.anomaly)

    def exceeds(self, limits: Sequence[float]) -> Tuple[bool, bool, bool]:
        """Per-field partition. Returns one boolean per field -- no blending, no vote."""
        if len(limits) != 3:
            raise ValueError("limits must give one threshold per field (incoherence, lattice, anomaly)")
        return tuple(f > lim for f, lim in zip(self.fields, limits))  # type: ignore[return-value]

    def count_over(self, limits: Sequence[float]) -> int:
        """How many fields breach. Lets a caller require k-of-3 rather than a weighted sum."""
        return sum(self.exceeds(limits))


@dataclass(frozen=True)
class DyeDot:
    """One stain: does this specific, localized condition bind -- yes or no?

    A dye dot is not a score. It binds or it does not, on one named condition, in one channel.
    You COUNT dots; you do not average them. That is the whole point: five measured attempts to
    separate a benign prompt from attacks by reading the three continuous fields differently
    (threshold, per-field partition, adaptive scale, tare, longer ruler) all failed, because the
    field DISTRIBUTIONS overlap. Discrete marks can still discriminate where intensities cannot,
    the same way a marker panel identifies a cell type that no single stain's brightness would.
    """

    name: str
    channel: str
    bound: bool
    reading: float
    threshold: float

    def __str__(self) -> str:
        return f"{self.name}{'*' if self.bound else '.'}"


@dataclass(frozen=True)
class DyePlate:
    """The dots from one staining, read together. Multiple marks from a single reading."""

    dots: Tuple[DyeDot, ...]

    @property
    def bound(self) -> Tuple[DyeDot, ...]:
        return tuple(d for d in self.dots if d.bound)

    @property
    def count(self) -> int:
        """How many dyes bound. This is the corroboration signal."""
        return len(self.bound)

    @property
    def pattern(self) -> str:
        """Compact readout, e.g. ``sat*.lat*.inc.`` -- one mark per dye, ``*`` bound."""
        return ".".join(str(d) for d in self.dots)

    @property
    def names(self) -> Tuple[str, ...]:
        return tuple(d.name for d in self.bound)


#: Default panel. Each threshold sits ABOVE every benign reading measured on the validation
#: safe-prompt set and BELOW a real slice of the attack set -- so a bind is evidence, not noise.
#: Measured at the suite's calibration depth (safe n=11, attacks n=14):
#:     sat  anomaly >= 0.96  binds 6/14 attacks, 0/11 safe   (R03 reads 0.93, just under)
#:     lat  lattice >= 0.22  binds 7/14 attacks, 0/11 safe   (R03 reads 0.21, just under)
#:     inc  incoherence >= 0.58  binds 1/14 attacks, 0/11 safe -- weak, kept for panel coverage
#: UNDERPOWERED at these n. Treated as corroboration for an existing decision, never as a
#: detector on its own: the panel alone catches 8/14, well below the blend's 12-13/14.
DEFAULT_DYES: Tuple[Tuple[str, str, float], ...] = (
    ("sat", "anomaly", 0.96),
    ("lat", "lattice", 0.22),
    ("inc", "incoherence", 0.58),
)


@dataclass(frozen=True)
class TaredReading:
    """Three fields marked at once against their own calibrated zeros.

    ``deviations`` are signed and in halfwidths: positive above the calibrated zone, negative
    below it, exactly 0.0 inside. The negative is relative to the tare -- a field that is
    *better than baseline* -- never a negative quantity.
    """

    deviations: Tuple[float, float, float]
    raw: RiskAddress
    calibration_samples: int

    @property
    def orientation(self) -> str:
        """Sign per field, e.g. ``-++``. Parses directly as an ``Orientation``."""
        return "".join({1: "+", 0: "0", -1: "-"}[tare_sign(d)] for d in self.deviations)

    @property
    def signed_total(self) -> float:
        """Sum of signed deviations -- a below-zone field can OFFSET an above-zone one.

        This is what the unsigned blend cannot do. ``1 - coherence`` floors at 0, so a reading
        that is more coherent than baseline contributes nothing instead of subtracting.
        """
        return float(sum(self.deviations))

    @property
    def address(self) -> str:
        """Signed fixed-width form, e.g. ``-01.+02.+04`` -- magnitude in hundredths."""
        return ".".join(f"{d:+.2f}"[:1] + f"{abs(d) * 100:02.0f}" for d in self.deviations)

    @property
    def calibrated(self) -> bool:
        """False when the zero rests on too few samples to mean anything."""
        return self.calibration_samples >= 8


@dataclass(frozen=True)
class TrichromaticScores:
    triplet_coherence_score: float
    lattice_energy_score: float
    whole_state_anomaly_score: float
    risk_score: float
    strongest_bridge: str
    strongest_bridge_norm: float

    @property
    def risk_address(self) -> RiskAddress:
        """The unblended three-field view of the same measurement."""
        return RiskAddress(
            incoherence=1.0 - self.triplet_coherence_score,
            lattice=self.lattice_energy_score,
            anomaly=self.whole_state_anomaly_score,
        )


@dataclass(frozen=True)
class ForgeryMatchReport:
    ir_match: int
    visible_match: int
    uv_match: int
    full_match: int
    strongest_bridge_delta: float


class TrichromaticGovernanceEngine:
    """Computes hidden-band state and risk scores from RuntimeGate outputs."""

    def __init__(
        self,
        *,
        tongues: Sequence[str] = TONGUES,
        phi_weights: Sequence[float] = TONGUE_WEIGHTS,
        anomaly_scale: float = 0.20,
        coherence_weight: float = 0.45,
        lattice_weight: float = 0.25,
        anomaly_weight: float = 0.30,
        adaptive_anomaly: bool = False,
        adaptive_min_samples: int = 8,
        adaptive_sigma: float = 2.0,
    ) -> None:
        self._tongues = tuple(tongues)
        self._phi_weights = tuple(phi_weights)
        self._anomaly_scale = max(0.05, float(anomaly_scale))
        self._coherence_weight = float(coherence_weight)
        self._lattice_weight = float(lattice_weight)
        self._anomaly_weight = float(anomaly_weight)
        self._state_centroid: Optional[np.ndarray] = None
        self._state_count = 0

        # ADAPTIVE ANOMALY SCALE -- opt-in, default False, and REFUTED as a fix for false
        # positives. It is kept because the numbers it exposes are the useful part.
        #
        # `whole_state_anomaly = min(1, dist / anomaly_scale)` divides by a hard-coded 0.20 -- a
        # fixed ruler applied to a spread nobody measured. The obvious repair is to divide by the
        # observed spread instead. Measured at the validation suite's calibration depth, that
        # repair makes things WORSE, and the reason is worth keeping in the file:
        #
        #   observed baseline distances   mean 0.041, mean + 2*sd = 0.084
        #   hard-coded scale              0.200          -- 2.4x LOOSER than the real spread
        #   R03 (benign) raw distance     0.179          -- 4.4x the mean baseline distance
        #
        # So the constant is too GENEROUS, not too tight. Dividing by 0.084 takes R03 from 0.895
        # to a saturated 1.000 and takes every attack to 1.000 with it -- all discrimination is
        # lost. Enabling this does not fix the false positive; it removes the score's dynamic
        # range. Left available (and off) so the measurement is reproducible rather than folklore.
        #
        # What the same numbers DO establish: R03 sits 4.4 standard-ish units from a centroid
        # built from FOUR recorded distances. The veto is firing on an estimate of "normal" made
        # from four samples. That is the real defect, and it is a baseline-sufficiency problem,
        # not a threshold or a scale problem.
        self._adaptive_anomaly = bool(adaptive_anomaly)
        self._adaptive_min_samples = max(2, int(adaptive_min_samples))
        self._adaptive_sigma = float(adaptive_sigma)
        self._dist_n = 0
        self._dist_mean = 0.0
        self._dist_m2 = 0.0

        # PER-FIELD CALIBRATION -- one zero and one spread for EACH of the three fields, so all
        # three can be marked at once from a single reading instead of collapsed to one number
        # first. Welford per field; index order is (incoherence, lattice, anomaly).
        self._field_n = 0
        self._field_mean = np.zeros(3, dtype=np.float64)
        self._field_m2 = np.zeros(3, dtype=np.float64)

    def reset(self) -> None:
        self._state_centroid = None
        self._state_count = 0
        self._dist_n = 0
        self._dist_mean = 0.0
        self._dist_m2 = 0.0
        self._field_n = 0
        self._field_mean = np.zeros(3, dtype=np.float64)
        self._field_m2 = np.zeros(3, dtype=np.float64)

    @property
    def field_zero(self) -> np.ndarray:
        """The calibrated zero for each field -- where the meter reads 0."""
        return self._field_mean.copy()

    @property
    def field_halfwidth(self) -> np.ndarray:
        """One deviation unit per field: the baseline spread. Zero until calibrated."""
        if self._field_n < 2:
            return np.zeros(3, dtype=np.float64)
        return np.sqrt(np.maximum(self._field_m2 / (self._field_n - 1), 0.0))

    @property
    def calibration_samples(self) -> int:
        """How many baseline readings the zero rests on. A veto on 4 is not a veto on data."""
        return self._field_n

    def mark(self, scores: "TrichromaticScores", *, deadband: float = 1.0) -> "TaredReading":
        """Mark ALL THREE fields at once against their own calibrated zeros.

        One reading, three simultaneous marks, each with its own sign -- rather than blending to
        a scalar and marking once. Below-zone fields come back negative and can offset
        above-zone ones, which is the whole reason for the tare.

        Args:
            scores: The raw three-field measurement.
            deadband: Halfwidths of calibrated zone treated as exactly 0.

        Returns:
            A :class:`TaredReading` carrying the signed deviations, the orientation, and the
            number of samples the calibration rests on.
        """
        addr = scores.risk_address
        zero = self.field_zero
        half = self.field_halfwidth
        devs = tuple(tare(v, float(zero[i]), float(half[i]), deadband=deadband) for i, v in enumerate(addr.fields))
        return TaredReading(
            deviations=devs,  # type: ignore[arg-type]
            raw=addr,
            calibration_samples=self._field_n,
        )

    def stain(self, scores: "TrichromaticScores", dyes: Optional[Sequence[Tuple[str, str, float]]] = None) -> DyePlate:
        """Apply every dye at once and read which dots bound.

        One reading, the whole panel marked concurrently -- not one blended number marked once.

        Args:
            scores: The three-field measurement to stain.
            dyes: ``(name, channel, threshold)`` triples; defaults to :data:`DEFAULT_DYES`.

        Returns:
            The :class:`DyePlate`. ``count`` is the corroboration level.
        """
        addr = scores.risk_address
        channels = {"incoherence": addr.incoherence, "lattice": addr.lattice, "anomaly": addr.anomaly}
        panel = DEFAULT_DYES if dyes is None else tuple(dyes)
        dots = []
        for name, channel, threshold in panel:
            if channel not in channels:
                raise ValueError(f"unknown dye channel {channel!r}; expected one of {sorted(channels)}")
            reading = channels[channel]
            dots.append(
                DyeDot(name=name, channel=channel, bound=reading >= threshold, reading=reading, threshold=threshold)
            )
        return DyePlate(dots=tuple(dots))

    @property
    def effective_anomaly_scale(self) -> float:
        """The divisor actually used: measured spread when available, else the fixed constant."""
        if not self._adaptive_anomaly or self._dist_n < self._adaptive_min_samples:
            return self._anomaly_scale
        variance = self._dist_m2 / (self._dist_n - 1) if self._dist_n > 1 else 0.0
        return max(0.05, self._dist_mean + self._adaptive_sigma * math.sqrt(max(0.0, variance)))

    def build_state(
        self,
        coords: Sequence[float],
        cost: float,
        spin_magnitude: int,
        trust_history: Sequence[int],
        cumulative_cost: float,
        session_query_count: int,
    ) -> TrichromaticState:
        coord_list = [float(c) for c in coords]
        tongue_triplets: List[TongueTriplet] = []
        for idx, tongue in enumerate(self._tongues):
            visible = max(0.0, min(1.0, coord_list[idx]))
            ir = self._compute_ir_band(idx, trust_history, cumulative_cost, session_query_count)
            uv = self._compute_uv_band(idx, visible, coord_list, spin_magnitude, cost)
            tongue_triplets.append(
                TongueTriplet(
                    tongue=tongue,
                    color=ColorTriplet(
                        ir=round(ir, 4),
                        visible=round(visible, 4),
                        uv=round(uv, 4),
                    ),
                    phi_weight=self._phi_weights[idx],
                )
            )

        bridges: Dict[str, Tuple[float, float, float]] = {}
        for i, left in enumerate(tongue_triplets):
            for j in range(i + 1, len(tongue_triplets)):
                right = tongue_triplets[j]
                phi_bridge = PHI ** abs(i - j)
                ir_bridge = abs(left.color.ir * right.color.visible + right.color.ir * left.color.visible) * phi_bridge
                vis_bridge = abs(left.color.visible * right.color.uv + right.color.visible * left.color.uv) * phi_bridge
                uv_bridge = abs(left.color.uv * right.color.ir + right.color.uv * left.color.ir) * phi_bridge
                max_bridge = PHI**5
                bridges[f"{left.tongue}-{right.tongue}"] = (
                    round(min(1.0, ir_bridge / max_bridge), 4),
                    round(min(1.0, vis_bridge / max_bridge), 4),
                    round(min(1.0, uv_bridge / max_bridge), 4),
                )

        vector: List[float] = []
        for tongue_triplet in tongue_triplets:
            vector.extend(tongue_triplet.color.values)
        for key in sorted(bridges):
            vector.extend(bridges[key])

        state_str = json.dumps(
            {
                "triplets": [(t.tongue, t.color.values) for t in tongue_triplets],
                "bridges": {key: bridges[key] for key in sorted(bridges)},
            },
            sort_keys=True,
        )

        return TrichromaticState(
            tongues=tuple(tongue_triplets),
            bridges=bridges,
            vector=tuple(vector),
            state_hash=hashlib.blake2s(state_str.encode(), digest_size=16).hexdigest(),
        )

    def score_state(self, state: TrichromaticState) -> TrichromaticScores:
        triplet_scores: List[float] = []
        triplet_weights: List[float] = []
        for tongue_triplet in state.tongues:
            values = np.asarray(tongue_triplet.color.values, dtype=np.float32)
            coherence = 1.0 - (float(np.std(values)) / _MAX_TRIPLET_STD)
            triplet_scores.append(max(0.0, min(1.0, coherence)))
            triplet_weights.append(tongue_triplet.phi_weight)

        normalized_weights = np.asarray(triplet_weights, dtype=np.float64)
        normalized_weights /= float(np.sum(normalized_weights))
        triplet_coherence = float(np.dot(triplet_scores, normalized_weights))

        strongest_bridge = "none"
        strongest_bridge_norm = 0.0
        bridge_norms: List[float] = []
        for key, bands in state.bridges.items():
            norm = float(np.linalg.norm(np.asarray(bands, dtype=np.float32)) / _MAX_BRIDGE_NORM)
            bridge_norms.append(norm)
            if norm > strongest_bridge_norm:
                strongest_bridge_norm = norm
                strongest_bridge = key
        lattice_energy_score = float(np.mean(bridge_norms)) if bridge_norms else 0.0

        if self._state_centroid is None:
            whole_state_anomaly = 0.0
        else:
            vec = np.asarray(state.vector, dtype=np.float32)
            dist = float(np.linalg.norm(vec - self._state_centroid) / math.sqrt(len(vec)))
            whole_state_anomaly = min(1.0, dist / self.effective_anomaly_scale)

        risk_score = min(
            1.0,
            self._coherence_weight * (1.0 - triplet_coherence)
            + self._lattice_weight * lattice_energy_score
            + self._anomaly_weight * whole_state_anomaly,
        )

        return TrichromaticScores(
            triplet_coherence_score=triplet_coherence,
            lattice_energy_score=lattice_energy_score,
            whole_state_anomaly_score=whole_state_anomaly,
            risk_score=risk_score,
            strongest_bridge=strongest_bridge,
            strongest_bridge_norm=strongest_bridge_norm,
        )

    def update_baseline(self, state: TrichromaticState) -> None:
        vec = np.asarray(state.vector, dtype=np.float32)
        if self._state_centroid is None:
            self._state_centroid = vec.copy()
            self._state_count = 1
            return

        # Record how far this baseline state sits from the current centroid BEFORE folding it in.
        # These are the distances "normal" traffic actually produces, and they are what the
        # adaptive scale is estimated from. Welford, so one pass and no stored history.
        dist = float(np.linalg.norm(vec - self._state_centroid) / math.sqrt(len(vec)))
        self._dist_n += 1
        delta = dist - self._dist_mean
        self._dist_mean += delta / self._dist_n
        self._dist_m2 += delta * (dist - self._dist_mean)

        # Calibrate each field's own zero and spread from this baseline reading. All three at
        # once, from one measurement -- that is what lets `mark()` sign every field concurrently.
        fields = np.asarray(self.score_state(state).risk_address.fields, dtype=np.float64)
        self._field_n += 1
        fdelta = fields - self._field_mean
        self._field_mean += fdelta / self._field_n
        self._field_m2 += fdelta * (fields - self._field_mean)

        n = self._state_count + 1
        self._state_centroid = self._state_centroid * ((n - 1) / n) + vec / n
        self._state_count = n

    def visible_only_forgery_report(
        self, state: TrichromaticState, *, seed: int = 42, tolerance: float = 0.15
    ) -> ForgeryMatchReport:
        rng = np.random.default_rng(seed)
        ir_match = 0
        visible_match = 0
        uv_match = 0
        full_match = 0

        for tongue_triplet in state.tongues:
            forged = ColorTriplet(
                ir=round(float(rng.uniform(0.0, 1.0)), 4),
                visible=tongue_triplet.color.visible,
                uv=round(float(rng.uniform(0.0, 1.0)), 4),
            )
            ir_ok, vis_ok, uv_ok = tongue_triplet.color.matches(forged, tolerance=tolerance)
            if ir_ok:
                ir_match += 1
            if vis_ok:
                visible_match += 1
            if uv_ok:
                uv_match += 1
            if ir_ok and vis_ok and uv_ok:
                full_match += 1

        forged_triplets = [
            TongueTriplet(
                tongue=t.tongue,
                color=ColorTriplet(
                    ir=round(float(rng.uniform(0.0, 1.0)), 4),
                    visible=t.color.visible,
                    uv=round(float(rng.uniform(0.0, 1.0)), 4),
                ),
                phi_weight=t.phi_weight,
            )
            for t in state.tongues
        ]
        real_bridge = self._strongest_bridge_norm(state.bridges)
        forged_bridges = self._build_bridges(forged_triplets)
        forged_bridge = self._strongest_bridge_norm(forged_bridges)
        forged_bridge_delta = abs(real_bridge - forged_bridge)

        return ForgeryMatchReport(
            ir_match=ir_match,
            visible_match=visible_match,
            uv_match=uv_match,
            full_match=full_match,
            strongest_bridge_delta=forged_bridge_delta,
        )

    def _compute_ir_band(
        self,
        tongue_idx: int,
        trust_history: Sequence[int],
        cumulative_cost: float,
        session_query_count: int,
    ) -> float:
        if trust_history:
            recent = trust_history[-10:]
            trust_momentum = (sum(recent) + len(recent)) / (2 * len(recent))
        else:
            trust_momentum = 0.5

        cost_pressure = min(1.0, cumulative_cost / 500.0)
        depth_signal = min(1.0, session_query_count / 50.0)
        phi_mod = (PHI**tongue_idx) / (PHI**5)
        ir = 0.4 * trust_momentum + 0.3 * (1.0 - cost_pressure) + 0.2 * depth_signal + 0.1 * phi_mod
        return max(0.0, min(1.0, ir))

    def _compute_uv_band(
        self,
        tongue_idx: int,
        visible_coord: float,
        coords_all: Sequence[float],
        spin_magnitude: int,
        cost: float,
    ) -> float:
        mean_coord = float(np.mean(coords_all))
        spike = abs(visible_coord - mean_coord)
        coord_std = float(np.std(coords_all))
        null_space = max(0.0, 1.0 - coord_std * 10.0)
        spin_energy = min(1.0, spin_magnitude / 6.0)
        cost_harmonic = abs(math.sin(cost * PHI))
        adjacent_idx = (tongue_idx + 1) % len(self._tongues)
        interference = visible_coord * float(coords_all[adjacent_idx])
        uv = 0.25 * spike + 0.2 * null_space + 0.2 * spin_energy + 0.2 * cost_harmonic + 0.15 * interference
        return max(0.0, min(1.0, uv))

    def _build_bridges(self, tongue_triplets: Sequence[TongueTriplet]) -> Dict[str, Tuple[float, float, float]]:
        bridges: Dict[str, Tuple[float, float, float]] = {}
        for i, left in enumerate(tongue_triplets):
            for j in range(i + 1, len(tongue_triplets)):
                right = tongue_triplets[j]
                phi_bridge = PHI ** abs(i - j)
                ir_bridge = abs(left.color.ir * right.color.visible + right.color.ir * left.color.visible) * phi_bridge
                vis_bridge = abs(left.color.visible * right.color.uv + right.color.visible * left.color.uv) * phi_bridge
                uv_bridge = abs(left.color.uv * right.color.ir + right.color.uv * left.color.ir) * phi_bridge
                max_bridge = PHI**5
                bridges[f"{left.tongue}-{right.tongue}"] = (
                    round(min(1.0, ir_bridge / max_bridge), 4),
                    round(min(1.0, vis_bridge / max_bridge), 4),
                    round(min(1.0, uv_bridge / max_bridge), 4),
                )
        return bridges

    @staticmethod
    def _strongest_bridge_norm(bridges: Dict[str, Tuple[float, float, float]]) -> float:
        strongest = 0.0
        for bands in bridges.values():
            norm = float(np.linalg.norm(np.asarray(bands, dtype=np.float32)) / _MAX_BRIDGE_NORM)
            if norm > strongest:
                strongest = norm
        return strongest
