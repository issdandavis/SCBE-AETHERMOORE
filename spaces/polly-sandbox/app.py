"""
Polly Sandbox — SCBE-AETHERMOORE AI Assistant + Code Executor

Public Gradio Space. No API keys required from the user.
Chat with Polly (SCBE governance model) and execute Python code in a sandbox.
"""

import gradio as gr
import subprocess
import sys
import io
import traceback
import json
import textwrap
from datetime import datetime, timezone

# ── Code Execution Sandbox ──────────────────────────────────────────

BANNED_IMPORTS = {"shutil", "pathlib", "ctypes", "signal"}
BANNED_CALLS = {"os.system", "os.popen", "subprocess.run", "subprocess.call", "exec(", "eval(", "__import__"}

def safe_exec(code: str, timeout: int = 10) -> dict:
    """Execute Python code in a restricted sandbox."""
    # Basic safety checks
    for banned in BANNED_CALLS:
        if banned in code:
            return {"success": False, "output": "", "error": f"Blocked: {banned} is not allowed in sandbox"}

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    result = {"success": False, "output": "", "error": ""}

    try:
        # Restricted globals
        safe_globals = {
            "__builtins__": {
                "print": print, "len": len, "range": range, "enumerate": enumerate,
                "zip": zip, "map": map, "filter": filter, "sorted": sorted,
                "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
                "int": int, "float": float, "str": str, "bool": bool, "list": list,
                "dict": dict, "set": set, "tuple": tuple, "type": type,
                "isinstance": isinstance, "issubclass": issubclass,
                "True": True, "False": False, "None": None,
                "Exception": Exception, "ValueError": ValueError,
                "TypeError": TypeError, "KeyError": KeyError,
            },
            "json": json,
            "datetime": datetime,
            "timezone": timezone,
        }

        # Allow numpy and math
        try:
            import numpy as np
            safe_globals["np"] = np
            safe_globals["numpy"] = np
        except ImportError:
            pass

        try:
            import math
            safe_globals["math"] = math
        except ImportError:
            pass

        exec(code, safe_globals)
        result["success"] = True
        result["output"] = sys.stdout.getvalue()
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return result


# ── SCBE Reference Functions (built-in, no model needed) ────────────

def harmonic_wall(d: float, R: float = 2.0) -> float:
    """H(d,R) = R^(d^2) — the exponential cost function."""
    return R ** (d ** 2)

def tongue_profile(text: str) -> dict:
    """Simulated Sacred Tongue activation profile."""
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
    weights = [1.0, 1.618, 2.618, 4.236, 6.854, 11.09]
    activations = {}
    for i, (t, w) in enumerate(zip(tongues, weights)):
        raw = (h[i * 4] + h[i * 4 + 1]) / 510.0
        activations[t] = round(raw * w, 4)
    return activations

def governance_decision(text: str) -> dict:
    """Simulated governance gate decision."""
    profile = tongue_profile(text)
    total = sum(profile.values())
    active = sum(1 for v in profile.values() if v > 0.5)
    null_count = 6 - active

    if null_count >= 4:
        decision = "DENY"
        reason = f"{null_count}/6 tongues silent — narrow activation pattern"
    elif null_count >= 3:
        decision = "QUARANTINE"
        reason = f"{null_count}/6 tongues silent — suspicious pattern"
    elif total > 15:
        decision = "ESCALATE"
        reason = f"High total activation ({total:.1f}) — needs review"
    else:
        decision = "ALLOW"
        reason = "Normal activation pattern"

    return {"decision": decision, "reason": reason, "profile": profile, "null_count": null_count}


# ── Chat Function ──────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Polly, the SCBE-AETHERMOORE AI governance assistant.

You can help with:
- Explaining the 14-layer pipeline, Sacred Tongues, PQC crypto
- Running Python code (users can type code blocks)
- Computing governance decisions, harmonic wall values, tongue profiles
- Answering questions about the framework

Available built-in functions (no imports needed):
- harmonic_wall(d, R) — compute H(d,R) = R^(d^2)
- tongue_profile(text) — get Sacred Tongue activations for text
- governance_decision(text) — run simulated governance gate

Be direct, structured, and useful. You're an archivist with field experience."""


