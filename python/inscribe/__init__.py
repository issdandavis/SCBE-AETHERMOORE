"""inscribe — compact numerics for agentic code work.

Three small, exact tools (standalone, stdlib only):

- **ratios** — inscribe a value as a compact ratio (continued-fraction convergents):
  few integers, high accuracy (pi -> 355/113 to ~3e-7).
- **extrapolate** — reconstruct a polynomial relationship *exactly* from a few
  samples and predict far points with zero error (bounded coefficient notation).
- **tokens** — bijective numeration: set a token series as your "number set" and it
  IS a number system; decode -> operate -> encode (any Sacred-Tongues grid plugs in).

    from python.inscribe import inscribe, ladder, extrapolate, TokenNumbers
    inscribe(3.14159265)["ratio"]            # (best p/q within the denom bound)
    extrapolate([(0,0),(1,1),(2,4)], 10)     # -> 100  (x^2 reconstructed from 3 points)
    tn = TokenNumbers("KO AV RU CA UM DR".split())
    tn.decode(tn.add(tn.encode(7), tn.encode(8)))   # -> 15  (arithmetic on token series)
"""

from .extrapolate import evaluate, extrapolate, fit_polynomial, reconstruction_error
from .ratios import continued_fraction, convergents, inscribe, ladder
from .tokens import TokenNumbers, bijective_decode, bijective_encode

__all__ = [
    "inscribe",
    "ladder",
    "continued_fraction",
    "convergents",
    "fit_polynomial",
    "evaluate",
    "extrapolate",
    "reconstruction_error",
    "bijective_encode",
    "bijective_decode",
    "TokenNumbers",
]
