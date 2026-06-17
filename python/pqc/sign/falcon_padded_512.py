from .._common import _SigAlg

from pathlib import Path
import os


if os.environ.get('LICENSED_FALCON', '0') == '0':
	# fmt: off
	from .._util import patent_notice
	patent_notice(['US7308097B2'],
	            'the Falcon cryptosystem', 2,
	            ['https://csrc.nist.gov/csrc/media/Projects/post-quantum-cryptography/documents/selected-algos-2022/final-ip-statements/Falcon-Statements-final.pdf#page=20']
	)
	# fmt: on


_SigAlg._init_module(Path(__file__).stem, globals())
