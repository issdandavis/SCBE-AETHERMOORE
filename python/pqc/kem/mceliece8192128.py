from .._common import _KemAlg

from pathlib import Path


_KemAlg._init_module(Path(__file__).stem, globals())
