# Wolfram universality & complexity → the 256 Sacred-Tongue tokens

**Module:** `python/scbe/wolfram_face.py` · **Status:** research + reference implementation

## The idea in one line
Stephen Wolfram's **256 elementary cellular automata** and a Sacred Tongue's
**256-token (16×16) grid** are both exactly 8-bit spaces — so token byte `b`
*is* Wolfram **Rule `b`**, giving every token a new **"Wolfram face"**: its
cellular-automaton rule and complexity class.

## Wolfram's research (the part we map)
- **Elementary cellular automata (ECA):** 1-D, 2-state, nearest-neighbour. Each
  rule sets the next-state bit for all 2³ = 8 neighbourhoods → an 8-bit
  "Wolfram code", so there are exactly **256** of them.
- **Four complexity classes** (*A New Kind of Science*; MathWorld):
  - **Class I** — collapses to a single homogeneous state (order).
  - **Class II** — settles into stable or periodic structures (repetition / nesting).
  - **Class III** — chaotic / pseudo-random. **Rule 30** is the icon (Wolfram used it as a PRNG).
  - **Class IV** — localized structures that interact in complex ways: the **"edge of chaos."**
- **Universality:** **Rule 110** (Class IV) is **proven Turing-complete** (Cook).
  Under the ECA symmetry group it equals rules **124, 137, 193** — the four
  "universal tokens." Wolfram conjectures *every* genuinely Class IV rule is universal.
- **Principle of Computational Equivalence (PCE):** almost any process whose
  behaviour isn't obviously simple is computationally *equivalent* — as powerful
  as anything else. **Computational irreducibility:** for such rules there's no
  shortcut; you must run them step by step to see what they do.

## The mapping
| Wolfram | SCBE |
|---|---|
| Rule code 0–255 (8 bits) | token byte / 16×16 grid index 0–255 |
| 4 complexity classes | a `class` field on every token's Wolfram face |
| Rule 110 universality | tokens **110, 124, 137, 193** = "universal tokens" |
| computational irreducibility | a token whose dynamics can't be shortcut |

`wolfram_face.token_rule(i)` → `{rule, class, class_name, universal, wolfram_code_bits}`.
`render(rule)` draws the space-time diagram (e.g. Rule 110 from a single seed).

## Class census across the 256 tokens (this implementation)
| Class | Tokens |
|-------|--------|
| I — homogeneous (order) | 30 |
| II — periodic (repetition) | 201 |
| III — chaotic (pseudo-random) | 19 |
| IV — complex (edge of chaos) | 6 |

This matches Wolfram's qualitative finding: **most rules are simple (I+II), few
are chaotic, very few are complex.** Iconic anchors verify: 0/255 → I, 30 → III,
110 → IV, and the universal family 110/124/137/193 → IV.

## How classes are assigned (and the honest caveats)
Classes are **simulated**, not looked up: each rule is evolved from a *random*
seed on an **odd-width ring (63)** for 600 steps. Homogeneous → I; settles into a
cycle within the run → II; never repeats (chaotic on a 2⁶³ space) → III; the
canonical complex/universal rules are **pinned** to IV.

Caveats, stated plainly:
- **Wolfram's own classification is qualitative/visual** — automated classifiers
  disagree at the margins. This is a principled heuristic, not gospel.
- **Class III ↔ IV** detection is the hard part; that's why the complex/universal
  rules are pinned from the literature rather than auto-detected.
- **Additive/linear rules (90, 150)** are a known boundary case — nested,
  Sierpinski-like order vs. apparent randomness. Here Rule 90 lands in **II**
  (it cycles on the finite ring); many texts call it III. Wolfram notes additive
  rules' "randomness" is special and less complex than true Class III chaos.
- Random seed + **odd** width is deliberate: a power-of-two width makes additive
  rules collapse to zero — an artifact that would mislabel them Class I.

## Why this matters for SCBE
- Every token now carries a **dynamics signature** beside its tongue / chem /
  governance / role faces — one more decoder of the same bijective cube.
- **Class IV / universal tokens** (110, 124, 137, 193) are tokens that are, by
  PCE, tiny universal computers — a natural "maximally expressive" marker.
- Complexity class is a governance-relevant signal: Class III/IV tokens are
  computationally irreducible (unpredictable without running them), exactly the
  kind of thing a safety gate should treat with more suspicion than a Class I/II
  token whose behaviour is trivially bounded.

## Sources
- [Elementary Cellular Automaton — Wolfram MathWorld](https://mathworld.wolfram.com/ElementaryCellularAutomaton.html)
- [A New Kind of Science (online) — More Cellular Automata](https://www.wolframscience.com/nks/p60--more-cellular-automata/)
- [Wolfram code — Wikipedia](https://en.wikipedia.org/wiki/Wolfram_code)
- [The 256 Rules — Stanford Encyclopedia of Philosophy (Cellular Automata)](https://plato.stanford.edu/entries/cellular-automata/supplement.html)
- [Announcing the Rule 30 Prizes — Stephen Wolfram](https://writings.stephenwolfram.com/2019/10/announcing-the-rule-30-prizes/)
- Cook, M. *Universality in Elementary Cellular Automata* (Rule 110 Turing-completeness).
