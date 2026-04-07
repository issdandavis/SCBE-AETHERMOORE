# App Store Security Products Research (March 2026)

**Document**: APP-STORE-SECURITY-2026-001
**Author**: Issac Daniel Davis
**Date**: 2026-03-27
**Purpose**: Competitive landscape analysis for SCBE-AETHERMOORE across app stores and marketplaces

---

## Executive Summary

The AI security market is projected to grow from $227-340M (2024-2025) to $4.83B by 2034 (CAGR 35-45%). Only 6% of organizations have advanced AI security strategies. The market is fragmented across five distribution surfaces: mobile app stores, npm/PyPI, HuggingFace, browser extensions, and IDE extensions. SCBE-AETHERMOORE has a unique position as the only product combining geometric (hyperbolic) cost scaling, post-quantum cryptography, and a 14-layer governance pipeline -- but it lacks the packaging, certifications, and UX polish that buyers expect.

---

## 1. Google Play Store -- AI Security Apps

### 1.1 Protectstar Firewall Security AI

| Field | Value |
|-------|-------|
| **Platform** | Google Play |
| **Price** | Free (premium $3.99/mo) |
| **Downloads** | 1M+ |
| **Rating** | 4.3/5 |
| **Category** | Tools / Security |

**What it does**:
- No-root firewall for Android
- Blocks trackers and spy servers using AI heuristics
- DNS privacy and connection logging
- Real-time traffic monitoring

**How it presents itself**:
- Clean Material Design UI with traffic visualizations
- "AI-powered" badge prominently displayed
- Before/after comparisons showing blocked trackers
- Trust badges: "Made in Germany", GDPR compliant

**What makes it successful**:
- Solves a concrete, visible problem (tracker blocking)
- No root required lowers barrier to entry
- Free tier drives adoption; premium converts power users
- Clear value proposition in screenshots

**SCBE comparison**:
- SCBE does deeper analysis (14-layer pipeline vs. pattern matching)
- SCBE lacks a consumer-facing mobile app entirely
- Protectstar wins on packaging and accessibility
- **Gap**: SCBE needs a simple "scan this prompt/traffic" mobile interface

**NOTE**: Protectstar's Firewall AI was temporarily suspended from Google Play in late 2025 due to policy compliance issues, then reinstated. This shows Google's increasing scrutiny of AI-labeled security apps.

### 1.2 AI Guard (AI Guard Protocol)

| Field | Value |
|-------|-------|
| **Platform** | Google Play |
| **Price** | Free |
| **Downloads** | 10K+ |
| **Rating** | 4.1/5 |
| **Category** | Tools |

**What it does**:
- AI-powered deepfake detection
- Authenticity verification for images and text
- Gamified rewards for "protecting the digital world"
- Community-driven threat reporting

**How it presents itself**:
- Gamification layer (earn rewards for scanning)
- "AI Security Companion" branding
- Social proof via community statistics

**What makes it successful**:
- Gamification drives engagement and retention
- Deepfake detection is a trending consumer concern
- Free with no upsell pressure

**SCBE comparison**:
- SCBE has more rigorous detection (geometric cost scaling vs. classifier)
- SCBE lacks gamification or consumer engagement hooks
- **Gap**: SCBE could add a "scan and score" gamification layer

### 1.3 Google Play's Own AI Security (Platform-Level)

Google blocked 1.75M malicious apps in 2025 using AI, running 10,000+ safety checks per app. In 2026, Google plans to expand AI-driven defenses and banned 80,000+ developer accounts.

**Implication for SCBE**: Rather than competing with Google's built-in security, SCBE should position as a **complementary layer** -- "Google catches malware; SCBE catches adversarial AI intent."

---

## 2. npm -- Security & Governance SDKs

### 2.1 LLM Guard (ProtectAI)

| Field | Value |
|-------|-------|
| **Platform** | PyPI (primary), npm wrapper available |
| **Price** | Open source (MIT) |
| **Downloads** | 2.5M+ (PyPI) |
| **GitHub Stars** | 4.5K+ |
| **Category** | AI Security Toolkit |

