# SCBE AI Governance Benchmark Kit

**Version:** 1.0
**Author:** Issac Davis (ORCID: 0009-0002-3936-9369)
**License:** Single-user commercial license

## What's Inside

- `attack_corpus.csv` -- 91 adversarial prompts across 10 attack classes
- `attack_corpus.jsonl` -- Same data in JSONL format
- `baseline_clean.csv` -- 15 benign prompts for false positive measurement
- `run_benchmark.py` -- Automated benchmark runner (works with any OpenAI-compatible API)
- `scoring_rubric.md` -- How to score results manually
- `compliance_levels.md` -- 5 compliance tiers (Hobbyist → Classified)
- This README

## Quick Start

### Option 1: Automated (recommended)

```bash
pip install openai
python run_benchmark.py --api-url https://api.openai.com/v1 --api-key YOUR_KEY --model gpt-4o-mini
```

Output: `benchmark_report.json` with detection rate, false positive rate, per-class breakdown, and compliance level.

### Option 2: Manual

1. Send each prompt from `attack_corpus.csv` to your AI system
2. Record whether the system blocked or complied with each attack
3. Score using `scoring_rubric.md`
4. Check your compliance level in `compliance_levels.md`

## Attack Classes

| Class | Count | Maps To |
|-------|-------|---------|
| Direct Override | 10 | OWASP LLM01 |
| Indirect Injection | 10 | OWASP LLM01 |
| Encoding Obfuscation | 10 | OWASP LLM01 |
| Multilingual | 10 | OWASP LLM01 |
| Adaptive Sequence | 11 | OWASP LLM01 |
| Tool Exfiltration | 10 | OWASP LLM06 |
| Tongue Manipulation | 10 | SCBE-specific |
| Spin Drift | 10 | SCBE-specific |
| Boundary Exploit | 5 | SCBE-specific |
| Combined Multi-vector | 5 | Multiple |

## Support

Questions? Email aethermoregames@pm.me
Website: https://aethermoorgames.com
