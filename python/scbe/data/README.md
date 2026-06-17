# Vendored data

## chem_wep_smi.csv

Controlled-substances screening list, vendored verbatim from the ChemCrow
project's `ControlChemCheck` safety tool:

- Upstream: https://github.com/ur-whitelab/chemcrow-public
  (`chemcrow/data/chem_wep_smi.csv`)
- License: MIT (Copyright (c) 2023 Andrew White)
- Citation: Bran, A., Cox, S., Schilter, O., Baldassari, C., White, A. D.,
  Schwaller, P. "ChemCrow: Augmenting large-language models with chemistry
  tools." (2023). arXiv:2304.05376
- Columns: `cas`, `source`, `smiles` — CAS numbers and SMILES of chemicals
  controlled under international chemical-weapons schedules, with the
  controlling source per row.

Used by `python/scbe/controlled_substances.py` for DEFENSIVE screening only:
inputs matching (or closely resembling, Tanimoto > 0.35) a listed chemical are
refused at the governed packet boundary. Nothing in this repository
synthesizes from, expands, or enumerates this list.