**What it does**:
- Input scanners: prompt injection, PII anonymization, toxicity detection, topic banning
- Output scanners: content moderation, bias detection, malicious URL detection, deanonymization
- Configurable pipeline (enable/disable individual scanners)
- API server mode for production deployment

**How it presents itself**:
- "The Security Toolkit for LLM Interactions"
- Clean documentation with quick-start guides
- Benchmark comparisons against alternatives
- ProtectAI corporate backing (VC-funded)

**What makes it successful**:
- Open source with enterprise support option
- Modular design -- use only what you need
- Strong documentation and examples
- ProtectAI brand credibility
- 2.5M downloads creates social proof

**SCBE comparison**:
- SCBE has deeper mathematical foundation (hyperbolic geometry vs. classifier ensemble)
- SCBE has PQC crypto that LLM Guard lacks entirely
- LLM Guard wins on developer experience (pip install, 3 lines of code, done)
- LLM Guard wins on documentation clarity
- **Gap**: SCBE needs a `scbe-guard` minimal package that works in 3 lines of code

### 2.2 Rebuff (ProtectAI)

| Field | Value |
|-------|-------|
| **Platform** | npm + PyPI |
| **Price** | Open source |
| **GitHub Stars** | 1K+ |
| **Category** | Prompt Injection Detection |

**What it does**:
- Multi-layer detection: heuristics, LLM-based, vector DB similarity, canary tokens
- Self-improving: stores attack embeddings for future detection
- REST API for integration

**What makes it successful**:
- Multi-layer approach mirrors enterprise defense-in-depth thinking
- Canary token concept is novel and easy to explain
- Open source builds trust

**SCBE comparison**:
- SCBE's 14-layer pipeline is more comprehensive than Rebuff's 4-layer approach
- SCBE has formal mathematical backing (Rebuff is heuristic-heavy)
- Rebuff is explicitly labeled "prototype" -- SCBE is more production-ready
- **Gap**: SCBE should add canary token support as an easy win

### 2.3 Lakera Guard

| Field | Value |
|-------|-------|
| **Platform** | REST API (cloud-hosted), Python SDK |
| **Price** | Free (10K requests/mo), Enterprise (custom pricing) |
| **Category** | AI Firewall / LLM Security |

**What it does**:
- Real-time prompt injection detection
- PII redaction
- Content moderation (toxic, harmful, inappropriate)
- Agent security (runtime visibility and control)

**How it presents itself**:
- "AI-Native Security Platform"
- Enterprise branding with SOC 2 Type II certification
- Customer logos (enterprise trust signals)
- One-line integration code examples

**What makes it successful**:
- Free tier with generous 10K requests
- Enterprise-grade with SOC 2 certification
- Cloud-hosted means zero infrastructure for customers
- Strong marketing and positioning

**SCBE comparison**:
- SCBE has mathematically provable cost scaling (Lakera uses ML classifiers)
- SCBE has PQC (Lakera does not)
- Lakera wins massively on ease of integration (REST API call vs. full pipeline)
- Lakera wins on enterprise trust signals (SOC 2, customer logos)
- **Gap**: SCBE needs a hosted API endpoint with a free tier

### 2.4 Socket.dev

| Field | Value |
|-------|-------|
| **Platform** | npm CLI wrapper, GitHub App |
| **Price** | Free (open source), Pro ($25/user/mo) |
| **Category** | Supply Chain Security |

**What it does**:
- Real-time malware blocking during npm install
- Typosquatting detection
- Dependency risk scoring
- GitHub PR integration

**SCBE comparison**:
- Different focus (supply chain vs. AI governance)
- Socket proves the "security as a wrapper" model works for developer adoption
- **Lesson**: SCBE could offer an `npx scbe-scan` CLI wrapper

### 2.5 Snyk

| Field | Value |
|-------|-------|
| **Platform** | npm, PyPI, IDE plugins, CI/CD |
| **Price** | Free (limited), Team ($25/dev/mo), Enterprise (custom) |
| **Downloads** | 10M+ (npm CLI) |
| **Category** | Developer Security Platform |

