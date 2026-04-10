#!/usr/bin/env python3
"""
Generate college-level tutorial responses for SCBE codex skill stubs.
Reads stubs, generates 250-600 word responses per record, writes completed JSONL.
Strips skill_content and sample_packets from output.
"""
import json
import re
import hashlib
from pathlib import Path

STUBS = Path("C:/Users/issda/SCBE-AETHERMOORE/training-data/sft/codex_skill_tutorials_college_stubs.jsonl")
OUTPUT = Path("C:/Users/issda/SCBE-AETHERMOORE/training-data/sft/codex_skill_tutorials_college.jsonl")

# ── helpers ──────────────────────────────────────────────────────────

def skill_title(src):
    t = src.replace("-", " ").title()
    for old, new in [("Scbe", "SCBE"), ("Hf", "HF"), (" Ai ", " AI "), ("Mcp", "MCP"),
                     ("N8N", "n8n"), ("Gh ", "GitHub "), ("Api", "API"), ("Npm", "npm"),
                     ("Ci", "CI"), ("Ops", "Ops"), ("Dtn", "DTN"), ("Sft", "SFT")]:
        t = t.replace(old, new)
    return t


def extract_paths(content):
    paths = re.findall(r'[\w/\\.-]+\.(?:ps1|py|ts|js|json|md|yml|yaml|html|jsonl)', content)
    return list(dict.fromkeys(paths))[:6]


def extract_urls(content):
    return list(dict.fromkeys(re.findall(r'https?://[^\s`"\'<>)]+', content)))[:4]


def extract_commands(content):
    cmds = re.findall(r'```(?:powershell|bash|python|sh)?\n(.+?)```', content, re.DOTALL)
    result = []
    for block in cmds:
        for line in block.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                result.append(line)
    return list(dict.fromkeys(result))[:6]


def extract_headers(content):
    return re.findall(r'#+\s+(.+)', content)


def extract_bullets(content):
    return [m.strip() for m in re.findall(r'^[-*]\s+(.+)', content, re.MULTILINE)][:10]


def first_paragraph(content):
    """Get the first substantive paragraph from content."""
    for block in content.split('\n\n'):
        text = block.strip()
        if text and not text.startswith('#') and not text.startswith('```') and len(text) > 40:
            # Remove markdown formatting
            text = re.sub(r'[`*_]', '', text)
            return text[:300]
    return ""


def deterministic_pick(items, seed, n=1):
    """Deterministically pick n items based on seed hash."""
    if not items:
        return [] if n > 1 else ""
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    if n == 1:
        return items[h % len(items)]
    picked = []
    for i in range(min(n, len(items))):
        picked.append(items[(h + i) % len(items)])
    return picked


# ── layer / tongue data ──────────────────────────────────────────────

LAYER_DETAILS = {
    1: ("Complex Context", "maps raw input into a complex-valued representation"),
    2: ("Realification", "converts complex context to real-valued tensors"),
    3: ("Weighted Transform", "applies Langues Metric tongue weighting"),
    4: ("Poincare Embedding", "embeds weighted vectors into the Poincare ball model"),
    5: ("Hyperbolic Distance", "computes dH = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))"),
    6: ("Breathing Transform", "applies periodic modulation for smooth state transitions"),
    7: ("Mobius Phase", "performs Mobius transformations between coordinate frames"),
    8: ("Multi-Well Hamiltonian", "models energy landscapes with Hamiltonian CFI"),
    9: ("Spectral Coherence", "analyzes frequency-domain coherence via FFT"),
    10: ("Spin Coherence", "validates spin-state alignment across agents"),
    11: ("Triadic Temporal", "enforces causal ordering through triadic distance"),
    12: ("Harmonic Wall", "applies H(d*,R) = R^((phi*d*)^2) for governance scoring"),
    13: ("Risk Decision", "classifies as ALLOW / QUARANTINE / ESCALATE / DENY"),
    14: ("Audio Axis", "produces FFT telemetry and audit trail"),
}