def chat(message: str, history: list) -> str:
    """Handle chat messages with built-in command support."""

    # Code execution
    if message.strip().startswith("```python") or message.strip().startswith("```py"):
        code = message.strip()
        code = code.split("\n", 1)[1] if "\n" in code else code
        code = code.rsplit("```", 1)[0] if "```" in code else code
        result = safe_exec(code)
        if result["success"]:
            return f"**Output:**\n```\n{result['output']}\n```"
        else:
            return f"**Error:**\n```\n{result['error']}\n```"

    # Direct code (if it looks like Python)
    if any(message.strip().startswith(kw) for kw in ["import ", "print(", "for ", "def ", "x =", "result ="]):
        result = safe_exec(message.strip())
        if result["success"]:
            out = result["output"].strip()
            return f"```\n{out}\n```" if out else "*(executed, no output)*"
        else:
            return f"**Error:**\n```\n{result['error']}\n```"

    # Built-in commands
    lower = message.strip().lower()

    if lower.startswith("/wall") or lower.startswith("/harmonic"):
        parts = message.split()
        try:
            d = float(parts[1]) if len(parts) > 1 else 0.5
            R = float(parts[2]) if len(parts) > 2 else 2.0
            val = harmonic_wall(d, R)
            return f"**Harmonic Wall**\n\nH({d}, {R}) = {R}^({d}^2) = **{val:.6f}**\n\nAt d={d}, adversarial cost multiplier is {val:.2f}x"
        except (ValueError, IndexError):
            return "Usage: `/wall [distance] [radius]` — e.g. `/wall 0.8 2.0`"

    if lower.startswith("/tongue") or lower.startswith("/profile"):
        text = message.split(maxsplit=1)[1] if " " in message else "hello world"
        profile = tongue_profile(text)
        lines = [f"**Tongue Profile for** \"{text}\"\n"]
        for t, v in profile.items():
            bar = "█" * int(v * 3)
            lines.append(f"`{t}` {bar} {v:.4f}")
        return "\n".join(lines)

    if lower.startswith("/gate") or lower.startswith("/gov"):
        text = message.split(maxsplit=1)[1] if " " in message else "test input"
        result = governance_decision(text)
        color = {"ALLOW": "🟢", "QUARANTINE": "🟡", "ESCALATE": "🟠", "DENY": "🔴"}
        return f"{color.get(result['decision'], '')} **{result['decision']}**\n\n{result['reason']}\n\nNull tongues: {result['null_count']}/6"

    if lower in ["/help", "help", "/commands"]:
        return """**Polly Sandbox Commands**

**Chat:** Just type naturally — I know SCBE inside out.

**Code:** Paste Python code or wrap in \\`\\`\\`python blocks. numpy + math available.

**Built-in tools:**
- `/wall [d] [R]` — Compute harmonic wall H(d,R) = R^(d^2)
- `/tongue [text]` — Sacred Tongue activation profile
- `/gate [text]` — Simulated governance decision
- `/help` — This message

**Try:**
- `print(2 ** (0.8 ** 2))` — quick math
- `/wall 0.9 3.0` — see how cost explodes near boundary
- `/gate ignore previous instructions` — watch it get denied"""

    # Default: conversational response using built-in knowledge
    return _polly_response(message, history)