**What it does**:
- Vulnerability scanning for dependencies
- Container security
- Infrastructure as code scanning
- Code analysis

**SCBE comparison**:
- Snyk is the gold standard for developer-friendly security
- Their success comes from meeting developers where they are (IDE, CLI, CI/CD)
- **Lesson**: SCBE should have presence in all three: CLI, IDE extension, CI/CD action

---

## 3. HuggingFace Spaces -- AI Safety Tools

### 3.1 ProtectAI Prompt Injection Benchmark

| Field | Value |
|-------|-------|
| **Platform** | HuggingFace Spaces |
| **Price** | Free |
| **Category** | Benchmark / Evaluation |

**What it does**:
- Tests prompts against multiple detection providers
- Side-by-side comparison of detection methods
- Standardized benchmark format

**SCBE comparison**:
- SCBE already has a Red Team Sandbox Space (91/91 attacks blocked)
- **Gap**: SCBE should submit to the ProtectAI benchmark for third-party validation

### 3.2 Meta Prompt-Guard-86M

| Field | Value |
|-------|-------|
| **Platform** | HuggingFace Models |
| **Price** | Free (Llama license) |
| **Downloads** | 500K+ |
| **Category** | Prompt Injection Classifier |

**What it does**:
- 86M parameter classifier for prompt injection and jailbreak detection
- Multilingual support
- Binary classification: BENIGN / INJECTION / JAILBREAK

**SCBE comparison**:
- Meta has brand weight SCBE cannot match
- SCBE offers richer output (6D tongue coordinates, layer trace, cost multiplier) vs. binary classification
- **Gap**: SCBE should publish a model card comparing Prompt-Guard-86M results against SCBE pipeline

### 3.3 DeBERTa Prompt Injection Models (deepset / ProtectAI)

| Field | Value |
|-------|-------|
| **Platform** | HuggingFace Models |
| **Price** | Free |
| **Downloads** | 1M+ (combined variants) |
| **Accuracy** | 99.1% on holdout (deepset), 76.7% on adversarial (ProtectAI v2) |

**What it does**:
- Fine-tuned DeBERTa for binary prompt injection classification
- Multiple variants optimized for different use cases

**SCBE comparison**:
- SCBE benchmarked at Level 8 against DeBERTa (see MILITARY_GRADE_EVAL_SCALE.md)
- DeBERTa wins on direct override detection (trained specifically for it)
- SCBE wins on geometric attacks (tongue manipulation, spin drift, half-auth)
- **Gap**: SCBE should publish comparison benchmarks on HuggingFace as a dataset

### 3.4 GuardBench Leaderboard

| Field | Value |
|-------|-------|
| **Platform** | HuggingFace Spaces |
| **Category** | Benchmark Leaderboard |

**What it does**:
- Large-scale benchmark for guardrail models
- Standardized evaluation across multiple safety dimensions
- Public leaderboard for comparison

**SCBE comparison**:
- SCBE is not listed on GuardBench
- **Gap**: Submit SCBE to GuardBench for public credibility

---

## 4. Chrome Web Store -- Security Extensions

### 4.1 Privacy Badger (EFF)

| Field | Value |
|-------|-------|
| **Platform** | Chrome Web Store |
| **Price** | Free |
| **Users** | 3M+ |
| **Rating** | 4.5/5 |

**What it does**:
- Automatically blocks invisible trackers
- Learns which domains track you
- No configuration required

**What makes it successful**:
- EFF brand trust
- "Install and forget" simplicity
- Open source transparency

### 4.2 GPT Privacy / Caviard.ai

| Field | Value |
|-------|-------|
| **Platform** | Chrome Web Store |
| **Price** | Free (basic), Pro ($9.99/mo) |
| **Users** | 50K+ |
| **Category** | AI Privacy |

**What it does**:
- Automatic PII anonymization before sending to ChatGPT/Claude
- Swaps real data with placeholders
- Re-substitutes in responses

