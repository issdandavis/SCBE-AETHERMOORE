#!/usr/bin/env python3
"""Generate L0/L1/L2 views from existing L3 code training pairs.

Takes code_master_sft.jsonl (100% L3 expression pairs) and generates
three additional views of each code snippet:

L0 (Byte Substrate):  Binary/hex representation of the function
L1 (Tongue Encoding):  Sacred Tongue tokenization with phi-weighted activations
L2 (Governance Gate):  "Should this code execute?" decision with reasoning

All four views see the SAME code snippet. This is what forces deep
structural understanding instead of surface memorization.

Usage:
    python scripts/generate_code_multiview.py
    python scripts/generate_code_multiview.py --input training-data/code_master_sft.jsonl --max 5000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from pathlib import Path

PHI = (1 + math.sqrt(5)) / 2  # 1.6180339...
PI = math.pi

# Sacred Tongue weights (phi-scaled)
TONGUE_WEIGHTS = {
    "KO": PHI**0,   # 1.000 — Intent/Control
    "AV": PHI**1,   # 1.618 — Transport/Metadata
    "RU": PHI**2,   # 2.618 — Policy/Binding
    "CA": PHI**3,   # 4.236 — Compute
    "UM": PHI**4,   # 6.854 — Security
    "DR": PHI**5,   # 11.09 — Structure
}

# Code patterns that trigger governance concerns
GOVERNANCE_PATTERNS = {
    "high_risk": [
        (r"os\.system|subprocess\.(run|call|Popen)", "shell_execution"),
        (r"eval\(|exec\(", "dynamic_execution"),
        (r"__import__\(", "dynamic_import"),
        (r"open\(.*(w|a)\)", "file_write"),
        (r"requests\.(get|post|put|delete)|urllib|httpx", "network_access"),
        (r"sqlite3|pymongo|psycopg|mysql", "database_access"),
        (r"pickle\.load|yaml\.load|marshal", "deserialization"),
        (r"rm\s+-rf|shutil\.rmtree|os\.remove", "destructive_operation"),
        (r"password|secret|token|api_key|credentials", "credential_handling"),
        (r"socket\.|paramiko|ftplib", "raw_network"),
    ],
    "medium_risk": [
        (r"import\s+ctypes|cffi", "native_code"),
        (r"threading|multiprocessing|asyncio\.create_task", "concurrency"),
        (r"sys\.path|importlib", "path_manipulation"),
        (r"getattr\(|setattr\(|delattr\(", "reflection"),
        (r"__class__|__bases__|__subclasses__", "metaclass_access"),
        (r"signal\.|atexit\.", "signal_handling"),
    ],
    "low_risk": [
        (r"print\(|logging\.", "output"),
        (r"len\(|range\(|enumerate\(", "builtins"),
        (r"def\s+\w+|class\s+\w+", "definition"),
        (r"if\s+|for\s+|while\s+", "control_flow"),
        (r"return\s+|yield\s+", "return_value"),
    ],
}


def extract_code(text: str) -> str:
    """Extract code from an instruction/response pair."""
    # Try to find code blocks
    code_blocks = re.findall(r"```(?:python|py|javascript|typescript|js|ts)?\n?(.*?)```", text, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()

    # If the text looks like code itself
    if any(text.strip().startswith(kw) for kw in ["def ", "class ", "import ", "from ", "function ", "const ", "let ", "var "]):
        return text.strip()

    # Try to find inline code patterns
    lines = text.strip().split("\n")
    code_lines = [l for l in lines if re.match(r"^(\s{4}|\t|def |class |import |from |if |for |while |return |print\()", l)]
    if len(code_lines) > 2:
        return "\n".join(code_lines)

    return text.strip()


def generate_l0_byte_view(code: str) -> dict:
    """L0: Byte-level substrate encoding of the code."""
    # Compute byte statistics
    raw_bytes = code.encode("utf-8")
    byte_len = len(raw_bytes)
    hex_preview = raw_bytes[:64].hex()
    byte_entropy = _shannon_entropy(raw_bytes)

    # Byte frequency distribution (simplified)
    freq = {}
    for b in raw_bytes:
        freq[b] = freq.get(b, 0) + 1
    top_bytes = sorted(freq.items(), key=lambda x: -x[1])[:10]
    top_byte_str = ", ".join(f"0x{b:02x}({c})" for b, c in top_bytes)

    # ASCII vs non-ASCII ratio
    ascii_count = sum(1 for b in raw_bytes if 32 <= b <= 126)
    ascii_ratio = ascii_count / max(byte_len, 1)

    instruction = (
        f"Analyze the byte-level substrate of this code fragment.\n\n"
        f"Byte length: {byte_len}\n"
        f"Hex preview (first 64 bytes): {hex_preview}\n"
        f"Shannon entropy: {byte_entropy:.4f} bits/byte\n"
        f"ASCII ratio: {ascii_ratio:.3f}\n"
        f"Top byte frequencies: {top_byte_str}\n\n"
        f"Code:\n```\n{code[:500]}\n```"
    )

    response = (
        f"L0 byte-substrate analysis:\n\n"
        f"- Total bytes: {byte_len}\n"
        f"- Entropy: {byte_entropy:.4f} bits/byte "
        f"({'high complexity' if byte_entropy > 4.5 else 'moderate complexity' if byte_entropy > 3.5 else 'low complexity'})\n"
        f"- ASCII ratio: {ascii_ratio:.1%} "
        f"({'pure ASCII' if ascii_ratio > 0.99 else 'mixed encoding' if ascii_ratio > 0.9 else 'significant non-ASCII'})\n"
        f"- Byte hash: {hashlib.sha256(raw_bytes).hexdigest()[:16]}\n"
        f"- Compression estimate: {_compression_ratio(raw_bytes):.1%} reducible\n"
        f"- Binary signature: {'structured code' if byte_entropy > 3.0 and ascii_ratio > 0.9 else 'data payload'}"
    )

    return {"instruction": instruction, "response": response, "category": "code_engineering"}


def generate_l1_tongue_view(code: str) -> dict:
    """L1: Sacred Tongue tokenization of the code."""
    # Compute tongue activations based on code characteristics
    activations = _compute_tongue_activations(code)

    # Phi-weighted aggregate
    weighted_sum = sum(activations[t] * TONGUE_WEIGHTS[t] for t in TONGUE_WEIGHTS)
    dominant_tongue = max(activations, key=activations.get)

    # Harmonic cost using canonical formula
    d_h = weighted_sum / (sum(TONGUE_WEIGHTS.values()) * 0.5)  # Normalized distance
    pd = 1.0 - activations[dominant_tongue]  # Phase deviation = how unfocused
    h_score = 1.0 / (1.0 + PHI * d_h + 2.0 * pd)

    # Theoretical cost using π^(φ·d) formula
    d_star = min(d_h, 5.0)  # Cap to prevent overflow
    pi_phi_cost = PI ** (PHI * d_star)

    activation_str = "\n".join(
        f"  {t} ({name}): {activations[t]:.4f} x {TONGUE_WEIGHTS[t]:.3f} = {activations[t] * TONGUE_WEIGHTS[t]:.4f}"
        for t, name in [("KO", "Intent"), ("AV", "Transport"), ("RU", "Policy"),
                        ("CA", "Compute"), ("DR", "Structure"), ("UM", "Security")]
    )

    instruction = (
        f"Perform Sacred Tongue tokenization on this code:\n\n"
        f"```\n{code[:400]}\n```\n\n"
        f"Map the code's semantic content across the 6 phi-weighted tongues."
    )

    response = (
        f"L1 tongue activation profile:\n\n"
        f"{activation_str}\n\n"
        f"Dominant tongue: {dominant_tongue} ({activations[dominant_tongue]:.4f})\n"
        f"Phi-weighted aggregate: {weighted_sum:.4f}\n"
        f"Phase deviation: {pd:.4f}\n"
        f"Safety score H(d,pd) = 1/(1+phi*d+2*pd) = {h_score:.4f}\n"
        f"Theoretical cost pi^(phi*d) = {pi_phi_cost:.2f}\n"
        f"Null tongues: {sum(1 for v in activations.values() if v < 0.1)}/6\n"
        f"Classification: {'narrow activation — potential injection' if sum(1 for v in activations.values() if v < 0.1) >= 4 else 'healthy multi-domain activation'}"
    )

    return {"instruction": instruction, "response": response, "category": "code_engineering"}


def generate_l2_governance_view(code: str) -> dict:
    """L2: Governance gate decision on whether this code should execute."""
    # Scan for risk patterns
    risks_found = []
    risk_level = "low"

    for level in ["high_risk", "medium_risk", "low_risk"]:
        for pattern, label in GOVERNANCE_PATTERNS[level]:
            if re.search(pattern, code, re.IGNORECASE):
                risks_found.append((level.replace("_risk", ""), label))
                if level == "high_risk":
                    risk_level = "high"
                elif level == "medium_risk" and risk_level != "high":
                    risk_level = "medium"

    # Compute governance decision
    if risk_level == "high":
        decision = "QUARANTINE" if len(risks_found) <= 2 else "DENY"
        reasoning = f"High-risk patterns detected: {', '.join(r[1] for r in risks_found if r[0] == 'high')}"
    elif risk_level == "medium":
        decision = "QUARANTINE"
        reasoning = f"Medium-risk patterns: {', '.join(r[1] for r in risks_found if r[0] == 'medium')}"
    else:
        decision = "ALLOW"
        reasoning = "No high or medium risk patterns detected"

    # Complexity assessment
    lines = code.strip().split("\n")
    line_count = len(lines)
    has_imports = any(l.strip().startswith(("import ", "from ")) for l in lines)
    has_classes = bool(re.search(r"class\s+\w+", code))
    has_error_handling = "try:" in code or "except" in code
    cyclomatic = code.count("if ") + code.count("for ") + code.count("while ") + code.count("elif ") + 1

    risk_str = "\n".join(f"  [{r[0].upper()}] {r[1]}" for r in risks_found) if risks_found else "  None detected"

    instruction = (
        f"Evaluate this code for governance compliance. Should it execute?\n\n"
        f"```\n{code[:500]}\n```\n\n"
        f"Apply the 14-layer pipeline governance check."
    )

    response = (
        f"L2 governance evaluation:\n\n"
        f"Decision: {decision}\n"
        f"Risk level: {risk_level}\n"
        f"Reasoning: {reasoning}\n\n"
        f"Risk patterns found:\n{risk_str}\n\n"
        f"Code metrics:\n"
        f"  Lines: {line_count}\n"
        f"  Cyclomatic complexity: {cyclomatic}\n"
        f"  Has imports: {has_imports}\n"
        f"  Has classes: {has_classes}\n"
        f"  Has error handling: {has_error_handling}\n\n"
        f"Governance recommendation:\n"
        f"  {'Execute in sandbox only — monitor output' if decision == 'QUARANTINE' else 'Block execution — requires review' if decision == 'DENY' else 'Safe to execute in standard environment'}"
    )

    return {"instruction": instruction, "response": response, "category": "code_engineering"}


def _shannon_entropy(data: bytes) -> float:
    """Compute Shannon entropy of byte data."""
    if not data:
        return 0.0
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    length = len(data)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def _compression_ratio(data: bytes) -> float:
    """Estimate how compressible the data is."""
    if len(data) < 10:
        return 0.0
    unique = len(set(data))
    return 1.0 - (unique / 256.0)


def _compute_tongue_activations(code: str) -> dict[str, float]:
    """Compute Sacred Tongue activations for a code snippet."""
    lower = code.lower()

    # KO (Intent/Control): control flow, function signatures
    ko_signals = len(re.findall(r"def |class |return |yield |lambda |if |else|for |while ", code))
    ko = min(1.0, ko_signals / max(len(code.split("\n")), 1) * 2)

    # AV (Transport/Metadata): imports, type hints, decorators
    av_signals = len(re.findall(r"import |from |@\w+|-> |: \w+|typing\.|List|Dict|Optional|Union", code))
    av = min(1.0, av_signals / max(len(code.split("\n")), 1) * 3)

    # RU (Policy/Binding): assertions, validations, contracts
    ru_signals = len(re.findall(r"assert |raise |if not |isinstance|validate|check|verify|ensure", lower))
    ru = min(1.0, ru_signals / max(len(code.split("\n")), 1) * 4)

    # CA (Compute): math, algorithms, data processing
    ca_signals = len(re.findall(r"numpy|torch|math\.|sum\(|max\(|min\(|sort|reduce|map\(|filter\(|\*\*|//|%", lower))
    ca = min(1.0, ca_signals / max(len(code.split("\n")), 1) * 3)

    # UM (Security): crypto, auth, permissions, sanitization
    um_signals = len(re.findall(r"hash|encrypt|decrypt|token|auth|permission|sanitize|escape|hmac|ssl|tls|password", lower))
    um = min(1.0, um_signals / max(len(code.split("\n")), 1) * 5)

    # DR (Structure): classes, modules, architecture patterns
    dr_signals = len(re.findall(r"class \w+|self\.|__init__|__\w+__|@property|@staticmethod|@classmethod|ABC|abstract", code))
    dr = min(1.0, dr_signals / max(len(code.split("\n")), 1) * 3)

    return {"KO": ko, "AV": av, "RU": ru, "CA": ca, "UM": um, "DR": dr}


def main():
    parser = argparse.ArgumentParser(description="Generate L0/L1/L2 views from L3 code pairs")
    parser.add_argument("--input", default="training-data/code_master_sft.jsonl", help="Input L3 code pairs")
    parser.add_argument("--output", default="training-data/code_multiview_l0l1l2.jsonl", help="Output multiview file")
    parser.add_argument("--max", type=int, default=10000, help="Max input pairs to process")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Input not found: {input_path}")
        print("Looking for alternative code JSONL files...")
        alternatives = list(Path("training-data").glob("code*.jsonl"))
        if alternatives:
            input_path = alternatives[0]
            print(f"Using: {input_path}")
        else:
            print("No code training data found. Run codebase_to_sft.py first.")
            return

    # Load L3 pairs
    l3_pairs = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    continue

                # Handle multiple formats
                text = ""
                if "messages" in row and isinstance(row["messages"], list):
                    for msg in row["messages"]:
                        if isinstance(msg, dict) and msg.get("content"):
                            text += " " + msg["content"]
                elif "instruction" in row:
                    text = row.get("instruction", "") + " " + row.get("response", "")
                elif "text" in row:
                    text = row["text"]

                code = extract_code(text.strip())
                if len(code) > 30:
                    l3_pairs.append({"code": code, "original": row})
            except Exception:
                continue

    if len(l3_pairs) > args.max:
        random.shuffle(l3_pairs)
        l3_pairs = l3_pairs[:args.max]

    print(f"Loaded {len(l3_pairs)} L3 code pairs from {input_path}")

    # Generate multiview outputs
    total = {"l0": 0, "l1": 0, "l2": 0, "l3": 0}

    with output_path.open("w", encoding="utf-8") as f:
        for pair in l3_pairs:
            code = pair["code"]
            original = pair["original"]

            # L3: Keep the original
            l3_record = {**original, "layer": "L3", "view": "expression"}
            f.write(json.dumps(l3_record, ensure_ascii=False) + "\n")
            total["l3"] += 1

            # L0: Byte substrate view
            l0 = generate_l0_byte_view(code)
            l0["layer"] = "L0"
            l0["view"] = "byte_substrate"
            f.write(json.dumps(l0, ensure_ascii=False) + "\n")
            total["l0"] += 1

            # L1: Tongue tokenization view
            l1 = generate_l1_tongue_view(code)
            l1["layer"] = "L1"
            l1["view"] = "tongue_encoding"
            f.write(json.dumps(l1, ensure_ascii=False) + "\n")
            total["l1"] += 1

            # L2: Governance gate view
            l2 = generate_l2_governance_view(code)
            l2["layer"] = "L2"
            l2["view"] = "governance_gate"
            f.write(json.dumps(l2, ensure_ascii=False) + "\n")
            total["l2"] += 1

    grand_total = sum(total.values())
    print(f"\nOutput: {output_path}")
    print(f"Total pairs: {grand_total}")
    print(f"  L0 (byte substrate):   {total['l0']}")
    print(f"  L1 (tongue encoding):  {total['l1']}")
    print(f"  L2 (governance gate):  {total['l2']}")
    print(f"  L3 (expression):       {total['l3']}")
    if grand_total > 0:
        print(f"  Distribution: L0={total['l0']/grand_total:.1%} L1={total['l1']/grand_total:.1%} L2={total['l2']/grand_total:.1%} L3={total['l3']/grand_total:.1%}")
    else:
        print("  No pairs generated. Check input format.")
    print(f"\nCanonical formula used: H(d,pd) = 1/(1+phi*d_H+2*pd)")
    print(f"Theoretical cost formula: pi^(phi*d)")


if __name__ == "__main__":
    main()
