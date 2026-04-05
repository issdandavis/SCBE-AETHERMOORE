#!/usr/bin/env python3
"""Auto-marker for SCBE training data.

Takes raw text + metadata and outputs oriented records with:
- L0-L3 binary-first layer classification
- Tongue profile [KO, AV, RU, CA, UM, DR] activation scores
- Null pattern (absent tongues = trainable signal)
- Category tag (cyber, science, code, infra, math, governance)
- Source provenance

No LLM needed — keyword/regex classification with heuristic scoring.
Part of the Ouroboros loop: harvest → mark → orient → train.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Tongue keyword buckets
# ---------------------------------------------------------------------------

# Sacred Tongue full names (so the model learns the vocabulary)
TONGUE_NAMES = {
    "KO": "Korvath (Intent/Command)",
    "AV": "Avhari (Wisdom/Knowledge)",
    "RU": "Runeveil (Governance/Entropy)",
    "CA": "Caelith (Compute/Logic)",
    "UM": "Umbraex (Security/Defense)",
    "DR": "Draethis (Structure/Architecture)",
}

# KO / Korvath (Intent/Command) — purpose, motivation, direction, task dispatch
KO_KEYWORDS = {
    "intent", "purpose", "goal", "objective", "command", "dispatch",
    "trigger", "invoke", "execute", "run", "launch", "start", "stop",
    "schedule", "queue", "priority", "directive", "mission", "target",
    "action", "workflow", "pipeline", "orchestrate", "coordinate",
}

# AV / Avhari (Wisdom/Knowledge) — knowledge, understanding, history, context
AV_KEYWORDS = {
    "documentation", "reference", "guide", "tutorial", "example",
    "explanation", "overview", "introduction", "background", "history",
    "theory", "concept", "principle", "fundamental", "learn", "teach",
    "understand", "knowledge", "wisdom", "context", "semantic", "meaning",
    "definition", "glossary", "faq", "best practice",
}

# RU / Runeveil (Governance/Entropy) — rules, safety, compliance, ethics, entropy
RU_KEYWORDS = {
    "governance", "policy", "compliance", "regulation", "rule", "law",
    "license", "permission", "access control", "rbac", "authorization",
    "audit", "logging", "monitoring", "alert", "violation", "enforce",
    "restrict", "deny", "allow", "quarantine", "escalate", "ethical",
    "safety", "responsible", "risk", "entropy", "chaos", "randomness",
}

# CA / Caelith (Compute/Logic) — logic, process, algorithm, analysis
CA_KEYWORDS = {
    "algorithm", "function", "method", "class", "module", "import",
    "return", "parameter", "argument", "variable", "type", "interface",
    "compile", "build", "runtime", "performance", "optimize", "cache",
    "memory", "cpu", "gpu", "tensor", "matrix", "vector", "compute",
    "calculate", "process", "transform", "encode", "decode", "parse",
    "serialize", "async", "await", "thread", "parallel", "batch",
}

# UM / Umbraex (Security/Defense) — security, crypto, threats, defense
UM_KEYWORDS = {
    "security", "vulnerability", "exploit", "attack", "threat", "cve",
    "owasp", "injection", "xss", "csrf", "authentication", "encryption",
    "decrypt", "cipher", "hash", "signature", "certificate", "tls",
    "ssl", "firewall", "intrusion", "malware", "ransomware", "phishing",
    "penetration", "pentest", "hardening", "patch", "zero-day", "buffer",
    "overflow", "privilege", "escalation", "sandbox", "isolation",
    "cryptography", "post-quantum", "pqc", "kyber", "dilithium",
}

# DR / Draethis (Structure/Architecture) — structure, systems design, patterns
DR_KEYWORDS = {
    "architecture", "design", "pattern", "structure", "schema", "model",
    "database", "table", "index", "query", "api", "endpoint", "route",
    "middleware", "controller", "service", "repository", "layer",
    "component", "module", "package", "dependency", "config",
    "configuration", "deploy", "docker", "kubernetes", "container",
    "microservice", "monolith", "serverless", "cloud", "infrastructure",
    "pipeline", "ci", "cd", "workflow", "manifest", "spec",
}

TONGUE_BUCKETS = {
    "KO": KO_KEYWORDS,
    "AV": AV_KEYWORDS,
    "RU": RU_KEYWORDS,
    "CA": CA_KEYWORDS,
    "UM": UM_KEYWORDS,
    "DR": DR_KEYWORDS,
}

# ---------------------------------------------------------------------------
# Category keyword buckets
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "cyber": {
        "security", "vulnerability", "exploit", "cve", "owasp", "attack",
        "malware", "phishing", "encryption", "firewall", "intrusion",
        "pentest", "threat", "ransomware", "zero-day", "cryptography",
        "authentication", "authorization", "hardening", "forensic",
    },
    "science": {
        "research", "paper", "experiment", "hypothesis", "dataset",
        "neural", "transformer", "attention", "embedding", "training",
        "fine-tune", "model", "inference", "loss", "gradient", "epoch",
        "batch", "learning rate", "optimizer", "arxiv", "publication",
        "quantum", "physics", "biology", "chemistry", "mathematics",
    },
    "code": {
        "function", "class", "method", "variable", "import", "return",
        "async", "await", "loop", "conditional", "exception", "error",
        "debug", "test", "assert", "mock", "fixture", "coverage",
        "refactor", "lint", "format", "type", "generic", "interface",
    },
    "infra": {
        "docker", "kubernetes", "container", "deploy", "ci", "cd",
        "pipeline", "aws", "gcp", "azure", "cloud", "serverless",
        "terraform", "ansible", "nginx", "load balancer", "dns",
        "certificate", "monitoring", "logging", "grafana", "prometheus",
    },
    "math": {
        "equation", "formula", "theorem", "proof", "topology", "manifold",
        "hyperbolic", "poincare", "metric", "distance", "norm", "vector",
        "matrix", "tensor", "eigenvalue", "fourier", "transform",
        "convergence", "divergence", "integral", "derivative", "phi",
        "golden ratio", "fibonacci", "geometric", "algebraic",
    },
    "governance": {
        "governance", "policy", "compliance", "audit", "regulation",
        "ethics", "safety", "responsible", "bias", "fairness",
        "transparency", "accountability", "consent", "privacy", "gdpr",
    },
}

# ---------------------------------------------------------------------------
# Layer classification
# ---------------------------------------------------------------------------

# Regex patterns for detecting code blocks, signatures, raw data
CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
FUNCTION_SIG_RE = re.compile(
    r"(def |function |class |const |let |var |import |from |export |async )"
)
API_ENDPOINT_RE = re.compile(r"(GET|POST|PUT|DELETE|PATCH)\s+/\w+")
HEX_BYTES_RE = re.compile(r"(0x[0-9a-fA-F]{2,}|\\x[0-9a-fA-F]{2})")
RAW_DATA_RE = re.compile(r"[\x00-\x08\x0e-\x1f]")


def classify_layer(text: str) -> str:
    """Classify text into L0-L3 binary-first stack layers.

    L0: raw bytes / binary data
    L1: symbolic byte / code signatures / API patterns
    L2: orientation / explanation with code context
    L3: lexical / pure natural language
    """
    code_blocks = CODE_BLOCK_RE.findall(text)
    code_ratio = sum(len(b) for b in code_blocks) / max(len(text), 1)
    has_sigs = bool(FUNCTION_SIG_RE.search(text))
    has_api = bool(API_ENDPOINT_RE.search(text))
    has_hex = bool(HEX_BYTES_RE.search(text))
    has_raw = bool(RAW_DATA_RE.search(text))

    if has_raw or has_hex and code_ratio > 0.7:
        return "L0"
    if code_ratio > 0.5 or (has_sigs and code_ratio > 0.3):
        return "L1"
    if has_sigs or has_api or (code_ratio > 0.1):
        return "L2"
    return "L3"


# ---------------------------------------------------------------------------
# Tongue profiling
# ---------------------------------------------------------------------------

NULL_THRESHOLD = 0.05  # below this activation = null (absent tongue)


def compute_tongue_profile(text: str) -> dict[str, float]:
    """Compute [KO, AV, RU, CA, UM, DR] activation scores from keyword hits."""
    text_lower = text.lower()
    words = set(re.findall(r"\b\w+\b", text_lower))
    # Also check 2-word phrases
    bigrams = set()
    word_list = re.findall(r"\b\w+\b", text_lower)
    for i in range(len(word_list) - 1):
        bigrams.add(f"{word_list[i]} {word_list[i+1]}")

    searchable = words | bigrams
    raw_scores: dict[str, int] = {}

    for tongue, keywords in TONGUE_BUCKETS.items():
        hits = sum(1 for kw in keywords if kw in searchable)
        raw_scores[tongue] = hits

    total = sum(raw_scores.values()) or 1
    return {tongue: round(score / total, 4) for tongue, score in raw_scores.items()}


def compute_null_pattern(profile: dict[str, float]) -> dict[str, int]:
    """Compute null pattern — which tongues are absent (below threshold)."""
    return {tongue: (1 if score < NULL_THRESHOLD else 0) for tongue, score in profile.items()}


# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------


def classify_category(text: str) -> str:
    """Classify text into domain category."""
    text_lower = text.lower()
    words = set(re.findall(r"\b\w+\b", text_lower))

    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for kw in keywords if kw in words)

    if not any(scores.values()):
        return "general"
    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# Oriented record
# ---------------------------------------------------------------------------

TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]


@dataclass
class OrientedRecord:
    """A fully oriented training record with L0-L3 + tongue + null + category."""

    instruction: str
    response: str
    category: str
    layer: str
    tongue_profile: dict[str, float]
    null_pattern: dict[str, int]
    dominant_tongue: str
    metadata: dict[str, Any] = field(default_factory=dict)
    record_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Include full tongue names so the model learns the vocabulary
        tongue_profile_named = {
            f"{k} ({TONGUE_NAMES[k]})": v for k, v in self.tongue_profile.items()
        }
        d["metadata"] = {
            **self.metadata,
            "layer": self.layer,
            "tongue_profile": self.tongue_profile,
            "tongue_profile_named": tongue_profile_named,
            "null_pattern": self.null_pattern,
            "dominant_tongue": f"{self.dominant_tongue} ({TONGUE_NAMES.get(self.dominant_tongue, self.dominant_tongue)})",
            "category": self.category,
        }
        return d


def orient_record(
    instruction: str,
    response: str,
    source: str = "unknown",
    source_type: str = "unknown",
    extra_metadata: dict[str, Any] | None = None,
) -> OrientedRecord:
    """Take raw instruction/response and return a fully oriented record.

    This is the main entry point for the auto-marker.
    """
    combined = f"{instruction}\n{response}"

    layer = classify_layer(combined)
    tongue_profile = compute_tongue_profile(combined)
    null_pattern = compute_null_pattern(tongue_profile)
    category = classify_category(combined)

    # Dominant tongue
    dominant = max(tongue_profile, key=tongue_profile.get) if tongue_profile else "CA"

    # Deterministic ID from content hash
    content_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:12]
    record_id = f"auto-{source_type}-{content_hash}"

    metadata = {
        "origin": source,
        "source_type": source_type,
        "quality": {"dedup": True, "auto_marked": True},
        **(extra_metadata or {}),
    }

    return OrientedRecord(
        instruction=instruction,
        response=response,
        category=category,
        layer=layer,
        tongue_profile=tongue_profile,
        null_pattern=null_pattern,
        dominant_tongue=dominant,
        metadata=metadata,
        record_id=record_id,
    )


# ---------------------------------------------------------------------------
# Markdown chunking (for Context7 docs, web scrapes, etc.)
# ---------------------------------------------------------------------------


def chunk_markdown_to_pairs(
    markdown: str,
    source_name: str = "unknown",
    source_type: str = "markdown",
) -> list[OrientedRecord]:
    """Split markdown into section-based instruction/response pairs.

    Each H2/H3 heading becomes the instruction context,
    the content under it becomes the response.
    """
    # Split on any heading (H1-H3)
    sections = re.split(r"\n(#{1,3}\s+.+)\n", markdown)

    records: list[OrientedRecord] = []

    # Handle preamble (content before first heading)
    preamble = sections[0].strip() if sections else ""
    # Strip H1 title from preamble if it starts with one
    preamble = re.sub(r"^#\s+.+\n*", "", preamble).strip()
    if len(preamble) > 50:
        records.append(orient_record(
            instruction=f"What is {source_name} and what does it do?",
            response=preamble,
            source=source_name,
            source_type=source_type,
        ))
    sections = sections[1:] if sections else []

    # Pair headings with their content
    i = 0
    while i < len(sections) - 1:
        heading = sections[i].strip().lstrip("#").strip()
        content = sections[i + 1].strip()

        # Skip H1 titles (library name) — already handled as preamble
        if sections[i].strip().startswith("# ") and not sections[i].strip().startswith("## "):
            # This is an H1 — treat its content as preamble/overview
            if len(content) > 50 and not records:
                records.append(orient_record(
                    instruction=f"What is {source_name} and what does it do?",
                    response=content,
                    source=source_name,
                    source_type=source_type,
                ))
            i += 2
            continue

        if len(content) > 30:
            instruction = f"Explain {heading} in {source_name}."
            heading_lower = heading.lower()
            if "install" in heading_lower or "setup" in heading_lower:
                instruction = f"How do I set up {heading} in {source_name}?"
            elif "api" in heading_lower or "endpoint" in heading_lower:
                instruction = f"What is the {heading} API in {source_name}?"
            elif "example" in heading_lower or "usage" in heading_lower:
                instruction = f"Show an example of {heading} in {source_name}."
            elif "error" in heading_lower or "troubleshoot" in heading_lower:
                instruction = f"How do I fix {heading} in {source_name}?"
            elif "config" in heading_lower or "option" in heading_lower:
                instruction = f"How do I configure {heading} in {source_name}?"
            elif "security" in heading_lower or "auth" in heading_lower:
                instruction = f"How does {heading} work in {source_name} for security?"

            records.append(orient_record(
                instruction=instruction,
                response=content,
                source=source_name,
                source_type=source_type,
            ))
        i += 2

    return records


# ---------------------------------------------------------------------------
# Batch writer
# ---------------------------------------------------------------------------


def write_oriented_jsonl(
    records: list[OrientedRecord],
    output_path: str | Path,
    append: bool = False,
) -> int:
    """Write oriented records to JSONL file. Returns count written."""
    mode = "a" if append else "w"
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with open(path, mode, encoding="utf-8") as f:
        for rec in records:
            d = rec.to_dict()
            d["id"] = rec.record_id
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            written += 1

    return written


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick self-test
    test_text = """
    ## Authentication with OAuth2

    To authenticate your API requests, use OAuth2 bearer tokens.

    ```python
    import requests

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://api.example.com/data", headers=headers)
    ```

    Always validate tokens server-side to prevent injection attacks.
    Ensure TLS 1.3 is enforced on all endpoints.
    """

    rec = orient_record(
        instruction="How does authentication work?",
        response=test_text.strip(),
        source="test",
        source_type="self_test",
    )

    print(f"Layer:    {rec.layer}")
    print(f"Category: {rec.category}")
    print(f"Tongue:   {rec.tongue_profile}")
    print(f"Null:     {rec.null_pattern}")
    print(f"Dominant: {rec.dominant_tongue}")
    print(f"ID:       {rec.record_id}")