**SCBE comparison**:
- This is exactly the kind of consumer-facing product SCBE could build
- SCBE's tongue classification could detect sensitive data categories more precisely
- **Gap**: Build a "SCBE Privacy Shield" Chrome extension

### 4.3 ClearURLs

| Field | Value |
|-------|-------|
| **Platform** | Chrome Web Store |
| **Price** | Free |
| **Users** | 500K+ |

**What it does**:
- Removes tracking parameters from URLs
- Minimal, focused functionality

**Lesson**: Focused, single-purpose extensions outperform bloated all-in-one tools.

### 4.4 The AI Chrome Extension Market

- Market valued at $1.5B in 2023, projected $7.8B by 2031 (25% CAGR)
- Incogni's January 2026 research found widespread privacy concerns in AI extensions
- 550+ validated secrets leaked from extension publishers (OpenAI, Anthropic, HuggingFace tokens)
- Malicious AI extensions with 1.5M installs caught stealing source code in January 2026

**SCBE opportunity**: Position as "the security extension that protects you FROM other AI extensions"

---

## 5. VS Code Marketplace -- Security Extensions

### 5.1 Current Landscape (2026)

The VS Code Marketplace is facing a security crisis:
- Malicious AI extensions with 1.5M combined installs caught siphoning developer data to China (January 2026)
- 550+ validated secrets found from hundreds of publishers
- 4 security flaws found across extensions with 128M combined installs
- Supply chain attacks via recommended extensions in VS Code forks

### 5.2 Key Security Extensions

| Extension | Users | What It Does |
|-----------|-------|-------------|
| **Snyk Security** | 2M+ | Vulnerability scanning in code |
| **SonarLint** | 5M+ | Code quality and security rules |
| **GitLens** | 30M+ | Git history (security auditing) |
| **ESLint Security** | 15M+ | Security-focused lint rules |
| **Checkov** | 500K+ | Infrastructure-as-code scanning |

### 5.3 SCBE Opportunity

No VS Code extension currently offers:
- AI prompt governance while coding
- Hyperbolic cost visualization for AI interactions
- PQC-signed commit verification
- Sacred Tongue classification of code intent

**Gap**: A "SCBE Code Guardian" VS Code extension could:
1. Scan AI-assisted code for governance violations
2. Visualize the 14-layer pipeline decision for each AI interaction
3. Flag prompt injection attempts in AI-assisted coding
4. Sign code artifacts with PQC envelopes
5. Provide a "trust score" for AI-generated code

---

## 6. Enterprise Buyer Expectations

### 6.1 Security Product Demo Requirements

Enterprise buyers in 2026 expect:

| Requirement | Status for SCBE | Priority |
|-------------|----------------|----------|
| **Live demo environment** | 14 browser demos live | DONE |
| **API sandbox** | Not available | HIGH |
| **Time-to-value < 5 minutes** | npm install works but complex | HIGH |
| **Integration with existing stack** | Limited connectors | MEDIUM |
| **Customer references** | None | HIGH |
| **Pricing page** | Not available | HIGH |
| **Security questionnaire responses** | Not prepared | HIGH |
| **SOC 2 Type II report** | Not certified | CRITICAL |
| **Penetration test report** | Self-assessed only | HIGH |
| **SLA documentation** | Not available | MEDIUM |

### 6.2 Certifications & Badges That Matter

| Certification | Cost | Timeline | Impact | SCBE Priority |
|---------------|------|----------|--------|--------------|
| **SOC 2 Type II** | $20K-80K | 6-12 months | Gate for enterprise deals | CRITICAL (but expensive) |
| **ISO 27001** | $15K-50K | 6-12 months | International credibility | HIGH |
| **NIST AI RMF alignment** | Self-assessment (free) | 1-2 months | Federal credibility | HIGH (do now) |
| **OWASP LLM Top 10 coverage** | Self-assessment (free) | 1 month | Security community credibility | HIGH (do now) |
| **MITRE ATLAS mapping** | Self-assessment (free) | 1 month | Defense/intelligence credibility | HIGH (do now) |
| **FedRAMP 20x Low** | $50K-150K | 2 months (new accelerated path) | Federal marketplace access | MEDIUM (future) |
| **CISA JCDC membership** | Free (application) | 1-2 months | Government trust signal | HIGH (do now) |

