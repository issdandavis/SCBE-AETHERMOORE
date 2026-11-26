"""host_capability: the AetherDesk boot check -- certify what THIS box can actually run.

The honest version of "runs on any compute": don't claim universal, PROBE the host and certify
exactly what works here, before the shell offers it. Consolidates the toolchain/model checks that
were scattered across loomfn / polyglot_conformance / rosetta / the AetherDesk provider panel into
one certificate the shell can gate features on.

Probes three things:
  * TOOLCHAINS -- python (always) + node / rustc / cc / go (which language faces can be cross-verified here)
  * RESOURCES  -- cpu count, free disk, total RAM (best-effort; honest None if the OS won't tell us)
  * MODELS     -- local servers reachable (Ollama, LM Studio) + which provider API keys are present
                  (presence only -- never the key value)

Then maps that to RUNNABLE capabilities: which cross-face verification is possible, whether an
LLM climber can run, and which pure-python tools run anywhere. HONEST: a key being present does not
prove the credential works -- only that it is set; a reachable local server is a real check.

    python -m python.helm.host_capability        # print this box's capability certificate
"""

from __future__ import annotations

import json
import os
import shutil
import urllib.request
from typing import Any, Dict, Optional, Sequence

_LOCAL_MODELS = {
    "ollama": "http://127.0.0.1:11434/api/tags",
    "lmstudio": "http://127.0.0.1:1234/v1/models",
}
_ENV_MODELS = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "xai": ["XAI_API_KEY", "GROK_API_KEY"],
    "huggingface": ["HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
}
_TOOLCHAINS = ["node", "rustc", "cc", "go"]


def probe_toolchains() -> Dict[str, bool]:
    """Which language toolchains are on PATH (python is always present -- we are running in it)."""
    out: Dict[str, bool] = {"python": True}
    for t in _TOOLCHAINS:
        out[t] = shutil.which(t) is not None
    return out


def _ram_bytes() -> Optional[int]:
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:  # posix
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except Exception:
        pass
    try:  # windows
        import ctypes

        class _MS(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        ms = _MS()
        ms.dwLength = ctypes.sizeof(_MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):  # type: ignore[attr-defined]
            return int(ms.ullTotalPhys)
    except Exception:
        pass
    return None


def probe_resources() -> Dict[str, Any]:
    ram = _ram_bytes()
    free = shutil.disk_usage(os.getcwd()).free
    return {
        "cpu_count": os.cpu_count() or 1,
        "ram_gb": round(ram / 1e9, 1) if ram else None,  # None = OS would not report it (honest)
        "free_disk_gb": round(free / 1e9, 1),
    }


def _reachable(url: str, timeout: float) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 - fixed localhost probe
            return 200 <= r.status < 500
    except Exception:
        return False


def probe_models(timeout: float = 1.0) -> Dict[str, Dict[str, Any]]:
    """Local model servers reachable + provider API keys present (presence only, never the value)."""
    out: Dict[str, Dict[str, Any]] = {}
    for name, url in _LOCAL_MODELS.items():
        ok = _reachable(url, timeout)
        out[name] = {"kind": "local", "available": ok, "detail": url}
    for name, envs in _ENV_MODELS.items():
        hit = next((e for e in envs if os.environ.get(e)), None)
        out[name] = {"kind": "env", "available": hit is not None, "detail": hit or ("checked: " + ", ".join(envs))}
    return out


def runnable_capabilities(toolchains: Dict[str, bool], models: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Pure mapping: given what's present, what can AetherDesk actually run here?"""
    faces = ["python"]
    for tool, face in (("node", "javascript"), ("rustc", "rust"), ("cc", "c"), ("go", "go")):
        if toolchains.get(tool):
            faces.append(face)
    any_model = any(m.get("available") for m in models.values())
    return {
        "cross_face_verify": faces,  # languages a program can be cross-checked across HERE
        "cross_face_count": len(faces),
        "llm_climber": any_model,  # curriculum/reasoning_ladder --llm runnable here
        "python_tools": ["forge", "curriculum", "reasoning_ladder", "stepwise", "failure_map", "pazaak"],
    }


def certify(probe_network: bool = True, timeout: float = 1.0) -> Dict[str, Any]:
    toolchains = probe_toolchains()
    models = probe_models(timeout) if probe_network else {}
    resources = probe_resources()
    runnable = runnable_capabilities(toolchains, models)
    n_models = sum(1 for m in models.values() if m.get("available"))
    verdict = "AetherDesk core runs (python); cross-face verify across %d language(s); %d model(s) available" % (
        runnable["cross_face_count"],
        n_models,
    )
    return {
        "schema": "aetherdesk_host_capability_v1",
        "toolchains": toolchains,
        "resources": resources,
        "models": models,
        "runnable": runnable,
        "verdict": verdict,
    }


def render(cert: Dict[str, Any]) -> str:
    tc = cert["toolchains"]
    res = cert["resources"]
    have = [t for t, ok in tc.items() if ok]
    models_up = [n for n, m in cert["models"].items() if m.get("available")]
    ram = ("%.1fGB" % res["ram_gb"]) if res["ram_gb"] else "unknown"
    lines = [
        "AETHERDESK HOST CAPABILITY  (what THIS box can run)",
        "  toolchains : " + ", ".join(have),
        "  resources  : %d cpu, %s ram, %.1fGB free disk" % (res["cpu_count"], ram, res["free_disk_gb"]),
        "  models     : " + (", ".join(models_up) if models_up else "none reachable/keyed"),
        "  cross-face : " + " + ".join(cert["runnable"]["cross_face_verify"]),
        "  llm climber: " + ("yes" if cert["runnable"]["llm_climber"] else "no (no model here)"),
        "  --> " + cert["verdict"],
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] = ()) -> int:
    cert = certify()
    if "--json" in argv:
        print(json.dumps(cert, indent=2))
    else:
        print(render(cert))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
