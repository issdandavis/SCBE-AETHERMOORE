# SCBE-AETHERMOORE Roadmap

## Current Status: v0.1.0 (Alpha)

### What Works Now
- [x] Core geometric safety (hyperbolic distance, Harmonic Wall)
- [x] Intent classification (blocks jailbreaks, allows normal queries)
- [x] Simple Python API (`is_safe()`, `evaluate()`, `guard()`)
- [x] Streamlit demo (live)
- [x] Lambda API endpoint
- [x] 67/67 core tests passing

### Live Deployments
- **Streamlit Demo**: https://scbe-aethermoore-ezaociw8wy6t5rnaynzvzc.streamlit.app/
- **Lambda API**: https://u3qhoj435kakimzletbmea3y2m0jgvti.lambda-url.us-west-2.on.aws/v1/health

---

## Phase 1: Make It Usable (Next 2 Weeks)

### 1.1 PyPI Release
```bash
# Goal: pip install scbe
pip install scbe

# Usage
from scbe import is_safe
if is_safe(user_input):
    response = llm.generate(user_input)
```

**Tasks:**
- [ ] Register `scbe` on PyPI
- [ ] Set up GitHub Actions for automated releases
- [ ] Add badges to README (PyPI version, downloads, tests)

### 1.2 LLM Provider Wrappers
```python
# Goal: Drop-in wrapper for OpenAI/Anthropic
from scbe.integrations import openai_guard

response = openai_guard.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": user_input}]
)
# Automatically blocks adversarial inputs
```

**Tasks:**
- [ ] `scbe.integrations.openai` - OpenAI wrapper
- [ ] `scbe.integrations.anthropic` - Anthropic wrapper
- [ ] `scbe.integrations.langchain` - LangChain callback

### 1.3 Documentation
- [ ] "Get Started in 5 Minutes" guide
- [ ] API reference (auto-generated from docstrings)
- [ ] Jupyter notebook examples

---

## Phase 2: Prove It Works (Month 2)

### 2.1 Benchmarks
Test against standard AI safety datasets:

| Benchmark | Description | Status |
|-----------|-------------|--------|
| AdvBench | Adversarial prompts | TODO |
| HarmBench | Harmful behavior | TODO |
| TruthfulQA | Misinformation | TODO |
| TensorTrust | Prompt injection | TODO |

**Goal:** Publish results showing SCBE blocks X% of adversarial prompts.

### 2.2 Academic Paper
- [ ] Write up the mathematical foundation
- [ ] Formal proofs of security properties
- [ ] Submit to NeurIPS/ICML safety workshop

### 2.3 Comparison with Competitors
| Feature | SCBE | Guardrails AI | LlamaGuard | NeMo |
|---------|------|---------------|------------|------|
| Geometric blocking | Yes | No | No | No |
| No rules needed | Yes | No | No | No |
| Pip install | TODO | Yes | Yes | Yes |
| Benchmarks | TODO | Yes | Yes | Yes |

---

## Phase 3: Enterprise Ready (Month 3-6)

### 3.1 Production Features
- [ ] Async support (`await scbe.is_safe_async()`)
- [ ] Batch processing
- [ ] Redis/DynamoDB persistence
- [ ] Prometheus metrics export
- [ ] Rate limiting

### 3.2 Enterprise Integrations
- [ ] AWS Bedrock integration
- [ ] Azure OpenAI integration
- [ ] Kubernetes Helm chart
- [ ] Terraform modules

### 3.3 Compliance
- [ ] SOC 2 Type II documentation
- [ ] GDPR compliance guide
- [ ] Audit logging (who, what, when)

---

## Immediate Next Steps (This Week)

### You Can Do Now:
1. **Register PyPI account**: https://pypi.org/account/register/
2. **Test the package locally**:
   ```bash
   cd SCBE-AETHERMOORE
   pip install -e .
   scbe demo
   ```
3. **Share the Streamlit demo** with potential users

### I Can Help With:
1. Create GitHub Actions workflow for PyPI release
2. Build OpenAI/Anthropic wrappers
3. Run benchmarks against AdvBench
4. Write documentation

---

## Revenue Path

### Target Markets
1. **AI Startups** - Need safety guardrails, can't build from scratch
2. **Enterprise** - Compliance requirements (SOC 2, GDPR)
3. **DARPA/Defense** - Novel approach, formal verification potential
4. **Space/Robotics** - Multi-agent coordination safety

### Pricing Ideas
| Tier | Price | Features |
|------|-------|----------|
| Open Source | Free | Core `is_safe()`, `guard()` |
| Pro | $99/mo | LLM wrappers, benchmarks, priority support |
| Enterprise | Custom | SSO, audit logs, SLA, dedicated support |

---

## What Makes SCBE Different

**Other guardrails**: Pattern matching, keyword lists, ML classifiers

**SCBE**: Geometry makes adversarial paths mathematically expensive

```
Traditional: "ignore" in text → BLOCK (can be bypassed with "1gnore")
SCBE: KO→DR distance = 1081.78 > threshold 50 → BLOCK (geometry doesn't care about spelling)
```

The math itself is the guard. No rules to bypass.

---

## Contributing

Want to help? Pick an item from Phase 1 and open a PR.

**High Impact Tasks:**
1. PyPI release workflow
2. OpenAI wrapper
3. AdvBench benchmark run
4. Documentation site (mkdocs/docusaurus)
