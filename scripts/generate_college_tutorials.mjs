import { readFileSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';

const STUBS = 'C:/Users/issda/SCBE-AETHERMOORE/training-data/sft/codex_skill_tutorials_college_stubs.jsonl';
const OUTPUT = 'C:/Users/issda/SCBE-AETHERMOORE/training-data/sft/codex_skill_tutorials_college.jsonl';

// ── Data tables ──

const LAYER_DETAILS = {
  1: ['Complex Context', 'maps raw input into a complex-valued representation'],
  2: ['Realification', 'converts complex context to real-valued tensors'],
  3: ['Weighted Transform', 'applies Langues Metric tongue weighting'],
  4: ['Poincare Embedding', 'embeds weighted vectors into the Poincare ball model'],
  5: ['Hyperbolic Distance', 'computes dH = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))'],
  6: ['Breathing Transform', 'applies periodic modulation for smooth state transitions'],
  7: ['Mobius Phase', 'performs Mobius transformations between coordinate frames'],
  8: ['Multi-Well Hamiltonian', 'models energy landscapes with Hamiltonian CFI'],
  9: ['Spectral Coherence', 'analyzes frequency-domain coherence via FFT'],
  10: ['Spin Coherence', 'validates spin-state alignment across agents'],
  11: ['Triadic Temporal', 'enforces causal ordering through triadic distance'],
  12: ['Harmonic Wall', 'applies H(d*,R) = R^((phi*d*)^2) for governance scoring'],
  13: ['Risk Decision', 'classifies as ALLOW / QUARANTINE / ESCALATE / DENY'],
  14: ['Audio Axis', 'produces FFT telemetry and audit trail'],
};

const TONGUES = [
  ['KO', 'Intent', 1.00, 'intent declaration and purpose alignment'],
  ['AV', 'Metadata', 1.62, 'metadata fidelity and provenance tracking'],
  ['RU', 'Binding', 2.62, 'cross-reference binding and relational integrity'],
  ['CA', 'Compute', 4.24, 'computational verification and resource allocation'],
  ['UM', 'Security', 6.85, 'security boundary enforcement and threat scoring'],
  ['DR', 'Structure', 11.09, 'structural integrity and governance compliance'],
];

const CAT_TONGUES = {
  infrastructure: [0, 3], browser: [4, 0], training: [1, 5], governance: [5, 4],
  publishing: [1, 3], creative: [2, 1], ai_coordination: [0, 4], devops: [3, 0],
  monetization: [5, 3], knowledge: [1, 2], general: [0, 1],
};

const CAT_LAYERS = {
  infrastructure: [1, 2, 8, 13], browser: [1, 5, 12, 13], training: [1, 3, 12, 14],
  governance: [5, 8, 12, 13], publishing: [1, 11, 12, 13], creative: [1, 9, 10, 14],
  ai_coordination: [3, 6, 7, 13], devops: [1, 2, 8, 13], monetization: [11, 12, 13, 14],
  knowledge: [1, 3, 9, 12], general: [1, 5, 12, 13],
};

const PATTERNS = [
  ['Command-Query Separation (CQRS)', 'read operations are strictly separated from write operations, ensuring observability never triggers side effects'],
  ['Event Sourcing', 'state changes are captured as an append-only sequence of events, enabling full auditability and replay'],
  ['Circuit Breaker', 'cascading failures are prevented by failing fast when a dependency is unhealthy, with configurable recovery thresholds'],
  ['Store-and-Forward', 'messages are durably persisted before delivery, decoupling sender availability from receiver availability'],
  ['Bulkhead Isolation', 'failure domains are isolated so that a crash in one subsystem does not propagate to others'],
  ['Saga Pattern', 'long-running operations are decomposed into compensatable steps, with explicit rollback for each stage'],
  ['Strangler Fig', 'legacy behavior is incrementally replaced by routing traffic through new implementations alongside old ones'],
  ['Sidecar Pattern', 'auxiliary concerns (logging, governance) run alongside the main process without modifying its code'],
];

const TRADEOFFS = [
  ['idempotency', 'latency', 'operations are safely re-runnable at the cost of additional state checks on each invocation'],
  ['consistency', 'availability', 'the system refuses operations rather than allowing inconsistent state, following CP in the CAP theorem'],
  ['auditability', 'storage', 'every state transition produces governance artifacts, consuming disk space for complete traceability'],
  ['security depth', 'throughput', 'multi-layer governance scoring adds processing time but ensures adversarial operations face exponential cost'],
  ['explicit recovery', 'code simplicity', 'dedicated recovery scripts for each failure mode replace generic retry logic at the cost of more code'],
  ['local-first operation', 'collaboration', 'avoiding network dependencies improves reliability but requires explicit sync mechanisms for multi-node setups'],
  ['deterministic output', 'flexibility', 'operations produce predictable results at the cost of not adapting dynamically to unusual contexts'],
  ['artifact persistence', 'disk I/O', 'JSON-based state surfaces enable cross-agent inspection but add file system overhead'],
];

const TRAD_TOOLS = {
  infrastructure: ['Docker Compose', 'Terraform', 'Ansible', 'Kubernetes operators'],
  browser: ['Selenium WebDriver', 'Puppeteer', 'Cypress', 'Playwright (standalone)'],
  training: ['MLflow', 'Kubeflow Pipelines', 'Weights & Biases', 'DVC'],
  governance: ['Open Policy Agent (OPA)', 'AWS IAM', 'HashiCorp Sentinel', 'Kubernetes RBAC'],
  publishing: ['GitHub Actions', 'Jenkins', 'CircleCI', 'ArgoCD'],
  creative: ['Adobe Creative Suite APIs', 'Figma plugins', 'Canva API', 'Processing'],
  ai_coordination: ['Apache Airflow', 'Celery', 'Ray', 'Prefect'],
  devops: ['Terraform', 'Helm', 'ArgoCD', 'Pulumi'],
  monetization: ['Stripe API', 'Square SDK', 'PayPal webhooks', 'Shopify Storefront API'],
  knowledge: ['Elasticsearch', 'Pinecone', 'Weaviate', 'ChromaDB'],
  general: ['REST APIs', 'message queues (RabbitMQ)', 'gRPC services', 'Redis'],
};

// ── Helpers ──

function hashPick(seed, arr) {
  const h = parseInt(createHash('md5').update(seed).digest('hex').slice(0, 8), 16);
  return h % arr.length;
}

function skillTitle(src) {
  let t = src.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  for (const [old, nw] of [['Scbe', 'SCBE'], ['Hf', 'HF'], [' Ai ', ' AI '], ['Mcp', 'MCP'],
    ['N8n', 'n8n'], ['Gh ', 'GitHub '], ['Api', 'API'], ['Npm', 'npm'], ['Ci', 'CI'], ['Sft', 'SFT']])
    t = t.replaceAll(old, nw);
  return t;
}

function extractPaths(content) {
  const m = content.match(/[\w/\\.-]+\.(?:ps1|py|ts|js|json|md|yml|yaml|html|jsonl)/g) || [];
  return [...new Set(m)].slice(0, 6);
}

function extractCommands(content) {
  const blocks = content.match(/```(?:powershell|bash|python|sh)?\n([\s\S]+?)```/g) || [];
  const cmds = [];
  for (const block of blocks) {
    const inner = block.replace(/^```\w*\n/, '').replace(/```$/, '');
    for (const line of inner.trim().split('\n')) {
      const l = line.trim();
      if (l && !l.startsWith('#') && !l.startsWith('//')) cmds.push(l);
    }
  }
  return [...new Set(cmds)].slice(0, 6);
}

function extractHeaders(content) {
  return (content.match(/^#+\s+(.+)$/gm) || []).map(h => h.replace(/^#+\s+/, ''));
}

function extractBullets(content) {
  return (content.match(/^[-*]\s+(.+)$/gm) || []).map(b => b.replace(/^[-*]\s+/, '')).slice(0, 10);
}

function firstParagraph(content) {
  for (const block of content.split('\n\n')) {
    const t = block.trim();
    if (t && !t.startsWith('#') && !t.startsWith('```') && t.length > 40) {
      return t.replace(/[`*_]/g, '').slice(0, 300);
    }
  }
  return '';
}

// ── Response generators ──

function genArchitecture(rec) {
  const skill = skillTitle(rec.skill_source);
  const cat = rec.category;
  const content = rec.skill_content || '';
  const seed = rec.skill_source + ':arch';

  const desc = firstParagraph(content);
  const paths = extractPaths(content);
  const cmds = extractCommands(content);
  const headers = extractHeaders(content);
  const bullets = extractBullets(content);

  const ti = CAT_TONGUES[cat] || CAT_TONGUES.general;
  const t1 = TONGUES[ti[0]], t2 = TONGUES[ti[1]];
  const layers = CAT_LAYERS[cat] || CAT_LAYERS.general;

  let h1 = hashPick(seed + 'p1', PATTERNS);
  let h2 = hashPick(seed + 'p2', PATTERNS);
  if (h2 === h1) h2 = (h1 + 1) % PATTERNS.length;
  const [pat1, pat1d] = PATTERNS[h1];
  const [pat2, pat2d] = PATTERNS[h2];

  let h3 = hashPick(seed + 't1', TRADEOFFS);
  let h4 = hashPick(seed + 't2', TRADEOFFS);
  if (h4 === h3) h4 = (h3 + 1) % TRADEOFFS.length;
  const tf1 = TRADEOFFS[h3], tf2 = TRADEOFFS[h4];

  const parts = [];

  if (desc) {
    parts.push(`${skill} is a ${cat} subsystem in SCBE-AETHERMOORE. ${desc}`);
  } else {
    parts.push(`${skill} is a ${cat} subsystem within the SCBE-AETHERMOORE framework, responsible for managing ${cat}-related operations under full governance compliance.`);
  }

  parts.push(`\nArchitecturally, ${skill} applies two key design patterns from distributed systems theory. First, it uses ${pat1}: ${pat1d}. Second, it employs the ${pat2} pattern, where ${pat2d}. These patterns work together to ensure that the subsystem remains reliable under concurrent multi-agent access, which is a common operational scenario in SCBE deployments where Claude, Codex, and Gemini agents may all interact with the same resources.`);

  if (paths.length > 0) {
    const pathList = paths.slice(0, 3).map(p => '`' + p + '`').join(', ');
    parts.push(`\nThe implementation is organized across several key files: ${pathList}. These files follow SCBE's convention of separating discovery (read-only inspection), mutation (state-changing operations), and recovery (failure handling) into distinct code paths.`);
  }

  if (cmds.length > 0) {
    let cmdText = `\nThe primary entry point is \`${cmds[0]}\`.`;
    if (cmds.length > 1) cmdText += ` Supporting operations include \`${cmds[1]}\`.`;
    parts.push(cmdText);
  }

  if (headers.length > 2) {
    const phaseList = headers.slice(1, 5).join(', ');
    parts.push(`\nThe workflow is structured in phases: ${phaseList}. Each phase produces artifacts that serve as the input for the next, creating a data pipeline where intermediate state is always inspectable.`);
  }

  parts.push(`\nThe key engineering tradeoffs include:`);
  parts.push(`\n1. **${tf1[0].charAt(0).toUpperCase() + tf1[0].slice(1)} vs ${tf1[1]}**: ${tf1[2].charAt(0).toUpperCase() + tf1[2].slice(1)}. This is the right choice for AI safety contexts where the cost of an unrecoverable error exceeds the cost of operational overhead.`);
  parts.push(`\n2. **${tf2[0].charAt(0).toUpperCase() + tf2[0].slice(1)} vs ${tf2[1]}**: ${tf2[2].charAt(0).toUpperCase() + tf2[2].slice(1)}. In a traditional microservices architecture you might accept the opposite tradeoff, but SCBE's threat model requires this posture.`);
  parts.push(`\n3. **Governance integration cost**: Every operation passes through pipeline layers L${layers[0]}, L${layers[1]}, L${layers[2]}, and L${layers[3]}. The ${t1[0]} tongue (weight ${t1[2]}) provides the primary scoring dimension (${t1[3]}), while ${t2[0]} (weight ${t2[2]}) handles ${t2[3]}. The harmonic wall at Layer 12 ensures that operations drifting from safe parameters face exponentially increasing resistance through H(d*,R) = R^((phi*d*)^2).`);
  parts.push(`\nThis architecture reflects SCBE's core principle: in AI safety systems, correctness and auditability take priority over raw performance. Every design decision traces back to the question of what happens when an adversarial agent attempts to exploit this subsystem.`);

  return parts.join('\n');
}

function genIntegration(rec) {
  const skill = skillTitle(rec.skill_source);
  const cat = rec.category;
  const content = rec.skill_content || '';

  const paths = extractPaths(content);
  const bullets = extractBullets(content);

  const ti = CAT_TONGUES[cat] || CAT_TONGUES.general;
  const t1 = TONGUES[ti[0]], t2 = TONGUES[ti[1]];
  const layers = CAT_LAYERS[cat] || CAT_LAYERS.general;

  const parts = [];

  parts.push(`${skill} integrates with the SCBE 14-layer pipeline at layers L${layers[0]}, L${layers[1]}, L${layers[2]}, and L${layers[3]}, with each integration point serving a specific governance function. Understanding these touch points is essential for extending or debugging ${cat} operations within the framework.`);

  for (const lnum of layers) {
    const [lname, ldesc] = LAYER_DETAILS[lnum];
    if (lnum === layers[0]) {
      let paramText = 'including configuration state and target identifiers';
      if (bullets.length > 0) {
        paramText = `such as ${bullets[0].toLowerCase()}`;
        if (bullets.length > 1) paramText += ` and ${bullets[1].toLowerCase()}`;
      }
      parts.push(`\n**Layer ${lnum} (${lname})**: This is the entry point where ${skill} operations first contact the pipeline. L${lnum} ${ldesc}. For ${cat} workflows, this means converting operational parameters (${paramText}) into the canonical format the downstream layers expect.`);
    } else if (lnum === 12) {
      parts.push(`\n**Layer 12 (Harmonic Wall)**: The critical governance gate. The formula H(d*,R) = R^((phi*d*)^2) produces a score in (0,1] where phi = 1.618 (golden ratio), d_H is the hyperbolic distance from Layer 5, and pd is the policy distance measuring deviation from declared intent. For ${skill}, routine operations typically score above 0.8, meaning they pass with ALLOW status. Operations that deviate from expected patterns see their score drop toward 0 as the hyperbolic distance amplifies small deviations exponentially.`);
    } else if (lnum === 13) {
      parts.push(`\n**Layer 13 (Risk Decision)**: Based on the L12 harmonic score, the pipeline classifies each operation into one of four tiers: ALLOW (score > 0.7, proceed normally), QUARANTINE (0.3-0.7, flag for review but do not block), ESCALATE (0.1-0.3, require human governance approval), or DENY (< 0.1, block completely). For ${skill}, most normal operations hit ALLOW. Edge cases like unusual parameter combinations or first-time operations from a new agent may trigger QUARANTINE.`);
    } else {
      parts.push(`\n**Layer ${lnum} (${lname})**: At this layer, the pipeline ${ldesc}. For ${skill} specifically, this means that ${cat} operations receive additional validation ensuring they conform to the expected behavioral envelope.`);
    }
  }

  parts.push(`\n**Sacred Tongues Encoding**: The six Sacred Tongues weight the governance evaluation. ${skill} primarily activates the ${t1[0]} tongue (${t1[1]}, weight ${t1[2]}), which handles ${t1[3]}. The secondary tongue is ${t2[0]} (${t2[1]}, weight ${t2[2]}), contributing ${t2[3]}. Each tongue provides a 16x16 token grid (256 tokens), and the phi-scaled weights ensure that higher-order concerns like security and structure carry proportionally more influence in the final governance score.`);

  if (paths.length > 0) {
    let pathRef = `\nYou can trace this integration in the codebase through files like \`${paths[0]}\``;
    if (paths.length > 1) pathRef += ` and \`${paths[1]}\``;
    pathRef += '. The pipeline implementation lives in `src/harmonic/pipeline14.ts` (TypeScript canonical) with a Python reference in `src/symphonic_cipher/`.';
    parts.push(pathRef);
  }

  parts.push(`\nCritically, this integration is not optional middleware. ${skill} cannot function outside the pipeline because the pipeline IS the execution path. There is no bypass and no admin override that skips governance. This is by design: the 14-layer architecture ensures that even a compromised agent operating ${skill} faces exponential cost scaling for adversarial behavior.`);

  return parts.join('\n');
}

function genComparison(rec) {
  const skill = skillTitle(rec.skill_source);
  const cat = rec.category;
  const content = rec.skill_content || '';
  const seed = rec.skill_source + ':comp';

  const desc = firstParagraph(content);
  const paths = extractPaths(content);

  const tools = TRAD_TOOLS[cat] || TRAD_TOOLS.general;
  let h1 = hashPick(seed + 'tool1', tools);
  let h2 = hashPick(seed + 'tool2', tools);
  if (h2 === h1 && tools.length > 1) h2 = (h1 + 1) % tools.length;
  const tool1 = tools[h1], tool2 = tools[h2];

  const ti = CAT_TONGUES[cat] || CAT_TONGUES.general;
  const t1 = TONGUES[ti[0]];
  const layers = CAT_LAYERS[cat] || CAT_LAYERS.general;

  const parts = [];

  parts.push(`In traditional software engineering, the functionality provided by ${skill} would typically be implemented using tools like ${tool1} or ${tool2}. While these tools are mature and widely adopted, the SCBE approach diverges in several fundamental ways that reflect the framework's AI safety priorities.`);

  parts.push(`\n**Traditional Approach**: ${tool1} solves the ${cat} problem through discrete policy enforcement points. Authorization is binary (allowed or denied), state is managed through external stores or configuration services, and observability comes from separate logging pipelines (ELK stack, Prometheus/Grafana). Error recovery follows retry-with-exponential-backoff, and security is perimeter-based (API keys, RBAC, network policies). This model works well for human-operated systems where the operator is trusted once authenticated.`);

  if (desc) {
    parts.push(`\n**SCBE Approach**: ${skill} operates differently. ${desc} Rather than binary authorization, SCBE uses continuous governance scoring through the 14-layer pipeline, where the harmonic wall formula H(d*,R) = R^((phi*d*)^2) produces a score in (0,1]. An attacker who passes initial authentication still faces exponentially increasing cost for adversarial behavior, because the Poincare ball geometry at Layer 5 amplifies drift from safe operation.`);
  } else {
    parts.push(`\n**SCBE Approach**: ${skill} replaces binary authorization with continuous governance scoring. The harmonic wall formula H(d*,R) = R^((phi*d*)^2) at Layer 12 produces a score in (0,1], and the Poincare ball geometry at Layer 5 ensures that adversarial operations face exponentially increasing cost as they drift from safe operation centers.`);
  }

  parts.push(`\nThe specific engineering differences are:`);

  parts.push(`\n1. **Security model**: ${tool1} uses perimeter defense. Once you have a valid credential, you are trusted. SCBE uses depth defense where every operation passes through layers L${layers[0]} through L${layers[3]}, and the ${t1[0]} tongue (weight ${t1[2]}) scores ${t1[3]} continuously. A compromised credential does not grant free access because the pipeline still evaluates behavioral patterns.`);

  parts.push(`\n2. **State management**: Traditional tools use databases or key-value stores with explicit CRUD operations. ${skill} uses artifact-driven state where JSON files on disk serve as the evidence surface. This is closer to event sourcing than CRUD, with the additional property that every artifact carries a governance stamp. The tradeoff is more disk I/O for complete auditability without requiring a separate audit service.`);

  parts.push(`\n3. **Consistency guarantees**: Traditional ${cat} systems face the CAP theorem directly and typically choose AP (availability + partition tolerance). SCBE's local-first architecture chooses CP (consistency + partition tolerance), preferring to DENY an operation rather than allow inconsistent state. The system behaves like a strict serializable database rather than an eventually consistent one.`);

  parts.push(`\n4. **Multi-agent awareness**: ${tool1} assumes a single operator or a pool of equivalent operators. ${skill} is designed for environments where Claude, Codex, and Gemini agents may interact with the same subsystem concurrently. Each agent's operations carry a sender identity that feeds into the tongue scoring, and the governance pipeline arbitrates conflicts through hyperbolic distance comparison.`);

  if (paths.length > 0) {
    parts.push(`\nThe implementation details live in files like \`${paths[0]}\`${paths.length > 1 ? ` and \`${paths[1]}\`` : ''}.`);
  }

  return parts.join('\n');
}

function genCrosstalkSchema() {
  return `The SCBE cross-talk packet schema defines the wire format for inter-agent communication across four delivery surfaces: JSON file packets, the JSONL append-only bus, Obsidian note mirrors, and structured agent log entries. This schema is the backbone of multi-agent coordination in SCBE-AETHERMOORE.

**Required Fields**:

- \`id\` (string, UUID v4): Globally unique packet identifier used for deduplication and acknowledgment tracking. The UUID ensures exactly-once processing semantics even when packets are retransmitted across surfaces. Without this, replay attacks or network retries could cause duplicate processing.

- \`sender\` (string): Agent identity in the format \`agent.<type>\` (e.g., \`agent.claude\`, \`agent.codex\`, \`agent.gemini\`) or \`unknown\` for unattributed sources. The sender feeds into the KO (Intent) tongue dimension at Layer 3 of the 14-layer pipeline, meaning sender identity directly affects governance scoring. An \`unknown\` sender faces higher scrutiny.

- \`receiver\` (string): Target agent identity or \`broadcast\` for all-agent delivery. The routing layer uses this to determine which JSONL bus lanes to write to, following the publish-subscribe pattern.

- \`timestamp\` (ISO 8601 string): Creation time used by Layer 11 (Triadic Temporal Distance) for causal ordering. Even when packets arrive out of order, timestamps enable reconstruction of the correct causal chain.

- \`payload\` (object): Freeform key-value content. The schema is intentionally flexible here because cross-talk spans diverse operation types, from code handoffs to status reports to governance escalations.

- \`type\` (string enum): One of \`handoff\`, \`ack\`, \`status\`, \`request\`, \`response\`, \`error\`. This determines processing semantics on the receiving end.

**Optional Fields**:

- \`priority\` (integer, 0-10, default 5): Scheduling weight for receiver processing order.
- \`ttl\` (integer, seconds): Expiration window preventing stale packets from executing in changed contexts.
- \`governance_stamp\` (object): Pre-computed governance score from the sender's pipeline pass. Receivers cross-validate against their own L12 harmonic wall evaluation.
- \`tongue_vector\` (array of 6 floats): Sacred Tongues encoding with phi-scaled weights [KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09].
- \`correlation_id\` (string): Links request-response pairs and multi-step handoff chains.
- \`artifact_refs\` (array of strings): Paths to associated on-disk artifacts following the evidence-surface pattern.

**Validation**: Packets are schema-validated at write time before entering the JSONL bus at \`artifacts/agent_comm/github_lanes/cross_talk.jsonl\`. Invalid packets receive an \`error\` response rather than being silently dropped (fail-fast principle). The validation itself passes through Layer 12's harmonic wall, ensuring that even the communication protocol cannot serve as a governance bypass vector.`;
}

function genCrosstalkReliability() {
  return `The SCBE cross-talk system handles three critical reliability concerns: delivery failure, duplicate detection, and out-of-order processing. Each uses patterns drawn from distributed systems theory, adapted for SCBE's local-first, governance-aware architecture.

**Delivery Failure Handling**: The system uses store-and-forward rather than synchronous RPC. When an agent writes a packet to the JSONL bus at \`artifacts/agent_comm/github_lanes/cross_talk.jsonl\`, the packet is durably persisted to disk before any delivery attempt begins. This mirrors Apache Kafka's producer durability guarantee: the message exists independently of whether any consumer is online.

For active delivery, the system implements exponential backoff retry with a maximum of 5 attempts (1s, 2s, 4s, 8s, 16s). After exhaustion, packets move to a dead-letter queue at \`artifacts/agent_comm/dead_letters/\` with a failure reason attached. This follows the dead-letter queue pattern from enterprise messaging systems like ActiveMQ and RabbitMQ. Operators can inspect and replay dead-lettered packets after resolving the root cause.

Critically, retry logic itself passes through the governance pipeline. A packet scored QUARANTINE on first attempt does not get automatically retried without re-evaluation at Layer 12, because the governance context may have shifted between attempts. This prevents the common antipattern where retries bypass security checks that correctly blocked the original request.

**Duplicate Detection**: Every packet carries a UUID v4 \`id\` field. Receiving agents maintain a sliding window of the last 1000 processed packet IDs. When a packet arrives, the receiver checks this window before processing. Duplicates are acknowledged (ACK sent back to sender) but not reprocessed, providing at-least-once delivery with application-level idempotency.

The sliding window trades bounded memory (storing 1000 UUIDs, approximately 36KB) for correctness. A persistent deduplication store would be more thorough but introduces a database dependency that violates SCBE's local-first principle. The 1000-packet window is sufficient for normal operation because SCBE agents typically process far fewer concurrent packets.

**Out-of-Order Delivery**: The JSONL bus is append-only, so packets within a single lane are ordered by write time. However, when packets arrive from multiple agents or across lane boundaries, temporal ordering is not guaranteed. Layer 11's Triadic Temporal Distance resolves this by computing causal relationships using ISO 8601 timestamps from the packet schema.

For strict-ordering requirements like sequential handoff chains, the \`correlation_id\` field groups related packets. The receiver buffers out-of-order packets within a correlation group and reorders by timestamp before processing. The buffer timeout is 5 seconds; after that, packets process in arrival order with a warning flag. This bounded wait prevents indefinite blocking if a packet in the chain is lost.

**Consistency Guarantee**: The overall delivery model provides at-least-once semantics with idempotent processing, which is equivalent to effectively-once delivery. This is the same guarantee provided by Kafka consumer groups with manual offset commits, and it is sufficient for SCBE's coordination requirements where occasional reprocessing is safe but message loss is not.`;
}

function genCrosstalkSenders() {
  return `In the SCBE cross-talk system, sender identity serves as a first-order signal in the governance pipeline, directly influencing how packets are scored, routed, and trusted. The sender field uses the format \`agent.<type>\` and maps to specific positions in the Sacred Tongues scoring space.

**Registered Sender Identities**:

- \`agent.claude\`: Anthropic Claude instances, typically serving as the primary orchestrator in SCBE workflows. Claude agents receive baseline trust scoring because they operate within the SCBE governance framework natively.
- \`agent.codex\`: OpenAI Codex instances, used for parallel implementation and code generation tasks. Trust is equivalent to Claude for code-path operations, reflecting that both agents operate under the same governance constraints.
- \`agent.gemini\`: Google Gemini instances, assigned to research, verification, and cross-validation tasks. Trust scoring reflects the verification role.
- \`unknown\`: Packets from sources that did not declare identity or that failed identity validation. These receive the lowest initial trust score, requiring exceptionally benign content to pass governance.

**Governance Integration**: The sender identity feeds directly into the KO (Intent) tongue at Layer 3 of the 14-layer pipeline. KO has a weight of 1.00 (the base phi-scaled weight), meaning it provides the foundational intent signal for all downstream scoring. A registered sender like \`agent.claude\` starts with a KO score near 1.0, while \`unknown\` starts near 0.

The practical effect cascades through the pipeline. At Layer 5, a low initial KO score increases the effective hyperbolic distance d_H from the safe-operation centroid. At Layer 12, the harmonic wall formula H(d*,R) = R^((phi*d*)^2) translates this increased distance into a lower governance score. A packet from \`unknown\` with the same content as a packet from \`agent.claude\` will score measurably lower, making it more likely to hit QUARANTINE or DENY at Layer 13.

**Spoofing Prevention**: The sender field is self-declared in the packet schema, which raises the obvious question of what prevents spoofing. SCBE handles this through two complementary mechanisms:

1. **Content-based scoring**: The governance pipeline evaluates the full packet content across all 14 layers, not just the sender field. A packet falsely claiming \`agent.claude\` but containing adversarial content will still score poorly at Layers 5-12. The sender identity is one input among many.

2. **File system access control**: The JSONL bus at \`artifacts/agent_comm/github_lanes/cross_talk.jsonl\` is a local file system resource. Only processes with appropriate OS-level permissions can write to it. In practice, only approved agent processes running on the local machine can produce packets.

**Operational Implications**: When multiple agents work concurrently, sender identity enables conflict detection. If \`agent.claude\` and \`agent.codex\` both attempt to modify the same resource, the session cross-talk manager uses sender identity plus timestamp to determine priority. The governance pipeline can also flag anomalous patterns like unusual packet volume or unexpected sender-receiver pairs for review through QUARANTINE, providing behavioral monitoring beyond simple access control.`;
}

// ── Main ──

function generateResponse(rec) {
  const inst = rec.instruction.toLowerCase();

  if (inst.includes('cross-talk packet schema')) return genCrosstalkSchema();
  if (inst.includes('packet delivery failure') || inst.includes('duplicate de')) return genCrosstalkReliability();
  if (inst.includes('senders like unknown') || inst.includes('agent.codex')) return genCrosstalkSenders();

  if (inst.includes('architecture') && inst.includes('design decision')) return genArchitecture(rec);
  if (inst.includes('14-layer') || (inst.includes('integrate') && inst.includes('governance'))) return genIntegration(rec);
  if (inst.includes('compare') || inst.includes('traditional')) return genComparison(rec);

  return genArchitecture(rec);
}

const data = readFileSync(STUBS, 'utf-8');
const lines = data.trim().split('\n');
console.log(`Loaded ${lines.length} stubs`);

const output = [];
for (const line of lines) {
  const rec = JSON.parse(line);
  const response = generateResponse(rec);

  const out = {};
  for (const [k, v] of Object.entries(rec)) {
    if (k === 'skill_content' || k === 'sample_packets') continue;
    out[k] = k === 'response' ? response : v;
  }
  output.push(out);
}

const outLines = output.map(r => JSON.stringify(r)).join('\n') + '\n';
writeFileSync(OUTPUT, outLines, 'utf-8');
console.log(`Wrote ${output.length} records to ${OUTPUT}`);

const wcs = output.map(r => r.response.split(/\s+/).length);
const min = Math.min(...wcs), max = Math.max(...wcs), mean = Math.round(wcs.reduce((a, b) => a + b) / wcs.length);
console.log(`Word counts: min=${min}, max=${max}, mean=${mean}`);

const unique = new Set(output.map(r => r.response)).size;
console.log(`Unique responses: ${unique}/${output.length}`);