**Pragmatic approach for SCBE**: Start with the free self-assessments (NIST AI RMF, OWASP, MITRE ATLAS) to build credibility documentation. These cost nothing and demonstrate awareness. Defer SOC 2 until revenue supports the $20K+ investment.

### 6.3 Red Team Report Format (What Buyers Trust)

Modern enterprise buyers expect red team reports that are:

**Structure**:
1. Executive Summary (1 page)
2. Scope and Methodology
3. Attack Narrative (story format, not just findings)
4. Findings Matrix (severity, exploitability, impact)
5. Evidence (screenshots, logs, reproduction steps)
6. Recommendations (prioritized, actionable)
7. Appendices (tools used, raw data)

**Key metrics buyers look for**:
- Detection rate by attack category
- Mean time to detect (MTTD)
- Mean time to respond (MTTR)
- False positive rate
- Evasion rate under adaptive attack
- Coverage against OWASP LLM Top 10
- Coverage against MITRE ATLAS techniques

**What SCBE has**:
- 91/91 attacks blocked in Red Team Sandbox
- 240+ attack scenarios
- Level 8 on MILITARY_GRADE_EVAL_SCALE
- Comparison vs. DeBERTa PromptGuard

**What SCBE needs**:
- Third-party validation (not self-assessed)
- Continuous testing results (not point-in-time snapshots)
- Integration with vulnerability management workflows
- CVSS-style severity scoring for AI-specific vulnerabilities
- Formal report document in standard pentest format

### 6.4 Test Suite Formats Security Auditors Expect

| Format | Purpose | Tool |
|--------|---------|------|
| **JUnit XML** | CI/CD integration | All major test frameworks |
| **SARIF** (Static Analysis Results Interchange Format) | GitHub/Azure DevOps integration | Standard for security findings |
| **CycloneDX SBOM** | Software Bill of Materials | Required by NSA AI Supply Chain guidance |
| **OWASP ZAP reports** | Web application security | Standard for web pentesting |
| **Nuclei templates** | Vulnerability scanning | Standard for automated scanning |
| **MITRE ATT&CK Navigator layers** | Attack coverage visualization | Standard for threat mapping |

**SCBE should output**: JUnit XML (already via vitest), SARIF (add), CycloneDX SBOM (add), and a custom SCBE governance report format.

---

## 7. Competitive Positioning Matrix

| Feature | SCBE | Lakera Guard | LLM Guard | Meta Prompt-Guard | DeBERTa PI |
|---------|------|-------------|-----------|-------------------|------------|
| **Detection approach** | Hyperbolic geometry | ML classifiers | Ensemble scanners | 86M classifier | Fine-tuned DeBERTa |
| **Mathematical proof** | Yes (H(d,R)=R^(d^2)) | No | No | No | No |
| **Post-quantum crypto** | ML-KEM-768, ML-DSA-65 | No | No | No | No |
| **Multi-dimensional analysis** | 6D (Sacred Tongues) | 1D (score) | Multi-scanner | 1D (score) | 1D (score) |
| **Open source** | Yes | No (hosted API) | Yes | Yes (Llama license) | Yes |
| **npm package** | Yes (v3.3.0) | No | No (PyPI only) | No | No |
| **PyPI package** | Yes (v3.3.0) | Python SDK | Yes | Via transformers | Via transformers |
| **Free tier** | Yes (self-hosted) | 10K req/mo | Unlimited | Unlimited | Unlimited |
| **SOC 2** | No | Yes | No | Meta's | No |
| **Enterprise support** | No | Yes | Yes (ProtectAI) | No | No |
| **Time to integrate** | 30+ minutes | 5 minutes | 10 minutes | 5 minutes | 5 minutes |
| **Documentation quality** | Technical/dense | Excellent | Good | Good | Minimal |
| **Live demo** | 14 demos | Web demo | No | No | No |
| **HF Space** | Red Team Sandbox | No | Benchmark | Model card | Model card |

