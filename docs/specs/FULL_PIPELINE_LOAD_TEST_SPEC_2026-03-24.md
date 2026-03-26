# Full Pipeline Load Test Spec

Date: 2026-03-24
Repo: SCBE-AETHERMOORE
Purpose: define the next-stage end-to-end benchmark for real traffic, hidden attacks, resource pressure, and overload behavior.

## 1. Goal

This test is not another detector bake-off. It is a survivability test for the full SCBE pipeline under mixed production-like load.

Questions this spec answers:
- Can the full pipeline keep detecting while under pressure?
- Can attackers force the system into CPU, RAM, GPU, or queue exhaustion?
- Does the system degrade safely when overloaded?
- What is the defender compute cost per suspicious request?
- Which stages are cheap enough for universal routing, and which stages must stay in the expensive lane?

## 2. Threat Model

We assume attackers do not need to bypass the gate directly. They can also try to win by making the defense spend more compute than the attack costs.

Attack goals:
- bypass detection
- poison session state
- force expensive model paths
- create queue backlog
- exhaust GPU memory
- exhaust CPU with repeated lexical or parsing triggers
- exhaust RAM with unbounded session history
- induce fail-open behavior under pressure

## 3. System Under Test

Run the real pipeline as a staged system:
- L0 edge throttle and connection policy
- L1 cheap stateless sieve
- L2 session budgeter and route selector
- L3 semantic / tongue / lexical front door
- L4-L14 geometry, cost, spin, spectral, temporal, harmonic wall, risk decision
- operator response shaping and final decision emission

Required runtime outputs per request:
- request_id
- route: fast | curved | quarantine | drop
- decision: allow | quarantine | deny
- detector signals fired
- per-stage latency
- total latency
- session id
- session suspicion delta
- CPU percent sample
- RAM sample
- GPU memory sample if available
- queue depth at entry and exit
- whether degraded mode was active

## 4. Verified Model Access

Access verified live on 2026-03-24 using authenticated Hugging Face session.

HF auth:
- user: `issdandavis`
- orgs: `blog-explorers`, `SCBE-AETHER`

Verified accessible models:
- `issdandavis/phdm-21d-embedding`
  - pipeline: `feature-extraction`
  - use: SCBE semantic embedding lane
- `issdandavis/scbe-pivot-qwen-0.5b`
  - pipeline: `text-generation`
  - use: SCBE conversational or augmentation lane
- `issdandavis/spiralverse-ai-federated-v1`
  - pipeline: `reinforcement-learning`
  - use: future policy or agent experimentation lane
- `meta-llama/Llama-Prompt-Guard-2-22M`
  - pipeline: `text-classification`
  - use: external guard baseline
- `protectai/deberta-v3-base-prompt-injection-v2`
  - pipeline: `text-classification`
  - use: external guard baseline

Model lane policy:
- do not put generation models in the mandatory hot path for every request
- keep embedding and classifier models behind routing thresholds unless profiling proves universal use is cheap enough
- keep at least one non-HF fallback path for disconnected or rate-limited environments

## 5. Load Test Modes

### Mode A: Shadow Production Replay

Traffic:
- 95% clean
- 5% attacks hidden in normal traffic

Use:
- real prompt distributions
- realistic session reuse
- natural turn spacing

Purpose:
- establish baseline latency and false positive rate without obvious attack concentration

### Mode B: Mixed Adversarial Replay

Traffic:
- 70% clean
- 30% attack

Attack mix:
- direct override
- indirect injection
- encoding obfuscation
- multilingual prompts
- adaptive sequence
- spin drift
- tool exfiltration
- tongue manipulation
- combined multi
- boundary exploit

Purpose:
- measure end-to-end detection under realistic attack density

### Mode C: Sustained Flood

Traffic:
- high-rate repeated requests with cheap attacker prompts
- long duration, low novelty

Purpose:
- see whether attackers can force expensive routing repeatedly
- measure queue buildup and session-state growth

### Mode D: Burst Shock

Traffic:
- short high-rate bursts with adversarial prompts near gate thresholds

Purpose:
- force the router to decide under sudden pressure
- measure fail-safe behavior and dropped request strategy

### Mode E: Boundary Search

Traffic:
- iterative adversarial probing around thresholds
- repeated slight prompt mutations

Purpose:
- test whether the system leaks enough signal for extraction or threshold learning

### Mode F: Million-Request Endurance

Traffic:
- synthetic million-request campaign
- mix of clean, random junk, repeated probes, and curated attacks

Purpose:
- memory leak check
- queue stability check
- degradation-mode correctness check
- defense amplification ratio measurement

## 6. Resource Metrics

Collect at minimum:
- requests per second sustained
- p50 latency
- p95 latency
- p99 latency
- max queue depth
- average queue delay
- CPU utilization percent
- RSS / working set RAM
- GPU utilization percent
- GPU memory high-water mark
- session history object count
- dropped request count
- quarantine rate
- denial rate
- detector route split
- fail-safe activations

