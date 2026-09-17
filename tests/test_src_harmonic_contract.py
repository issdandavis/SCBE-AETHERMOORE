"""Bound the src variant explicitly; the legacy package shares its import name."""

import json
from pathlib import Path
import subprocess
import sys


def test_src_probe_terminates_and_commitments_bind_context():
    module = Path(__file__).resolve().parents[1] / "src/symphonic_cipher/flat_slope_encoder.py"
    # A subprocess timeout turns a recurrence of the PROBE infinite loop into
    # a test failure rather than stranding the complete CI worker.
    script = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location('src_flat_slope', sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
key = bytes(range(32))
results = []
for domain in ('KO', 'AV'):
    for mode in module.ModalityMask:
        fp = module.derive_harmonic_mask(42, key, modality=mode, domain=domain)
        results.append({'domain': domain, 'mode': mode.value,
                        'harmonics': sorted(fp.harmonics),
                        'commitment': fp.key_commitment.hex()})
print(json.dumps(results))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(module)],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    rows = json.loads(result.stdout)
    assert len(rows) == 8
    assert len({row["commitment"] for row in rows}) == 8
    for row in rows:
        if row["mode"] == "probe":
            assert row["harmonics"] == [1]
        else:
            assert 4 <= len(row["harmonics"]) <= 8
