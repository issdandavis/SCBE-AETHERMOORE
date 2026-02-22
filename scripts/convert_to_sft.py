#!/usr/bin/env python3
"""
Backward-compatible wrapper for SCBE SFT conversion.

Primary entrypoint now lives in:
    symphonic_cipher.scbe_aethermoore.convert_to_sft:main
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from symphonic_cipher.scbe_aethermoore.convert_to_sft import main


if __name__ == "__main__":
    main()
