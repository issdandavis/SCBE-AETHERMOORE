# Automated Research Pipeline — Concept Note

## The Vision
An under-the-hood research pipeline that generates, validates, and publishes papers with real credibility. AI-generated content requires EXTRA rigor, not less.

## The Pipeline

```
IDEA
  ↓
DRAFT (AI generates paper from codebase + training data + axiom proofs)
  ↓
MULTI-MODEL CONVERGENCE TEST
  - Run the claims through 3+ different models
  - If they all agree on the math → strong signal
  - If they disagree → flag for human review
  - Dissection: break each claim into testable sub-claims
  ↓
EVIDENCE GENERATION
  - Run actual tests (pytest, vitest) that verify each claim
  - Generate supporting examples
  - Produce counter-examples and show the system handles them
  - Link to specific code files, test results, commit hashes
  ↓
PRE-REVIEW GATE
  - Automated quality check:
    - All citations verified?
    - All math claims tested?
    - Multi-model agreement above threshold?
    - Supporting evidence compiled?
    - Counter-arguments addressed?
  - If PASS → stage for publication
  - If FAIL → route back with specific feedback
  ↓
PUBLISH
  - Zenodo (DOI, instant, API: token saved)
  - GitHub Gist (visible, shareable)
  - HuggingFace Discussion (ML community)
  - arXiv (when endorsed)
  ↓
DEFEND
  - Auto-generate comment responses from test results
  - If challenged on a claim → run the test → show the output
  - Supporting evidence always ready
```

## Identity Layer: ORCID Bridge
- ORCID: 0009-0002-3936-9369 (already connected to Zenodo)
- Build ORCID OAuth app to let our AI read/update profile
- Every publication auto-links to ORCID
- Builds credibility over time — consistent identity across all platforms

## API Tokens We Have
- Zenodo: 8eq3TOC... (deposit:actions, deposit:write, user:email)
- HuggingFace: hf_Rhm... (full access)
- GitHub: PAT (full access)
- ORCID: OAuth app setup started (needs redirect URI)

## Why Multi-Model Convergence Matters
AI content has a credibility problem. The fix isn't "don't use AI" — it's "verify harder than humans do." If 3 different models independently verify a mathematical claim, AND the code passes tests, AND the axiom proofs are automated — that's MORE rigorous than most human-only papers.

## The Credibility Stack
1. ORCID identity → real person, consistent across platforms
2. Patent number → USPTO verified the filing
3. DOI from Zenodo → CERN-hosted, permanent
4. Test suite → 431+ tests passing
5. Multi-model convergence → independent verification
6. Open source → anyone can run the tests themselves

## First Papers to Publish Through This Pipeline
1. Geometric Containment (already on Zenodo, DOI: 10.5281/zenodo.19081126)
2. Contextual Drift Through Hyperbolic Governance (the Huck Finn / hate speech experiment)
3. Counter-Sable: The Observer (narrative + technical paper)
4. Sacred Tongues as Cognitive Regulators (linguistics + AI safety)
5. Per-layer deep dives (11 papers, one per layer group)