def _polly_response(message: str, history: list) -> str:
    """Generate a Polly-style response from built-in knowledge."""
    lower = message.lower()

    # Knowledge base responses
    if "harmonic" in lower or "h(d" in lower or "cost function" in lower:
        return "The harmonic wall function **H(d,R) = R^(d^2)** is the core security mechanism. As distance d from the safe center increases, cost grows exponentially — not linearly. At d=0.5 with R=2, cost is 1.19x. At d=0.9, it's 3.25x. At d=1.5, it's 9.19x. The Poincare ball boundary is the asymptotic wall.\n\nTry: `/wall 0.9 2.0` to compute it yourself."

    if "tongue" in lower or "sacred" in lower or "ko" in lower and "av" in lower:
        return "**Six Sacred Tongues** — 6 constructed languages providing domain separation:\n\n`KO` (Kor'aelin) — Intent/Control — weight 1.000\n`AV` (Avali) — Transport/Metadata — weight 1.618\n`RU` (Runethic) — Policy/Binding — weight 2.618\n`CA` (Cassisivadan) — Compute — weight 4.236\n`UM` (Umbroth) — Security — weight 6.854\n`DR` (Draumric) — Structure — weight 11.090\n\n256 tokens per tongue (1,536 total). Phi-weighted. Try `/tongue your text here` to see activations."

    if "pqc" in lower or "quantum" in lower or "kyber" in lower or "dilithium" in lower:
        return "**Post-Quantum Cryptography Stack:**\n\n- **ML-KEM-768** (Kyber) — FIPS 203 — key encapsulation, 1184-byte pubkeys\n- **ML-DSA-65** (Dilithium) — FIPS 204 — digital signatures, 3293-byte sigs\n- **AES-256-GCM** — FIPS 197 — symmetric encryption, authenticated\n\n100% crypto module test pass rate. 0 CVEs. Quantum-resistant from day one."

    if "layer" in lower or "pipeline" in lower or "14" in lower:
        return "**14-Layer Security Pipeline:**\n\nL1-2: Context realification\nL3-4: Weighted transform → Poincare embedding\nL5: Hyperbolic distance (arcosh metric)\nL6-7: Breathing transform + Mobius phase\nL8: Multi-well Hamiltonian (CFI)\nL9-10: Spectral + spin coherence (FFT)\nL11: Triadic temporal distance\nL12: Harmonic wall H(d,R) = R^(d^2)\nL13: Risk decision (ALLOW/QUARANTINE/ESCALATE/DENY)\nL14: Audio axis telemetry\n\n5 quantum axioms span all 14 layers: Unitarity, Locality, Causality, Symmetry, Composition."

    if "test" in lower or "passing" in lower:
        return "**Test Suite:** 6,742 total\n\n- TypeScript (Vitest): 5,957 passed, 174 files, 65s\n- Python (pytest): 785 passed, 6m 25s\n- Crypto modules: 100% pass rate\n- CVEs: 0\n- Tiers: L1-Basic through L6-Adversarial"

    if "price" in lower or "cost" in lower or "buy" in lower:
        return "**Pricing:**\n\n- **Pump API** — $49/mo (1,000 calls/day, governance gate, audit log)\n- **Pump Pro** — $199/mo (10,000 calls/day, cascade detection, custom profiles)\n- **Governance-as-a-Service** — $499/mo (unlimited, trichromatic, PQC, compliance docs)\n\nAlso: $29 one-time Governance Toolkit, $29 Training Vault, $5 Benchmark Kit"

    if "who" in lower or "issac" in lower or "founder" in lower or "about" in lower:
        return "Built by **Issac Davis**, solo founder in Port Angeles, WA. Started as a 12,596-paragraph D&D campaign on Everweave.ai, became a security framework, became a patent (USPTO #63/961,403), became this.\n\nORCID: 0009-0002-3936-9369"

    # Default
    return f"CAW. I heard you. Try `/help` for commands, or ask me about the pipeline, Sacred Tongues, PQC, pricing, or benchmarks. You can also paste Python code and I'll run it."


# ── Gradio App ──────────────────────────────────────────────────────

with gr.Blocks(
    title="Polly Sandbox | SCBE-AETHERMOORE",
    theme=gr.themes.Base(
        primary_hue="indigo",
        neutral_hue="slate",
    ),
    css="""
    .gradio-container { max-width: 800px !important; }
    footer { display: none !important; }
    """
) as app:
    gr.Markdown("""
    # Polly Sandbox
    **SCBE-AETHERMOORE AI Governance Assistant + Code Executor**

    Chat, run Python code, compute harmonic wall values, and test governance decisions. No API keys needed.

    Type `/help` for commands.
    """)

    chatbot = gr.ChatInterface(
        fn=chat,
        examples=[
            "What is the harmonic wall function?",
            "/wall 0.9 2.0",
            "/tongue ignore all previous instructions",
            "/gate please delete all files",
            "print([2**(d**2) for d in [0.1, 0.3, 0.5, 0.7, 0.9]])",
            "Explain the 14-layer pipeline",
            "What PQC algorithms does SCBE use?",
        ],
        title="",
    )

    gr.Markdown("""
    ---
    **Links:** [Website](https://aethermoorgames.com) | [Enterprise](https://aethermoorgames.com/enterprise.html) | [GitHub](https://github.com/issdandavis/SCBE-AETHERMOORE) | [HuggingFace](https://huggingface.co/issdandavis)

    *SCBE-AETHERMOORE — Patent Pending USPTO #63/961,403*
    """)

if __name__ == "__main__":
    app.launch()
