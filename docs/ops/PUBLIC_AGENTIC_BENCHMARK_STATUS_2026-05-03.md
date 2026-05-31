# Public Agentic Benchmark Status - 2026-05-03

## Current Result

The public GitHub Actions benchmark lane is live and has completed one remote scored Aider Polyglot smoke run.

- Workflow: `Public Agentic Benchmarks`
- Run: `25271257631`
- URL: `https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/25271257631`
- Artifact: `public-agentic-benchmarks-aider-polyglot-scored-small`
- Artifact URL: `https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/25271257631/artifacts/6768448249`
- Track: `aider-polyglot-scored-small`
- Model: `gpt-4o-mini`
- Edit format: `whole`
- Test cases sampled: `1`
- Aider commit: `3ec8ec5`

## Score

The first scored smoke completed successfully as infrastructure, but did not solve the sampled task.

```text
pass_rate_1: 0.0
pass_rate_2: 0.0
pass_num_1: 0
pass_num_2: 0
percent_cases_well_formed: 100.0
error_outputs: 2
num_malformed_responses: 0
syntax_errors: 0
indentation_errors: 0
test_timeouts: 0
total_tests: 225
```

The sampled task was Rust `simple-cipher`. The uploaded source still contained `todo!()` bodies after the run, and the tests failed `0 passed; 23 failed`.

## Interpretation

This is a real public benchmark plumbing milestone, not a capability win yet.

What is proven:

- GitHub Actions can provision Docker and execute the Aider Polyglot scorer remotely.
- The workflow can upload a score artifact.
- The lane can run without using local disk-heavy Docker.

What is not proven:

- GeoSeal or Sacred Tongues improves the public benchmark score.
- The selected model/edit-format can solve the sampled task.
- The one-case result generalizes to the 225-case suite.

## Fix Landed After Run

The first artifact omitted hidden Aider diagnostics such as `.aider.results.json` and `.aider.chat.history.md`. The workflow now copies those into a visible `diagnostics/` folder before upload so future runs expose model/API/edit failure details.

## Next Benchmark Step

Run another one-case scored variant after the diagnostics patch lands. The highest-value cheap comparison is:

```bash
gh workflow run public-agentic-benchmarks.yml --ref main -f track=aider-polyglot-scored-small -f num_tests=1 -f model=gpt-4o-mini -f edit_format=diff
```

If that still leaves the source unchanged, the next fix is provider/model invocation diagnostics. If it edits but fails tests, the next fix is a GeoSeal coding adapter or prompt wrapper, then a 3-case comparison against raw Aider.
