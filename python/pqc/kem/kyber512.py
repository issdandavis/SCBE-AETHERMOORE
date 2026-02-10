from .._common import _KemAlg

import os
from pathlib import Path


if os.environ.get('LICENSED_KYBER', '0') == '0':
	# fmt: off
	from .._util import patent_notice
	patent_notice(['FR2956541A1/US9094189B2/EP2537284B1', 'US9246675/EP2837128B1', 'potential unknown others'],
		      'the Kyber cryptosystem', 1, [
		      'https://ntruprime.cr.yp.to/faq.html',
		      'https://csrc.nist.gov/csrc/media/Projects/post-quantum-cryptography/documents/selected-algos-2022/nist-pqc-license-summary-and-excerpts.pdf',
		      'https://groups.google.com/a/list.nist.gov/g/pqc-forum/c/G0DoD7lkGPk/m/d7Zw0qhGBwAJ',
		      'https://datatracker.ietf.org/meeting/116/proceedings#pquip:~:text=Patents%20and%20PQC',
		      'https://mailarchive.ietf.org/arch/msg/pqc/MS92cuZkSRCDEjpPP90s2uAcRPo/']
	)
	# fmt: on


_KemAlg._init_module(Path(__file__).stem, globals())