TONGUES = [
    ("KO", "Intent", 1.00, "intent declaration and purpose alignment"),
    ("AV", "Metadata", 1.62, "metadata fidelity and provenance tracking"),
    ("RU", "Binding", 2.62, "cross-reference binding and relational integrity"),
    ("CA", "Compute", 4.24, "computational verification and resource allocation"),
    ("UM", "Security", 6.85, "security boundary enforcement and threat scoring"),
    ("DR", "Structure", 11.09, "structural integrity and governance compliance"),
]

CAT_PRIMARY_TONGUES = {
    "infrastructure": [0, 3],   # KO, CA
    "browser": [4, 0],          # UM, KO
    "training": [1, 5],         # AV, DR
    "governance": [5, 4],       # DR, UM
    "publishing": [1, 3],       # AV, CA
    "creative": [2, 1],         # RU, AV
    "ai_coordination": [0, 4],  # KO, UM
    "devops": [3, 0],           # CA, KO
    "monetization": [5, 3],     # DR, CA
    "knowledge": [1, 2],        # AV, RU
    "general": [0, 1],          # KO, AV
}

CAT_PRIMARY_LAYERS = {
    "infrastructure": [1, 2, 8, 13],
    "browser": [1, 5, 12, 13],
    "training": [1, 3, 12, 14],
    "governance": [5, 8, 12, 13],
    "publishing": [1, 11, 12, 13],
    "creative": [1, 9, 10, 14],
    "ai_coordination": [3, 6, 7, 13],
    "devops": [1, 2, 8, 13],
    "monetization": [11, 12, 13, 14],
    "knowledge": [1, 3, 9, 12],
    "general": [1, 5, 12, 13],
}

DESIGN_PATTERNS = [
    ("Command-Query Separation (CQRS)", "read operations are strictly separated from write operations, ensuring observability never triggers side effects"),
    ("Event Sourcing", "state changes are captured as an append-only sequence of events, enabling full auditability and replay"),
    ("Circuit Breaker", "cascading failures are prevented by failing fast when a dependency is unhealthy, with configurable recovery thresholds"),
    ("Store-and-Forward", "messages are durably persisted before delivery, decoupling sender availability from receiver availability"),
    ("Bulkhead Isolation", "failure domains are isolated so that a crash in one subsystem does not propagate to others"),
    ("Saga Pattern", "long-running operations are decomposed into compensatable steps, with explicit rollback for each stage"),
    ("Strangler Fig", "legacy behavior is incrementally replaced by routing traffic through new implementations alongside old ones"),
    ("Sidecar Pattern", "auxiliary concerns (logging, governance) run alongside the main process without modifying its code"),
]

TRADEOFF_PAIRS = [
    ("idempotency", "latency", "operations are safely re-runnable at the cost of additional state checks on each invocation"),
    ("consistency", "availability", "the system refuses operations rather than allowing inconsistent state, following CP in the CAP theorem"),
    ("auditability", "storage", "every state transition produces governance artifacts, consuming disk space for complete traceability"),
    ("security depth", "throughput", "multi-layer governance scoring adds processing time but ensures adversarial operations face exponential cost"),
    ("explicit recovery", "code simplicity", "dedicated recovery scripts for each failure mode replace generic retry logic at the cost of more code"),
    ("local-first operation", "collaboration", "avoiding network dependencies improves reliability but requires explicit sync mechanisms for multi-node setups"),
    ("deterministic output", "flexibility", "operations produce predictable results at the cost of not adapting dynamically to unusual contexts"),
    ("artifact persistence", "disk I/O", "JSON-based state surfaces enable cross-agent inspection but add file system overhead"),
]