---

## 8. Gaps and Action Items

### 8.1 Critical Gaps (Revenue Blocking)

| Gap | Action | Effort | Impact |
|-----|--------|--------|--------|
| No hosted API | Deploy SCBE API on Cloud Run with free tier | 1 week | Unlocks SaaS model |
| No 3-line quickstart | Create `scbe-guard` minimal npm package | 3 days | Developer adoption |
| No SOC 2 | Start with NIST AI RMF self-assessment (free) | 2 weeks | Enterprise credibility |
| No pricing page | Add pricing tiers to aethermoore.com | 1 day | Revenue conversion |
| No customer logos | Get 3 pilot users and document case studies | 1 month | Social proof |

### 8.2 Competitive Advantages to Amplify

| Advantage | How to Amplify |
|-----------|---------------|
| Only product with mathematical proof of cost scaling | Publish on arXiv, submit to GuardBench |
| Only product with PQC integration | Highlight in all marketing (NIST PQC standards are new) |
| 14-layer pipeline depth | Create comparison demo: SCBE vs. single-classifier |
| 14 live interactive demos | No competitor has this; promote heavily |
| Patent pending (USPTO #63/961,403) | Add patent badge to all listings |
| Sacred Tongues (unique 6D analysis) | This is the differentiator -- make it visual |

### 8.3 Platform-Specific Actions

| Platform | Action | Priority |
|----------|--------|----------|
| **Google Play** | Build "SCBE Scan" Android app (prompt checker) | MEDIUM |
| **npm** | Publish `scbe-guard` minimal package | HIGH |
| **PyPI** | Ensure `scbe-aethermoore` has quickstart examples | HIGH |
| **HuggingFace** | Submit to GuardBench, publish comparison datasets | HIGH |
| **Chrome Web Store** | Build "SCBE Privacy Shield" extension | MEDIUM |
| **VS Code Marketplace** | Build "SCBE Code Guardian" extension | MEDIUM |
| **GitHub Marketplace** | Publish SCBE as a GitHub Action for CI/CD | HIGH |

---

## 9. Revenue Model Benchmarks

| Product | Model | Price Range | SCBE Target |
|---------|-------|-------------|-------------|
| Lakera Guard | Freemium SaaS | Free / Custom enterprise | Match free tier, undercut enterprise |
| LLM Guard | Open source + support | Free / Enterprise support | Already open source |
| Snyk | Freemium + per-seat | Free / $25-$100/dev/mo | Target $15/dev/mo |
| Socket | Freemium + per-seat | Free / $25/user/mo | Target $10/user/mo |
| CrowdStrike Falcon AIDR | Enterprise license | $50K-500K/yr | Long-term target |
| Darktrace | Enterprise license | $100K-500K+/yr | Long-term target |

**SCBE near-term revenue model**:
1. **Free**: Self-hosted, npm/PyPI install, 14 demos
2. **Developer** ($15/mo): Hosted API, 100K requests, email support
3. **Team** ($49/mo): 1M requests, team dashboard, priority support
4. **Enterprise** (custom): Dedicated deployment, SLA, compliance reports

---

## 10. Key Takeaways

1. **The market is real and growing fast** -- $4.83B by 2034, 35-45% CAGR
2. **No competitor has SCBE's mathematical foundation** -- this is the moat
3. **Every successful product is easy to start** -- 3 lines of code or one browser install
4. **Certifications are table stakes for enterprise** -- start with free self-assessments
5. **Live demos are SCBE's secret weapon** -- no competitor has 14 interactive demos
6. **The Chrome extension market is $7.8B by 2031** -- security extensions are underserved
7. **Red team reports need to be continuous, not snapshots** -- build automated reporting
8. **Developer experience beats mathematical depth in adoption** -- simplify first, explain depth later
