# AetherBrowser -- SCBE-Secured Web Browser

**Version:** 1.0.0
**Author:** Derived from SCBE-AETHERMOORE by Issac Davis
**License:** See SCBE-AETHERMOORE LICENSE

## Overview

AetherBrowser is the security layer for an SCBE (Spectral Context Bound Encryption) secured web browser. Rather than building a browser engine from scratch, AetherBrowser provides a cryptographically-grounded security wrapper that integrates with existing engines (Servo, Chromium, etc.) to enforce trust-aware browsing through hyperbolic geometry and harmonic scaling.

The core insight from SCBE: **adversarial intent costs exponentially more the further it drifts from safe operation**, making attacks computationally infeasible. AetherBrowser applies this principle to every web request, content evaluation, and navigation decision.

## Architecture

```
+-----------------------------------------------------------------------+
|                        AetherBrowser Security Layer                    |
|                                                                        |
|  +---------------------+  +---------------------+  +----------------+ |
|  |  SCBESecurityLayer   |  |  TrustZoneManager   |  | SacredTongue   | |
|  |                     |  |                     |  | Filter         | |
|  |  - classify_request |  |  Zones:             |  |                | |
|  |  - compute_trust    |  |   CORE (origin)     |  | 6 Tongues:     | |
|  |  - verify_certs     |  |   INNER (near)      |  |  KO: Intent    | |
|  |  - harmonic_wall    |  |   OUTER (mid)       |  |  AV: Transport | |
|  |                     |  |   WALL (boundary)   |  |  RU: Perms     | |
|  +---------------------+  +---------------------+  |  CA: Compute   | |
|                                                     |  UM: Privacy   | |
|  +------------------------------------------------+ |  DR: Schema    | |
|  |           Poincare Ball Trust Model             | +----------------+ |
|  |                                                  |                  |
|  |  origin (0,0) = max trust                       |                  |
|  |  boundary (r->1) = min trust                    |                  |
|  |  d_H grows exponentially near boundary          |                  |
|  +------------------------------------------------+                  |
+-----------------------------------------------------------------------+
        |                    |                    |
        v                    v                    v
   [Servo/Chromium]    [Network Stack]     [Content Pipeline]
```

## Key Concepts

### Poincare Ball Trust Model

Domains are mapped to points inside a Poincare ball (hyperbolic disc of curvature -1). The origin represents maximum trust; the boundary represents maximum risk. Hyperbolic distance grows exponentially near the boundary, naturally creating an escalating cost for adversarial behaviour.

```
Trust Score = 1 / (1 + d_H(domain_point, origin))
```

Where `d_H` is the Poincare ball distance:

```
d_H(u, v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
```

### Trust Zones

Four concentric zones in the Poincare ball:

| Zone  | Radius Range | Description                            |
|-------|-------------|----------------------------------------|
| CORE  | r < 0.2     | Bookmarks, explicitly trusted sites    |
| INNER | r < 0.5     | Authenticated, session-verified sites  |
| OUTER | r < 0.8     | General web (default for new domains)  |
| WALL  | r >= 0.8    | Blocked, malicious, policy-violating   |

Domains can be **promoted** toward CORE (with accumulated evidence) or **demoted** toward WALL (immediately, upon violation).

### Six Sacred Tongues Content Analysis

Each request is analysed across six security dimensions, derived from the SCBE Sacred Tongue framework:

| Tongue | Code | Security Dimension       | Checks                                      |
|--------|------|-------------------------|----------------------------------------------|
| Kor'aelin    | KO | Intent analysis         | Is the page doing what it claims?            |
| Avali        | AV | Transport security      | Is the connection secure and authentic?      |
| Runethic     | RU | Permission checking     | Does the page have permission for resources? |
| Cassisivadan | CA | Computation safety      | Is the page running safe scripts?            |
| Umbroth      | UM | Privacy protection      | Is the page leaking user data?               |
| Draumric     | DR | Schema validation       | Does the page structure match expectations?  |

Scores are combined using **phi-weighted composite scoring** (Golden Ratio PHI = 1.618...), giving highest weight to intent analysis (KO) and decreasing weight through schema validation (DR).

### Harmonic Wall

The Harmonic Wall prevents runaway redirect/iframe nesting by applying an escalating cost function:

```
cost(depth) = 1 + ALPHA * tanh(BETA * depth)
```

This is bounded in [1, 1+ALPHA], monotonically increasing, and follows a tanh saturation curve. Requests exceeding the cost limit are blocked.

### Governance Decisions

Three decision tiers (from SCBE Layer 13):

| Decision    | Risk Range      | Action                        |
|-------------|----------------|-------------------------------|
| ALLOW       | risk < 0.3     | Proceed normally              |
| QUARANTINE  | 0.3 <= risk < 0.7 | Sandbox / warn user        |
| DENY        | risk >= 0.7    | Block outright                |

## Project Structure