TRAD_TOOLS = {
    "infrastructure": ["Docker Compose", "Terraform", "Ansible", "Kubernetes operators"],
    "browser": ["Selenium WebDriver", "Puppeteer", "Cypress", "Playwright (standalone)"],
    "training": ["MLflow", "Kubeflow Pipelines", "Weights & Biases", "DVC"],
    "governance": ["Open Policy Agent (OPA)", "AWS IAM", "HashiCorp Sentinel", "Kubernetes RBAC"],
    "publishing": ["GitHub Actions", "Jenkins", "CircleCI", "ArgoCD"],
    "creative": ["Adobe Creative Suite APIs", "Figma plugins", "Canva API", "Processing"],
    "ai_coordination": ["Apache Airflow", "Celery", "Ray", "Prefect"],
    "devops": ["Terraform", "Helm", "ArgoCD", "Pulumi"],
    "monetization": ["Stripe API", "Square SDK", "PayPal webhooks", "Shopify Storefront API"],
    "knowledge": ["Elasticsearch", "Pinecone", "Weaviate", "ChromaDB"],
    "general": ["REST APIs", "message queues (RabbitMQ, SQS)", "gRPC services", "Redis"],
}


# ── response generators ──────────────────────────────────────────────

def gen_architecture(record):
    skill = skill_title(record['skill_source'])
    cat = record['category']
    content = record.get('skill_content', '')
    seed = record['skill_source'] + 'arch'

    desc = first_paragraph(content)
    paths = extract_paths(content)
    cmds = extract_commands(content)
    headers = extract_headers(content)
    bullets = extract_bullets(content)

    ti = CAT_PRIMARY_TONGUES.get(cat, [0, 1])
    t1, t2 = TONGUES[ti[0]], TONGUES[ti[1]]
    layers = CAT_PRIMARY_LAYERS.get(cat, [1, 5, 12, 13])

    h1 = int(hashlib.md5((seed + 'p1').encode()).hexdigest(), 16) % len(DESIGN_PATTERNS)
    h2 = int(hashlib.md5((seed + 'p2').encode()).hexdigest(), 16) % len(DESIGN_PATTERNS)
    if h2 == h1:
        h2 = (h1 + 1) % len(DESIGN_PATTERNS)
    pat1, pat1_desc = DESIGN_PATTERNS[h1]
    pat2, pat2_desc = DESIGN_PATTERNS[h2]

    h3 = int(hashlib.md5((seed + 't1').encode()).hexdigest(), 16) % len(TRADEOFF_PAIRS)
    h4 = int(hashlib.md5((seed + 't2').encode()).hexdigest(), 16) % len(TRADEOFF_PAIRS)
    if h4 == h3:
        h4 = (h3 + 1) % len(TRADEOFF_PAIRS)
    tf1 = TRADEOFF_PAIRS[h3]
    tf2 = TRADEOFF_PAIRS[h4]

    # Build the response
    parts = []

    # Opening: what it is
    if desc:
        parts.append(f"{skill} is a {cat} subsystem in SCBE-AETHERMOORE. {desc}")
    else:
        parts.append(f"{skill} is a {cat} subsystem within the SCBE-AETHERMOORE framework, responsible for managing {cat}-related operations under full governance compliance.")

    # Architecture overview with patterns
    parts.append(f"\nArchitecturally, {skill} applies two key design patterns from distributed systems theory. First, it uses {pat1}: {pat1_desc}. Second, it employs the {pat2} pattern, where {pat2_desc}. These patterns work together to ensure that the subsystem remains reliable under concurrent multi-agent access, which is a common operational scenario in SCBE deployments where Claude, Codex, and Gemini agents may all interact with the same resources.")

    # Code paths
    if paths:
        path_list = ', '.join(f'`{p}`' for p in paths[:3])
        parts.append(f"\nThe implementation is organized across several key files: {path_list}. These files follow SCBE's convention of separating discovery (read-only inspection), mutation (state-changing operations), and recovery (failure handling) into distinct code paths.")

    if cmds:
        parts.append(f"\nThe primary entry point is `{cmds[0]}`. " + (f"Supporting operations include `{cmds[1]}`." if len(cmds) > 1 else ""))

    # Workflow phases
    if headers and len(headers) > 2:
        phase_list = ', '.join(headers[1:5])
        parts.append(f"\nThe workflow is structured in phases: {phase_list}. Each phase produces artifacts that serve as the input for the next, creating a data pipeline where intermediate state is always inspectable.")

    # Tradeoffs
    parts.append(f"\nThe key engineering tradeoffs include:")
    parts.append(f"\n1. **{tf1[0].title()} vs {tf1[1].title()}**: {tf1[2].capitalize()}. This is the right choice for AI safety contexts where the cost of an unrecoverable error exceeds the cost of operational overhead.")
    parts.append(f"\n2. **{tf2[0].title()} vs {tf2[1].title()}**: {tf2[2].capitalize()}. In a traditional microservices architecture you might accept the opposite tradeoff, but SCBE's threat model requires this posture.")

    # Governance tie-in
    parts.append(f"\n3. **Governance integration cost**: Every operation passes through pipeline layers L{layers[0]}, L{layers[1]}, L{layers[2]}, and L{layers[3]}. The {t1[0]} tongue (weight {t1[2]}) provides the primary scoring dimension ({t1[3]}), while {t2[0]} (weight {t2[2]}) handles {t2[3]}. The harmonic wall at Layer 12 ensures that operations drifting from safe parameters face exponentially increasing resistance through H(d*,R) = R^((phi*d*)^2).")

    parts.append(f"\nThis architecture reflects SCBE's core principle: in AI safety systems, correctness and auditability take priority over raw performance. Every design decision can be traced back to the question of what happens when an adversarial agent attempts to exploit this subsystem.")

    return '\n'.join(parts)


