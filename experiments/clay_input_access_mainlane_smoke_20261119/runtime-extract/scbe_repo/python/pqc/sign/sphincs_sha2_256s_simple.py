from .._common import _SigAlg

from pathlib import Path

_SigAlg._init_module(Path(__file__).stem, globals())
