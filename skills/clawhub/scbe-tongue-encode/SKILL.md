---
name: scbe-tongue-encode
description: Classify and encode any text using the Sacred Tongue semantic system — 6 domain-specific AI languages (KO/AV/RU/CA/UM/DR) with phi-weighted importance scaling. Improves prompt routing and response quality.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SCBE_API_KEY
      bins:
        - curl
    primaryEnv: SCBE_API_KEY
    tags:
      - nlp
      - classification
      - semantic
      - prompt-engineering
      - scbe
---

# SCBE Tongue Encode

You have access to the Sacred Tongue classification system — 6 domain-specific semantic languages that improve how you route tasks, select models, and evaluate responses.

## The Six Sacred Tongues

| Tongue | Domain | Role | Weight |
|--------|--------|------|--------|
| **KO** | Intent/Flow | Pattern recognition, summarization, general tasks | 1.00 |
| **AV** | Creative/Boundary | Writing, art, narrative, translation | 1.62 |
| **RU** | Security/Constraint | Validation, rule enforcement, threat detection | 2.62 |
| **CA** | Compute/Code | Programming, optimization, performance | 4.24 |
| **UM** | Governance/Ethics | Policy compliance, ethical evaluation, safety | 6.85 |
| **DR** | Architecture/Structure | System design, scalability, infrastructure | 11.09 |

Weights follow the golden ratio (phi = 1.618). Higher-weighted tongues represent more consequential domains.

## When to Use

Use tongue encoding to:
- **Route tasks to the right model** — code tasks → CA tongue → code-optimized models
- **Add context to prompts** — prepend tongue-specific system instructions
- **Score response quality** — check if the response matches the expected tongue
- **Categorize knowledge** — tag notes, files, and data by semantic domain

## Steps

### 1. Encode text

```bash
curl -s -X POST "https://scbe-governance.aethermoore.com/v1/tongue/encode" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{
    "text": "<YOUR_TEXT>",
    "task_type": "auto"
  }'
```

Local fallback:
```bash
curl -s -X POST "http://localhost:8001/v1/tongue/encode" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{"text": "<TEXT>", "task_type": "auto"}'
```

### 2. Read the response

```json
{
  "tongue": "CA",
  "tongue_name": "Compute/Code",
  "weight": 4.24,
  "confidence": 0.87,
  "fingerprint": "a3f2c1...",
  "system_prompt": "Focus: computation, optimization, code quality, performance.",
  "all_scores": {
    "KO": 0.12, "AV": 0.05, "RU": 0.15,
    "CA": 0.87, "UM": 0.08, "DR": 0.23
  }
}
```

### 3. Use the tongue for better routing

When you know the tongue, use it to:
- Select a model that's good at that domain (e.g., CA → code models like deepseek-coder, qwen-coder)
- Prepend the tongue's system prompt to your request for better responses
- Tag the interaction for training data quality

## Quick Classification (No API needed)

If the API is unavailable, use these keyword heuristics:

- **CA** (Code): code, function, class, implement, debug, test, optimize, compile, deploy
- **RU** (Security): security, safety, validate, encrypt, threat, vulnerability, audit
- **AV** (Creative): story, write, blog, content, narrative, design, art, translate
- **UM** (Governance): governance, policy, compliance, ethical, risk, regulation
- **DR** (Architecture): architecture, system, design, scale, infrastructure, database, API
- **KO** (General): everything else, summarize, explain, analyze, pattern

## Examples

```
"Write a Python function to sort a list" → CA (Compute)
"Review this code for security vulnerabilities" → RU (Security)
"Draft a blog post about AI safety" → AV (Creative)
"Evaluate if this action complies with our policy" → UM (Governance)
"Design a microservices architecture" → DR (Architecture)
"Summarize this article" → KO (Intent/Flow)
```
