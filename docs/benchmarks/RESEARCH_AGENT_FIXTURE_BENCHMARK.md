# Research Agent Fixture Benchmark

Status: executable local BrowseComp/GAIA-style fixture lane, not a public
BrowseComp or GAIA score.

This lane measures whether an agent can execute a small evidence workflow:
search a local source pack, cite the required sources, format the answer, and
emit receipt hashes. It is deliberately stricter than "answer the question" so
plan-only or guess-only behavior fails.

## Command

```bash
python scripts/benchmark/research_agent_fixture_benchmark.py
```

Artifacts:

- `artifacts/benchmarks/research_agent_fixtures/latest_report.json`
- `artifacts/benchmarks/research_agent_fixtures/LATEST.md`

## Latest Expected Result

```text
decision=PASS
baseline=0/3
scbe=3/3
```

## Task Styles

- BrowseComp-style: short exact answer hidden behind split source clues.
- GAIA-style table lookup: structured row selection plus formatting rule.
- GAIA-style image-description join: relation extraction plus label-key lookup.

## Proof / Goal Split

- Proof layer: source pack, retrieval trace, answer, citations, checks, and
  receipt hashes.
- Goal layer: general BrowseComp/GAIA-capable research agent with robust
  multi-hop evidence execution.
- Boundary: local fixture proof does not imply a public benchmark score.

## Patent Provenance Boundary

The benchmark report links to local patent/workbench evidence as implementation
provenance only. It does not assert patentability, validity, or legal
sufficiency.

Linked local references:

- `docs/PATENT_DETAILED_DESCRIPTION.md`
- `docs/specs/EVALUATION_CONTRACT_v1.md`
- `docs/benchmarks/HARD_AGENTIC_BENCHMARK_PRETEST.md`

## Claim Boundary

Allowed:

- SCBE has local BrowseComp/GAIA-style executable research fixtures.
- The current evidence lane scores `3/3` against an answer-only baseline of
  `0/3`.
- The lane emits citations, evidence traces, checks, and receipt hashes.

Not allowed:

- Public BrowseComp score.
- Public GAIA score.
- Claim that local fixtures represent the full benchmark distribution.