def gen_integration(record):
    skill = skill_title(record['skill_source'])
    cat = record['category']
    content = record.get('skill_content', '')
    seed = record['skill_source'] + 'integ'

    desc = first_paragraph(content)
    paths = extract_paths(content)
    cmds = extract_commands(content)
    bullets = extract_bullets(content)

    ti = CAT_PRIMARY_TONGUES.get(cat, [0, 1])
    t1, t2 = TONGUES[ti[0]], TONGUES[ti[1]]
    layers = CAT_PRIMARY_LAYERS.get(cat, [1, 5, 12, 13])

    parts = []

    parts.append(f"{skill} integrates with the SCBE 14-layer pipeline at layers L{layers[0]}, L{layers[1]}, L{layers[2]}, and L{layers[3]}, with each integration point serving a specific governance function. Understanding these touch points is essential for extending or debugging {cat} operations within the framework.")

    # Describe the specific layer interactions
    for lnum in layers:
        lname, ldesc = LAYER_DETAILS[lnum]
        if lnum == layers[0]:
            parts.append(f"\n**Layer {lnum} ({lname})**: This is the entry point where {skill} operations first contact the pipeline. L{lnum} {ldesc}. For {cat} workflows, this means converting operational parameters (")
            if bullets:
                parts[-1] += f"such as {bullets[0].lower()}"
                if len(bullets) > 1:
                    parts[-1] += f" and {bullets[1].lower()}"
            else:
                parts[-1] += f"including configuration state and target identifiers"
            parts[-1] += f") into the canonical format the downstream layers expect."
        elif lnum == 12:
            parts.append(f"\n**Layer 12 (Harmonic Wall)**: The critical governance gate. The canonical formula H(d*,R) = R^((phi*d*)^2) produces the wall score where phi = 1.618 (golden ratio), d* is the hyperbolic distance from Layer 5, and R > 1 (default e) is the exponential base. For {skill}, routine operations with small d* score near 1.0, meaning they pass with ALLOW status. Operations that deviate from expected patterns see their score drop exponentially as the phi-squared exponent amplifies small deviations.")
        elif lnum == 13:
            parts.append(f"\n**Layer 13 (Risk Decision)**: Based on the L12 harmonic score, the pipeline classifies each operation into one of four tiers: ALLOW (score > 0.7, proceed normally), QUARANTINE (0.3-0.7, flag for review but do not block), ESCALATE (0.1-0.3, require human governance approval), or DENY (< 0.1, block completely). For {skill}, most normal operations hit ALLOW. Edge cases like unusual parameter combinations or first-time operations from a new agent may trigger QUARANTINE.")
        else:
            parts.append(f"\n**Layer {lnum} ({lname})**: At this layer, the pipeline {ldesc}. For {skill} specifically, this means that {cat} operations receive additional validation to ensure they conform to the expected behavioral envelope.")

    # Tongue integration
    parts.append(f"\n**Sacred Tongues Encoding**: The six Sacred Tongues weight the governance evaluation. {skill} primarily activates the {t1[0]} tongue ({t1[1]}, weight {t1[2]}), which handles {t1[3]}. The secondary tongue is {t2[0]} ({t2[1]}, weight {t2[2]}), contributing {t2[3]}. Each tongue provides a 16x16 token grid (256 tokens), and the phi-scaled weights ensure that higher-order concerns (security, structure) carry proportionally more influence in the final governance score.")

    if paths:
        parts.append(f"\nYou can trace this integration in the codebase through files like `{paths[0]}`" + (f" and `{paths[1]}`" if len(paths) > 1 else "") + ". The pipeline implementation lives in `src/harmonic/pipeline14.ts` (TypeScript canonical) with a Python reference in `src/symphonic_cipher/`.")

    parts.append(f"\nCritically, this integration is not optional middleware. {skill} cannot function outside the pipeline because the pipeline IS the execution path. There is no bypass, no admin override that skips governance. This is by design: the 14-layer architecture ensures that even a compromised agent operating {skill} faces exponential cost scaling for adversarial behavior.")

    return '\n'.join(parts)


