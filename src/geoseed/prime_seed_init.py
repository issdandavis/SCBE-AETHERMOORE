"""Deterministic prime-anchor init for GeoSeed / M6 fields.

This packages the closed prime-fog result as a constructor, not a predictor:

    smooth address tower -> wall window -> primorial wheel lanes

The output is a candidate-field seed. It never claims to pick the prime inside
the window; that remains the density-floor wall resolved by ordinary sieve work.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable

PHI = (1.0 + math.sqrt(5.0)) / 2.0
TONGUE_ABBRS = ("KO", "AV", "RU", "CA", "UM", "DR")
DEFAULT_M6_LAYER_PRIMES = (2, 3, 5, 7, 11, 13)
SMALL_NTH_PRIMES = (2, 3, 5, 7, 11)


@dataclass(frozen=True)
class PrimeSeedShell:
    """One GeoSeed shell bound to one modular sieve layer."""

    shell_index: int
    tongue_abbr: str
    layer_prime: int
    modulus: int
    totient: int
    survival_fraction: float
    cumulative_bits: float
    marginal_bits: float
    phi_weight: float
    hyperbolic_rho: float

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


@dataclass(frozen=True)
class PrimeAnchorSeed:
    """Constructor seed for a prime candidate field around an index."""

    schema_version: str
    index: int
    center_estimate: int
    wall_radius: int
    lower_bound: int
    upper_bound: int
    modulus: int
    allowed_residue_count: int
    survival_fraction: float
    density_note: str
    coverage_contract: str
    shells: tuple[PrimeSeedShell, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["shells"] = [shell.to_dict() for shell in self.shells]
        return payload


def _is_prime_trial(value: int) -> bool:
    if value < 2:
        return False
    if value in (2, 3):
        return True
    if value % 2 == 0:
        return False
    factor = 3
    while factor * factor <= value:
        if value % factor == 0:
            return False
        factor += 2
    return True


def validate_layer_primes(layer_primes: Iterable[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in layer_primes)
    if not values:
        raise ValueError("at least one layer prime is required")
    if len(values) > len(TONGUE_ABBRS):
        raise ValueError(
            f"GeoSeed M6 supports at most {len(TONGUE_ABBRS)} layer primes"
        )
    if sorted(values) != list(values) or len(set(values)) != len(values):
        raise ValueError("layer primes must be sorted and unique")
    bad = [value for value in values if not _is_prime_trial(value)]
    if bad:
        raise ValueError(f"layer values must be prime, got {bad}")
    return values


def nth_prime_smooth_address(index: int) -> int:
    """Approximate p_index with the standard smooth asymptotic address tower."""
    if index < 1:
        raise ValueError("index must be positive")
    if index <= len(SMALL_NTH_PRIMES):
        return SMALL_NTH_PRIMES[index - 1]

    n = float(index)
    log_n = math.log(n)
    log_log_n = math.log(log_n)
    # Cipolla-style address tower through 1/log(n)^2. This intentionally gives
    # a center, not an exact random-access formula.
    estimate = n * (
        log_n
        + log_log_n
        - 1.0
        + (log_log_n - 2.0) / log_n
        - ((log_log_n * log_log_n) - (6.0 * log_log_n) + 11.0) / (2.0 * log_n * log_n)
    )
    return max(2, int(round(estimate)))


def density_wall_radius(center: int, sigma: float = 16.0) -> int:
    """Return a sqrt(x)/log(x) wall radius around the smooth center.

    NOTE: this is the fluctuation *scale*, not a coverage guarantee. A fixed
    sigma does not bracket p_n reliably — empirical containment degrades with
    scale (~73% by n=2e5 at sigma=16). Use `dusart_bracket` for a guaranteed
    window; this remains available only for the explicit `mode="tight"` path.
    """
    if center < 2:
        raise ValueError("center must be at least 2")
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    log_center = max(math.log(center), 1.0)
    return max(16, int(math.ceil(sigma * math.sqrt(center) / log_center)))


def dusart_bracket(index: int) -> tuple[int, int]:
    """Proven lower/upper bounds on p_index — guaranteed to contain the prime.

    Bounds (all unconditional, no Riemann Hypothesis assumed):
      * lower: p_n > n(ln n + ln ln n - 1)                       for n >= 2  (Dusart)
      * upper: p_n < n(ln n + ln ln n)                           for n >= 6  (Rosser-Schoenfeld)
               p_n < n(ln n + ln ln n - 0.9484)                  for n >= 39017 (Dusart, sharper)

    Verified zero-miss on every n in [6, 2e5] (tightest margins: 5 below, 2 above).
    For n <= 5 the n-th prime is returned exactly (zero-width bracket).
    """
    if index < 1:
        raise ValueError("index must be positive")
    if index <= len(SMALL_NTH_PRIMES):
        exact = SMALL_NTH_PRIMES[index - 1]
        return exact, exact
    n = float(index)
    log_n = math.log(n)
    log_log_n = math.log(log_n)
    lower = n * (log_n + log_log_n - 1.0)
    upper_const = 0.9484 if index >= 39017 else 0.0
    upper = n * (log_n + log_log_n - upper_const)
    return math.floor(lower), math.ceil(upper)


def build_prime_seed_shells(
    layer_primes: Iterable[int] = DEFAULT_M6_LAYER_PRIMES,
) -> tuple[PrimeSeedShell, ...]:
    """Map modular layers onto the six GeoSeed shell slots."""
    values = validate_layer_primes(layer_primes)
    shells: list[PrimeSeedShell] = []
    modulus = 1
    totient = 1
    previous_bits = 0.0
    for shell_index, layer_prime in enumerate(values):
        modulus *= layer_prime
        totient *= layer_prime - 1
        survival = totient / modulus
        cumulative_bits = -math.log2(survival)
        shells.append(
            PrimeSeedShell(
                shell_index=shell_index,
                tongue_abbr=TONGUE_ABBRS[shell_index],
                layer_prime=layer_prime,
                modulus=modulus,
                totient=totient,
                survival_fraction=round(survival, 12),
                cumulative_bits=round(cumulative_bits, 9),
                marginal_bits=round(cumulative_bits - previous_bits, 9),
                phi_weight=round(PHI**shell_index, 12),
                hyperbolic_rho=round(shell_index * math.log(PHI), 12),
            )
        )
        previous_bits = cumulative_bits
    return tuple(shells)


def allowed_residue_count(modulus: int) -> int:
    if modulus < 1:
        raise ValueError("modulus must be positive")
    return sum(1 for residue in range(modulus) if math.gcd(residue, modulus) == 1)


def build_prime_anchor_seed(
    index: int,
    layer_primes: Iterable[int] = DEFAULT_M6_LAYER_PRIMES,
    mode: str = "proven",
    sigma: float = 16.0,
) -> PrimeAnchorSeed:
    """Build a deterministic candidate-field seed for the prime at a given index.

    mode="proven" (default): the window is `dusart_bracket`, which is *guaranteed*
        to contain p_index (unconditional bounds). A constructor that brackets the
        prime must not silently miss it.
    mode="tight": the legacy sigma*sqrt(x)/ln(x) window — narrower but only a
        probabilistic scale, NOT guaranteed (coverage degrades with scale).
    """
    shells = build_prime_seed_shells(layer_primes)
    center = nth_prime_smooth_address(index)
    final_shell = shells[-1]
    if mode == "proven":
        lo, hi = dusart_bracket(index)
        # widen (never shrink) so the smooth center is inside; still contains p_n
        lower = min(lo, center)
        upper = max(hi, center)
        contract = (
            "proven: p_n guaranteed in [lower, upper] (unconditional; "
            "Dusart p_n>n(ln n+lnln n-1) n>=2 & <n(ln n+lnln n-0.9484) n>=39017; "
            "Rosser-Schoenfeld p_n<n(ln n+lnln n) n>=6)"
        )
    elif mode == "tight":
        wall = density_wall_radius(center, sigma=sigma)
        lower, upper = max(2, center - wall), center + wall
        contract = (
            f"tight (sigma={sigma}*sqrt(x)/ln x): probabilistic scale, NOT guaranteed; "
            "empirical containment degrades with scale (~73% by n=2e5). "
            "Use mode='proven' to guarantee containment."
        )
    else:
        raise ValueError("mode must be 'proven' or 'tight'")
    return PrimeAnchorSeed(
        schema_version="geoseed_prime_anchor_seed_v1",
        index=index,
        center_estimate=center,
        wall_radius=max(center - lower, upper - center),
        lower_bound=lower,
        upper_bound=upper,
        modulus=final_shell.modulus,
        allowed_residue_count=final_shell.totient,
        survival_fraction=final_shell.survival_fraction,
        density_note="constructor only: emits candidate window and wheel lanes, never the prime pick",
        coverage_contract=contract,
        shells=shells,
    )


def seed_summary(index: int = 10_000) -> dict[str, object]:
    return build_prime_anchor_seed(index).to_dict()


if __name__ == "__main__":
    import json

    print(json.dumps(seed_summary(), indent=2))