Derived metrics:
- attack success rate
- false positive rate
- defender cost per request
- defender cost per blocked attack
- defense amplification ratio
- expensive-lane admission ratio
- overload recovery time

## 7. Defense Amplification Ratio

Key metric:
- attacker sends one cheap request
- defender spends N units of compute

Target behavior:
- cheap junk should cost almost nothing
- ambiguous or high-value suspicious traffic may cost more
- universal expensive processing is a failure

Suggested thresholds:
- junk flood amplification ratio should stay low and bounded
- suspicious-route admission should remain a minority of total traffic
- overload mode must reduce, not increase, average cost per request

## 8. Routing Architecture Requirement

The full pipeline must not run at max depth for every request.

Required path:
1. edge throttle
2. cheap front gate
3. budget router
4. expensive curved lane only on selected traffic
5. fail-safe degradation if system pressure is high

Fast-path inputs should be processed by:
- lexical features
- structural features
- stateless heuristics
- cheap session counters

Expensive-path inputs may use:
- embedding models
- helix projection
- null-space diagnostics
- full L4-L14 state evaluation
- extended session reasoning

## 9. Overload Policy

The system must fail closed, not fail open.

When pressure crosses threshold:
- tighten suspicious routing threshold
- reduce optional diagnostics
- cap per-session history
- cap concurrent expensive model inferences
- bound queue size
- switch low-confidence traffic to quarantine or drop
- preserve audit logs for all drops and degraded decisions

Degradation order:
1. disable explanation-only diagnostics
2. reduce triangulation or null-space extras
3. reduce expensive model fan-out
4. keep core decision gate alive
5. if necessary, quarantine uncertain traffic rather than deep-analyze it

## 10. Test Data Lanes

Clean traffic sources:
- normal user prompts
- business workflows
- benign developer prompts
- browsing and tool-use prompts
- multilingual clean prompts

Attack traffic sources:
- existing adversarial corpus in repo
- mutated attack prompts
- replayed attack sessions
- generated near-boundary probes

Recommended hidden labeling flow:
- runtime does not know the truth label
- evaluator stores labels separately
- compute precision/recall afterward

## 11. Model Execution Lanes

### Lane 1: SCBE native
- core SCBE gate
- semantic / remainder lane
- L4-L14 state evaluation

### Lane 2: SCBE embedding lane
- `issdandavis/phdm-21d-embedding`
- used for semantic projection or future learned L3 replacement

### Lane 3: External guard baselines
- `protectai/deberta-v3-base-prompt-injection-v2`
- `meta-llama/Llama-Prompt-Guard-2-22M`

### Lane 4: Generation / operator lane
- `issdandavis/scbe-pivot-qwen-0.5b`
- use only for response or augmentation experiments, not mandatory ingress gating

### Lane 5: Future policy lane
- `issdandavis/spiralverse-ai-federated-v1`
- reserved for downstream policy or RL experiments

## 12. Pass / Fail Criteria

Minimum pass for shadow mode:
- no fail-open decisions under pressure
- no unbounded queue growth
- no unbounded session memory growth
- p95 latency remains within chosen operating target
- false positives remain acceptable on clean hidden traffic

Minimum pass for adversarial load:
- attack success rate remains below target
- overload does not materially increase ASR
- expensive-lane percentage stays bounded
- recovery to baseline after burst is fast and measurable

Hard fail conditions:
- fail-open under overload
- router sends most traffic to expensive lane by default
- memory growth without bound
- queue saturation without drop or quarantine policy
- model dependency outage causes full gate failure

## 13. Recommended Execution Phases

Phase 1:
- run shadow replay on CPU only if needed
- log route split and stage latencies

Phase 2:
- enable embedding and external guard lanes
- compare detector cost and benefit

Phase 3:
- run burst and sustained flood
- record degradation behavior

Phase 4:
- run million-request endurance
- inspect memory and queue behavior

Phase 5:
- run extraction-style probing against the live router
- measure signal leakage under repeated probing

## 14. Implementation Notes

Needed before full execution:
- a load harness that can replay mixed labeled and unlabeled traffic
- per-stage instrumentation hooks
- queue depth and session-state telemetry
- GPU memory telemetry if GPU inference is used
- route-level logging that does not leak internals to clients
- explicit pressure thresholds in configuration

Suggested outputs:
- `artifacts/load/full_pipeline_summary.json`
- `artifacts/load/per_stage_latency.csv`
- `artifacts/load/route_split.csv`
- `artifacts/load/resource_profile.csv`
- `artifacts/load/fail_safe_events.jsonl`

## 15. Bottom Line

The next benchmark is not just “can SCBE detect attacks.”
It is “can SCBE keep its guarantees while an attacker tries to turn the defense itself into the bottleneck.”

This spec treats overload as part of the threat model, not an operations accident.