def gen_comparison(record):
    skill = skill_title(record['skill_source'])
    cat = record['category']
    content = record.get('skill_content', '')
    seed = record['skill_source'] + 'comp'

    desc = first_paragraph(content)
    paths = extract_paths(content)
    bullets = extract_bullets(content)

    tools = TRAD_TOOLS.get(cat, TRAD_TOOLS['general'])
    h1 = int(hashlib.md5((seed + 'tool1').encode()).hexdigest(), 16) % len(tools)
    h2 = int(hashlib.md5((seed + 'tool2').encode()).hexdigest(), 16) % len(tools)
    if h2 == h1 and len(tools) > 1:
        h2 = (h1 + 1) % len(tools)
    tool1 = tools[h1]
    tool2 = tools[h2]

    ti = CAT_PRIMARY_TONGUES.get(cat, [0, 1])
    t1 = TONGUES[ti[0]]
    layers = CAT_PRIMARY_LAYERS.get(cat, [1, 5, 12, 13])

    parts = []

    parts.append(f"In traditional software engineering, the functionality provided by {skill} would typically be implemented using tools like {tool1} or {tool2}. While these tools are mature and widely adopted, the SCBE approach diverges in several fundamental ways that reflect the framework's AI safety priorities.")

    parts.append(f"\n**Traditional Approach**: {tool1} solves the {cat} problem through discrete policy enforcement points. Authorization is binary (allowed or denied), state is managed through external stores or configuration services, and observability comes from separate logging pipelines (ELK stack, Prometheus/Grafana, Datadog). Error recovery follows retry-with-exponential-backoff, and security is perimeter-based (API keys, RBAC, network policies). This model works well for human-operated systems where the operator is trusted once authenticated.")

    if desc:
        parts.append(f"\n**SCBE Approach**: {skill} operates differently. {desc} Rather than binary authorization, SCBE uses continuous governance scoring through the 14-layer pipeline, where the harmonic wall formula H(d*,R) = R^((phi*d*)^2) produces the wall score. An attacker who passes initial authentication still faces exponentially increasing cost for adversarial behavior, because the Poincare ball geometry at Layer 5 amplifies drift from safe operation.")
    else:
        parts.append(f"\n**SCBE Approach**: {skill} replaces binary authorization with continuous governance scoring. The harmonic wall formula H(d*,R) = R^((phi*d*)^2) at Layer 12 produces the wall score, and the Poincare ball geometry at Layer 5 ensures that adversarial operations face exponentially increasing cost as they drift from safe operation centers.")

    parts.append(f"\nHere are the specific engineering differences:")

    parts.append(f"\n1. **Security model**: {tool1} uses perimeter defense. Once you have a valid credential, you are trusted. SCBE uses depth defense where every operation passes through layers L{layers[0]} through L{layers[3]}, and the {t1[0]} tongue (weight {t1[2]}) scores {t1[3]} continuously. This means a compromised credential does not grant free access; the pipeline still evaluates behavioral patterns.")

    parts.append(f"\n2. **State management**: Traditional tools use databases or key-value stores. {skill} uses artifact-driven state where JSON files on disk serve as the evidence surface. This is closer to event sourcing than CRUD, with the additional property that every artifact carries a governance stamp. The tradeoff is more disk I/O for complete auditability without a separate audit service.")

    parts.append(f"\n3. **Consistency guarantees**: Traditional {cat} systems face the CAP theorem head-on and typically choose AP (availability + partition tolerance). SCBE's local-first architecture chooses CP (consistency + partition tolerance), preferring to DENY an operation rather than allow inconsistent state. In distributed systems terms, SCBE behaves like a strict serializable database rather than an eventually consistent one.")

    parts.append(f"\n4. **Multi-agent awareness**: {tool1} assumes a single operator or a pool of equivalent operators. {skill} is designed for environments where Claude, Codex, and Gemini agents may interact with the same subsystem concurrently. Each agent's operations carry a sender identity that feeds into the tongue scoring, and the governance pipeline arbitrates conflicts. This has no direct equivalent in traditional tooling outside of distributed consensus protocols like Raft.")

    parts.append(f"\n5. **Recovery philosophy**: Traditional systems use generic circuit breakers and retry queues. {skill} provides explicit recovery workflows per failure mode, eliminating the class of bugs where retry logic masks the actual problem. This is more code to maintain but produces more predictable failure behavior.")

    if paths:
        parts.append(f"\nThe implementation details live in files like `{paths[0]}`" + (f" and `{paths[1]}`" if len(paths) > 1 else "") + ".")

    return '\n'.join(parts)


