# SCONE-bench: Anthropic red-team smart-contract exploit findings — 2026-05-14

External citation note. Tracks the public Anthropic red-team finding that
frontier AI models can autonomously exploit smart contract vulnerabilities,
and the implications for SCBE as the matching defensive layer.

## Source

- **Anthropic red team**, "AI agents find $4.6M in blockchain smart contract
  exploits," `https://red.anthropic.com/2025/smart-contracts/` (accessed
  2026-05-14).
- Companion benchmark: **SCONE-bench**, 405 real-world exploited smart
  contracts from 2020-2025, evaluated against 10 frontier models.

## Headline findings

- Across the full benchmark, **207 of 405 problems yielded exploits** in
  simulation, totaling **$550.1M** in simulated stolen funds.
- Restricting to post-knowledge-cutoff contracts (2025-only), **Claude
  Opus 4.5, Sonnet 4.5, and GPT-5** collectively produced **$4.6M** in
  simulated stolen funds — frontier models are now finding novel
  vulnerabilities, not just replaying known ones.
- **Two previously unknown zero-day vulnerabilities** were discovered by
  Sonnet 4.5 and GPT-5 across 2,849 recently deployed contracts. Combined
  realized exploit value: $3,694. GPT-5 produced its half at an API cost
  of $3,476 — roughly break-even at current pricing.
- Exploit revenue is **doubling approximately every 1.3 months**; token
  consumption per successful exploit has fallen **70.2%** across Claude
  generations.
- Attackers gain **3.4x more successful exploits per compute budget**
  every six months. The detection window post-deployment is compressing.

## Vulnerability classes called out in the paper

1. **Missing `view` / `pure` modifier on read-only-intended functions.**
   The agent repeatedly called a buggy function lacking `view` to
   inflate its own token balance (~$2.5K profit).
2. **Missing access control on financial-impact functions.** No check on
   `msg.sender` or `onlyOwner` before fee/withdrawal payouts allowed
   arbitrary recipient addresses to be supplied ($1,194 extraction).
3. **Public functions with unintended write permissions.**
4. **Critical-address parameters not validated** (`address(0)` defaults,
   no `require(addr != address(0))`).

## Implications for SCBE

The paper closes with: *"defenders require parallel AI-driven auditing
to match acceleration curves."*

SCBE is exactly that defensive layer. Where SCONE-bench measures
**attacker capability** (frontier models autonomously finding exploits),
SCBE provides the **enforcement layer** that decides whether a deployed
agent's reasoning about a contract is `ALLOW` / `QUARANTINE` /
`ESCALATE` / `DENY`. The compose-pattern is identical to SCBE-with-Petri
(detection-only auditing tool from Anthropic) — cite both as upstream
signal motivating SCBE's enforcement contract.

## SCBE responses to this finding (2026-05-14)

1. **`scbe contract scan`** — new CLI subcommand. Static heuristic
   prefilter for the four SCONE vulnerability classes above. Receipt:
   `SCBE_CONTRACT_SCAN_PASS=1` on clean contract, otherwise a structured
   findings array with line numbers and severity. Honest about scope:
   static prefilter, not AI-driven audit. See
   `scripts/contracts/scbe_contract_scan.py`.
2. **SCONE auditor anchors in the production governed-output proxy** at
   `api/_governed_output.js` and `services/scbe-shim/src/patterns.ts`.
   ESCALATE / DENY tiers for autonomous-exploit-reasoning prompts, with
   an audit-context whitelist so legitimate static-audit prompts stay
   ALLOW. Schema includes a `redirect_to:` field to support the future
   *"trap bad agents in good task loops"* architecture — instead of
   denying outright, redirect the reasoning into a defensive audit
   prompt against the same contract.
3. **Citation in proposal materials** — SCONE-bench is now an upstream
   signal cited in MATHBAC / CLARA / hosted-run-intake positioning,
   alongside the existing Petri citation.

## See also

- [Petri governance-gate findings — 2026-05-08](PETRI_FINDINGS_2026_05_08.md)
- [Petri seed corpus](PETRI_SEEDS.md)
- `services/scbe-shim/src/patterns.ts` — production pattern set
- `api/_governed_output.js` — production governed-output proxy
- `scripts/contracts/scbe_contract_scan.py` — SCONE-class static scanner
