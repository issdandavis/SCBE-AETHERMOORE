from .._common import _KemAlg

from pathlib import Path
import os


if os.environ.get('LICENSED_HQC', '0') == '0':
	# fmt: off
	from .._util import patent_notice
	patent_notice(['FR2956541B1/US9094189B2/EP2537284B1'],
	              'the HQC cryptosystem', 3,
	              ['https://csrc.nist.gov/csrc/media/Projects/post-quantum-cryptography/documents/round-4/final-ip-statements/HQC-Statements-Round4.pdf']
	)
	# fmt: on


_KemAlg._init_module(Path(__file__).stem, globals())