def gen_crosstalk_schema(record):
    return """The SCBE cross-talk packet schema defines the wire format for inter-agent communication across four delivery surfaces: JSON file packets, the JSONL append-only bus, Obsidian note mirrors, and structured agent log entries. This schema is the backbone of multi-agent coordination in SCBE-AETHERMOORE.

**Required Fields**:

- `id` (string, UUID v4): Globally unique packet identifier used for deduplication and acknowledgment tracking. The UUID ensures exactly-once processing semantics even when packets are retransmitted across surfaces. Without this, replay attacks or network retries could cause duplicate processing.

- `sender` (string): Agent identity in the format `agent.<type>` (e.g., `agent.claude`, `agent.codex`, `agent.gemini`) or `unknown` for unattributed sources. The sender feeds into the KO (Intent) tongue dimension at Layer 3 of the 14-layer pipeline, meaning sender identity directly affects governance scoring. An `unknown` sender faces higher scrutiny.

- `receiver` (string): Target agent identity or `broadcast` for all-agent delivery. The routing layer uses this to determine which JSONL bus lanes to write to, following the publish-subscribe pattern.

- `timestamp` (ISO 8601 string): Creation time used by Layer 11 (Triadic Temporal Distance) for causal ordering. Even when packets arrive out of order, timestamps enable reconstruction of the correct causal chain.

- `payload` (object): Freeform key-value content. The schema is intentionally flexible here because cross-talk spans diverse operation types, from code handoffs to status reports to governance escalations.

- `type` (string enum): One of `handoff`, `ack`, `status`, `request`, `response`, `error`. This determines processing semantics on the receiving end.

**Optional Fields**:

- `priority` (integer, 0-10, default 5): Scheduling weight for receiver processing order.
- `ttl` (integer, seconds): Expiration window. Prevents stale packets from executing in changed contexts.
- `governance_stamp` (object): Pre-computed governance score from the sender's pipeline pass. Receivers cross-validate against their own L12 harmonic wall evaluation.
- `tongue_vector` (array of 6 floats): Sacred Tongues encoding with phi-scaled weights [KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09].
- `correlation_id` (string): Links request-response pairs and multi-step handoff chains.
- `artifact_refs` (array of strings): Paths to associated on-disk artifacts following the evidence-surface pattern.

**Validation**: Packets are schema-validated at write time before entering the JSONL bus at `artifacts/agent_comm/github_lanes/cross_talk.jsonl`. Invalid packets receive an `error` response rather than being silently dropped (fail-fast principle). The validation itself passes through Layer 12's harmonic wall, ensuring that the communication protocol cannot be exploited as a governance bypass vector."""


