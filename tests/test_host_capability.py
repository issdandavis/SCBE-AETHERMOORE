"""host_capability: the AetherDesk boot check -- certify what THIS box can actually run, instead of
claiming it runs anywhere. Pure capability-mapping is tested deterministically; live probes are
checked for shape only (they depend on the machine)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.host_capability import (  # noqa: E402
    certify,
    probe_resources,
    probe_toolchains,
    render,
    runnable_capabilities,
)


def test_runnable_mapping_reflects_present_toolchains():
    tc = {"python": True, "node": True, "rustc": True, "cc": False, "go": False}
    r = runnable_capabilities(tc, models={})
    assert r["cross_face_verify"] == ["python", "javascript", "rust"]  # cc/go absent -> excluded
    assert r["cross_face_count"] == 3
    assert r["llm_climber"] is False  # no models


def test_python_is_always_a_face_and_llm_needs_a_model():
    bare = runnable_capabilities({"python": True}, models={})
    assert bare["cross_face_verify"] == ["python"]  # python is always runnable
    withmodel = runnable_capabilities({"python": True}, models={"ollama": {"available": True}})
    assert withmodel["llm_climber"] is True


def test_probe_toolchains_reports_python_and_bools():
    tc = probe_toolchains()
    assert tc["python"] is True
    assert all(isinstance(tc[t], bool) for t in ("node", "rustc", "cc", "go"))


def test_resources_are_sane():
    res = probe_resources()
    assert res["cpu_count"] >= 1
    assert res["free_disk_gb"] > 0
    assert res["ram_gb"] is None or res["ram_gb"] > 0  # None = OS would not report it (honest)


def test_certify_is_serializable_and_honest():
    cert = certify(probe_network=False)  # no network -> deterministic
    assert cert["schema"] == "aetherdesk_host_capability_v1"
    assert cert["toolchains"]["python"] is True
    assert "python" in cert["runnable"]["cross_face_verify"]
    assert cert["models"] == {}  # we skipped the probe, and we don't pretend otherwise
    json.dumps(cert)  # must be JSON-serializable for the shell to consume
    assert "HOST CAPABILITY" in render(cert) and "-->" in render(cert)
