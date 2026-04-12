"""Sacred Tongue -> code language mapping for multi-path coding.

Each Sacred Tongue carries a phi-weighted character. The mapping below
pairs each tongue with a code language whose syntactic and semantic
character matches that tongue's role in the Langues Weighting System.

This is the primitive the multipath coder needs: one input -> six
parallel transpilations, each driven by the tongue's offset-spin
oscillator from phi_phase.run_six_tongues.

If a tongue->language pairing turns out wrong, change it here only --
nothing downstream hard-codes the values.
"""

# Tongue weight = phi^(l-1). Heavier tongues get heavier-syntax languages.
TONGUE_LANG = {
    "KO": "python",  # Kor'aelin    weight 1.000  - high-level, expressive
    "AV": "typescript",  # Avali        weight 1.618  - structured, typed JS
    "RU": "rust",  # Runethic     weight 2.618  - compiled, ownership-strict
    "CA": "c",  # Cassisivadan weight 4.236  - low-level, manual memory
    "UM": "julia",  # Umbroth      weight 6.854  - scientific, multi-dispatch
    "DR": "haskell",  # Draumric     weight 11.090 - pure functional, lazy
}

LANG_TONGUE = {v: k for k, v in TONGUE_LANG.items()}

# File extension hints for emitted multi-path code stubs.
LANG_EXT = {
    "python": ".py",
    "typescript": ".ts",
    "rust": ".rs",
    "c": ".c",
    "julia": ".jl",
    "haskell": ".hs",
}