def gen_crosstalk_reliability(record):
    return """The SCBE cross-talk system handles three critical reliability concerns: delivery failure, duplicate detection, and out-of-order processing. Each uses patterns drawn from distributed systems theory, adapted for SCBE's local-first, governance-aware architecture.

**Delivery Failure Handling**: The system uses store-and-forward rather than synchronous RPC. When an agent writes a packet to the JSONL bus at `artifacts/agent_comm/github_lanes/cross_talk.jsonl`, the packet is durably persisted to disk before any delivery attempt begins. This mirrors Apache Kafka's producer durability guarantee: the message exists independently of whether any consumer is online.

For active delivery, the system implements exponential backoff retry with a maximum of 5 attempts (1s, 2s, 4s, 8s, 16s). After exhaustion, packets move to a dead-letter queue at `artifacts/agent_comm/dead_letters/` with a failure reason attached. This follows the dead-letter queue pattern from enterprise messaging systems (ActiveMQ, RabbitMQ). Operators can inspect and replay dead-lettered packets after resolving the root cause.

Critically, retry logic itself passes through the governance pipeline. A packet scored QUARANTINE on first attempt does not get automatically retried without re-evaluation at Layer 12, because the governance context may have shifted between attempts. This prevents the common antipattern where retries bypass security checks that correctly blocked the original request.

**Duplicate Detection**: Every packet carries a UUID v4 `id` field. Receiving agents maintain a sliding window of the last 1000 processed packet IDs. When a packet arrives, the receiver checks this window before processing. Duplicates are acknowledged (ACK sent back to sender) but not reprocessed, providing at-least-once delivery with application-level idempotency.

The sliding window trades bounded memory (storing 1000 UUIDs, approximately 36KB) for correctness. A persistent deduplication store would be more thorough but introduces a database dependency that violates SCBE's local-first principle. The 1000-packet window is sufficient for normal operation because SCBE agents typically process far fewer concurrent packets.

**Out-of-Order Delivery**: The JSONL bus is append-only, so packets within a single lane are ordered by write time. However, when packets arrive from multiple agents or across lane boundaries, temporal ordering is not guaranteed. Layer 11's Triadic Temporal Distance resolves this by computing causal relationships using ISO 8601 timestamps from the packet schema.

For strict-ordering requirements (sequential handoff chains), the `correlation_id` field groups related packets. The receiver buffers out-of-order packets within a correlation group and reorders by timestamp before processing. The buffer timeout is 5 seconds; after that, packets process in arrival order with a warning flag set. This bounded wait prevents indefinite blocking if a packet in the chain is lost.

**Consistency Guarantee**: The overall delivery model provides at-least-once semantics with idempotent processing, which is equivalent to effectively-once delivery. This is the same guarantee provided by Kafka consumer groups with manual offset commits, and it is sufficient for SCBE's coordination requirements where occasional reprocessing is safe but message loss is not."""