```
aether-browser/
  README.md                          # This file
  src/
    config.py                        # Constants, enums, default configuration
    scbe_security_layer.py           # Core security classes
  tests/
    test_scbe_security_layer.py      # 103 comprehensive tests
```

## Components

### `config.py`

All constants, enums, and default configuration values:

- Mathematical constants (PHI, PI, harmonic ratios)
- AETHERMOORE-derived constants (PHI_AETHER, LAMBDA_ISAAC, etc.)
- Poincare ball geometry parameters
- Trust zone thresholds and defaults
- Sacred Tongue weights and descriptions
- Harmonic Wall parameters
- HTTP method risk weights
- Certificate verification parameters

### `scbe_security_layer.py`

Three main classes:

**`SCBESecurityLayer`** -- Main security wrapper
- `classify_request(url, origin, method, content_signals)` -> `Decision`
- `compute_trust_score(domain)` -> `float` (0, 1] via Poincare ball distance
- `verify_certificate_chain(certs)` -> `bool` using Sacred Tongue coherence
- `apply_harmonic_wall(request_depth)` -> `float` cost value
- `is_blocked_by_wall(request_depth)` -> `bool`

**`TrustZoneManager`** -- Domain trust zone management
- `get_zone(domain)` -> `TrustZone` classification
- `promote_domain(domain, evidence)` -> `TrustZone` (move toward CORE)
- `demote_domain(domain, reason)` -> `TrustZone` (move toward WALL)
- `get_record(domain)` -> `DomainRecord` or `None`
- `list_domains_in_zone(zone)` -> `List[str]`

**`SacredTongueFilter`** -- Content filtering via Six Tongues
- `analyze_page(url, content_signals)` -> `Dict[str, float]` per-tongue coherence
- `composite_score(tongue_scores)` -> `float` phi-weighted composite

### Helper Functions

Stdlib-only Poincare ball geometry (no numpy):
- `_poincare_distance_nd(u, v)` -- n-dimensional hyperbolic distance
- `_poincare_distance_1d(r_u, r_v)` -- radial-axis distance
- `_domain_to_vector(domain, dims)` -- deterministic domain-to-ball mapping
- `_clamp_to_ball(r)` -- boundary safety

## Usage

```python
from scbe_security_layer import SCBESecurityLayer, Decision

layer = SCBESecurityLayer()

# Classify a web request
decision = layer.classify_request(
    url="https://example.com/page",
    origin="https://example.com",
    method="GET",
)
assert decision == Decision.ALLOW

# Compute trust score
trust = layer.compute_trust_score("example.com")
print(f"Trust: {trust:.3f}")  # Trust: 0.950

# Verify certificate chain
valid = layer.verify_certificate_chain(["leaf-cert", "intermediate", "root"])
print(f"Chain valid: {valid}")

# Check Harmonic Wall
cost = layer.apply_harmonic_wall(depth=3)
blocked = layer.is_blocked_by_wall(depth=3)
print(f"Cost at depth 3: {cost:.2f}, blocked: {blocked}")

# Content analysis with Sacred Tongue signals
signals = {
    "hsts": True,
    "cert_valid": True,
    "has_csp": True,
    "uses_eval": False,
    "third_party_trackers": 0,
}
decision = layer.classify_request(
    url="https://safe-site.com",
    method="GET",
    content_signals=signals,
)
```

## Running Tests

```bash
# From the aether-browser directory
python -m pytest tests/test_scbe_security_layer.py -v

# Or with unittest directly
python -m unittest tests.test_scbe_security_layer -v
```

All 103 tests cover:
- Configuration constants and mathematical invariants (14 tests)
- Poincare ball geometry helpers (18 tests)
- TrustZoneManager zone management (12 tests)
- SacredTongueFilter content analysis (18 tests)
- SCBESecurityLayer classification and security (23 tests)
- Integration tests combining all components (7 tests)
- Mathematical property verification (4 tests)

## Dependencies

**Zero external dependencies.** All code uses only Python standard library:
- `math` -- trigonometric and hyperbolic functions
- `hashlib` -- SHA-256 for domain hashing and certificate fingerprinting
- `dataclasses` -- structured data types
- `typing` -- type annotations
- `urllib.parse` -- URL parsing
- `enum` -- enumerations
- `time` -- timestamps for domain tracking

## Relationship to SCBE-AETHERMOORE

This project implements a browser-specific application of concepts from the SCBE-AETHERMOORE framework:

| SCBE Concept | AetherBrowser Application |
|-------------|--------------------------|
| Poincare ball model (L5-L7) | Domain trust scoring |
| Harmonic scaling (L12) | Redirect/iframe depth cost |
| Sacred Tongues / Langues metric (L3-L4) | Content analysis dimensions |
| Risk decisions (L13) | ALLOW / QUARANTINE / DENY |
| Governance realms (L8) | Trust zones (CORE/INNER/OUTER/WALL) |
| Golden Ratio weighting | Phi-weighted composite scoring |
| Certificate chain integrity | Sacred Tongue coherence validation |
