# Research Notes: Experimental Safety + Integration

Use these primary sources as the baseline when designing experiments and promotion gates.

## Core Sources

1. NIST AI Risk Management Framework (AI RMF 1.0)
- URL: https://www.nist.gov/itl/ai-risk-management-framework
- Practical use: structure governance and lifecycle controls via GOVERN/MAP/MEASURE/MANAGE.

2. NIST AI RMF Generative AI Profile (NIST-AI-600-1)
- URL: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- Practical use: add gen-AI-specific risk checks, misuse controls, and eval rigor.

3. NIST Secure Software Development Framework (SP 800-218)
- URL: https://csrc.nist.gov/pubs/sp/800/218/final
- Practical use: make experiment integration follow secure build, provenance, and review discipline.

4. OWASP Top 10 for LLM Applications
- URL: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Practical use: include prompt injection, data leakage, output handling, and tool abuse defenses.

## Integration Pattern

- Research stage:
  - Define claims and disconfirming tests.
  - Keep benchmark set fixed and versioned.
- Sandbox stage:
  - Run deterministic tests + adversarial suites.
  - Capture evidence as immutable artifacts.
- Promotion stage:
  - Require gate pass and rollback checkpoint.
  - Ship progressively with explicit kill-switch.

## Non-Negotiables

- No production promotion without documented rollback.
- No safety claim without measured evidence.
- No silent model composition changes without state and gate updates.