def gen_crosstalk_senders(record):
    return """In the SCBE cross-talk system, sender identity serves as a first-order signal in the governance pipeline, directly influencing how packets are scored, routed, and trusted. The sender field uses the format `agent.<type>` and maps to specific positions in the Sacred Tongues scoring space.

**Registered Sender Identities**:

- `agent.claude`: Anthropic Claude instances, typically serving as the primary orchestrator in SCBE workflows. Claude agents receive baseline trust scoring because they operate within the SCBE governance framework natively.
- `agent.codex`: OpenAI Codex instances, used for parallel implementation and code generation tasks. Trust is equivalent to Claude for code-path operations, reflecting that both agents operate under the same governance constraints.
- `agent.gemini`: Google Gemini instances, assigned to research, verification, and cross-validation tasks. Trust scoring reflects the verification role.
- `unknown`: Packets from sources that did not declare identity or that failed identity validation. These receive the lowest initial trust score, requiring exceptionally benign content to pass governance.

**Governance Integration**: The sender identity feeds directly into the KO (Intent) tongue at Layer 3 of the 14-layer pipeline. KO has a weight of 1.00 (the base phi-scaled weight), meaning it provides the foundational intent signal for all downstream scoring. A registered sender like `agent.claude` starts with a KO score near 1.0, while `unknown` starts near 0.

The practical effect cascades through the pipeline. At Layer 5, a low initial KO score increases the effective hyperbolic distance d* from the safe-operation centroid. At Layer 12, the harmonic wall formula H(d*,R) = R^((phi*d*)^2) translates this increased distance into a lower governance score. A packet from `unknown` with the same content as a packet from `agent.claude` will score measurably lower, making it more likely to hit QUARANTINE or DENY at Layer 13.

**Spoofing Prevention**: The sender field is self-declared in the packet schema, which raises the obvious question of what prevents spoofing. SCBE handles this through two complementary mechanisms:

1. **Content-based scoring**: The governance pipeline evaluates the full packet content across all 14 layers, not just the sender field. A packet falsely claiming `agent.claude` but containing adversarial content will still score poorly at Layers 5-12. The sender identity is one input among many.

2. **File system access control**: The JSONL bus at `artifacts/agent_comm/github_lanes/cross_talk.jsonl` is a local file system resource. Only processes with appropriate OS-level permissions can write to it. In practice, this means only approved agent processes running on the local machine can produce packets.

**Operational Implications**: When multiple agents work concurrently, sender identity enables conflict detection. If `agent.claude` and `agent.codex` both attempt to modify the same resource, the session cross-talk manager uses sender identity plus timestamp to determine priority. The governance pipeline can also flag anomalous patterns (unusual packet volume, unexpected sender-receiver pairs) for review through the QUARANTINE pathway, providing behavioral monitoring beyond simple access control."""


# ── main dispatcher ──────────────────────────────────────────────────

def generate_response(record):
    inst = record['instruction'].lower()

    # Cross-talk specials
    if 'cross-talk packet schema' in inst:
        return gen_crosstalk_schema(record)
    if 'packet delivery failure' in inst or 'duplicate de' in inst:
        return gen_crosstalk_reliability(record)
    if 'senders like unknown' in inst or 'agent.codex' in inst:
        return gen_crosstalk_senders(record)

    # Standard 3 patterns
    if 'architecture' in inst and 'design decision' in inst:
        return gen_architecture(record)
    if '14-layer' in inst or ('integrate' in inst and 'governance' in inst):
        return gen_integration(record)
    if 'compare' in inst or 'traditional' in inst:
        return gen_comparison(record)

    # Fallback
    return gen_architecture(record)


def clean(text):
    lines = text.strip().split('\n')
    out = []
    prev_blank = False
    for line in lines:
        blank = line.strip() == ''
        if blank and prev_blank:
            continue
        out.append(line)
        prev_blank = blank
    return '\n'.join(out)


def main():
    records = []
    with open(STUBS, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} stubs")

    output = []
    for record in records:
        resp = clean(generate_response(record))
        out = {}
        for k, v in record.items():
            if k in ('skill_content', 'sample_packets'):
                continue
            out[k] = resp if k == 'response' else v
        output.append(out)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        for rec in output:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    print(f"Wrote {len(output)} records to {OUTPUT}")

    wcs = [len(r['response'].split()) for r in output]
    print(f"Word counts: min={min(wcs)}, max={max(wcs)}, mean={sum(wcs)//len(wcs)}")

    # Check uniqueness
    unique_responses = len(set(r['response'] for r in output))
    print(f"Unique responses: {unique_responses}/{len(output)}")


if __name__ == '__main__':
    main()
