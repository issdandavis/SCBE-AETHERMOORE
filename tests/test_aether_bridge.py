"""aether_bridge: the localhost gate between the AetherDesktop extension and the governed Colab
registry. Tests the pure decide() governance, transcript persistence, and the real HTTP surface
(token-gated, governed, sealed) -- the extension only ever EXECUTES on an ALLOWED verdict.
"""

import json
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "colab"))
sys.path.insert(0, str(ROOT))

import aether_bridge as B  # noqa: E402
from python.scbe.colab_actions import colab_registry  # noqa: E402


def test_decide_governs_each_action():
    reg = colab_registry()
    assert B.decide(reg, "colab_read_output", {"cell_index": 1}, None)["decision"] == "ALLOWED"
    assert B.decide(reg, "colab_run_cell", {"cell_index": 1}, None)["decision"] == "NEEDS_CONFIRM"
    assert B.decide(reg, "colab_run_cell", {"cell_index": 1}, "ok")["decision"] == "ALLOWED"
    bad = B.decide(reg, "colab_inject_and_run", {"code": "shutil.rmtree('/')"}, "x")
    assert bad["decision"] == "REFUSED" and "next" in bad


def test_append_transcript_writes_a_sealed_line(tmp_path):
    reg = colab_registry()
    rec = B.decide(reg, "colab_read_output", {"cell_index": 2}, None)
    out = tmp_path / "transcript.jsonl"
    B.append_transcript(rec, out)
    line = json.loads(out.read_text(encoding="utf-8").strip())
    assert line["action"] == "colab_read_output" and len(line["seal"]) == 64


def test_self_test_passes():
    assert B._self_test() == 0


def _req(url, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    if token is not None:
        r.add_header("X-Aether-Token", token)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_http_surface_is_token_gated_and_governed():
    httpd, token, _ = B.build_server(port=8788)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        base = "http://127.0.0.1:8788"
        # no token -> 401
        code, _ = _req(base + "/actions", token=None)
        assert code == 401
        # with token -> the governed action catalog
        code, payload = _req(base + "/actions", token)
        assert code == 200 and {a["name"] for a in payload["actions"]} >= {"colab_run_cell", "colab_inject_and_run"}
        # govern a guarded action: needs confirm, then allowed
        code, rec = _req(base + "/govern", token, "POST", {"action": "colab_run_cell", "params": {"cell_index": 3}})
        assert rec["decision"] == "NEEDS_CONFIRM"
        code, rec = _req(
            base + "/govern", token, "POST", {"action": "colab_run_cell", "params": {"cell_index": 3}, "confirm": "ok"}
        )
        assert rec["decision"] == "ALLOWED" and len(rec["seal"]) == 64
        # a destructive inject is REFUSED through the HTTP surface too
        code, rec = _req(
            base + "/govern",
            token,
            "POST",
            {"action": "colab_inject_and_run", "params": {"code": "os.system('rm -rf /')"}, "confirm": "x"},
        )
        assert rec["decision"] == "REFUSED"
        # audit shows the sealed chain holds
        code, audit = _req(base + "/audit", token)
        assert audit["chain_ok"] is True and audit["hops"] >= 3
    finally:
        httpd.shutdown()


@pytest.mark.skip(reason="manual: full serve() blocks; covered by build_server tests")
def test_serve_placeholder():
    pass
