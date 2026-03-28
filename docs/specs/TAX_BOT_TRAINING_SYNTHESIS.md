# Tax Bot Training Synthesis

**Date**: 2026-03-27
**Author**: SCBE-AETHERMOORE / Issac Daniel Davis
**Status**: Research complete, training plan ready
**Existing data**: `training-data/sft/tax_bot_v1.jsonl` (12 pairs), `training-data/sft/tax_bot_v2_synthesis.jsonl` (20 pairs)

---

## 1. Source Model & Dataset Analysis

### 1.1 niranjani23/fire-tax-advisor

| Attribute | Value |
|-----------|-------|
| Base model | Mistral (~3.9B params, 8-bit quantized) |
| License | MIT |
| Format | Full fine-tune (safetensors, F32/U8) |
| Downloads | 153 |
| Focus | FIRE (Financial Independence, Retire Early) + tax |
| Training data | **Undocumented** (empty README) |
| Training method | Unknown (likely SFT, Mistral-based) |

**What it does well**:
- Targets a specific financial subculture (FIRE community) that overlaps with our freelancer/creator audience
- Mistral base gives strong general reasoning
- MIT license means we can study outputs and use as a reference

**What it lacks**:
- Zero documentation on training data, methodology, or evaluation
- No indication of Schedule C, self-employment, or gig worker coverage
- No evidence of IRC citation accuracy
- Empty model card makes it unreliable as a training reference
- Likely trained on generic FIRE blog content, not actual tax law

**Relevance to us**: Low-to-medium. Useful only as a comparison baseline. We cannot extract training methodology.

---

### 1.2 Bmcbob76/echo-taxlaw-adapter

| Attribute | Value |
|-----------|-------|
| Base model | Qwen/Qwen2.5-7B-Instruct |
| Method | QLoRA (4-bit NF4 + LoRA rank 16, alpha 32) |
| Adapter size | ~38 MB |
| License | Apache 2.0 |
| Downloads | 53 |
| Focus | IRC sections 1-9999, Treasury Regulations, case law, tax planning |
| Training data | "Tax doctrine blocks" (proprietary, undisclosed source) |
| Epochs | 3, loss converged |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |

**What it does well**:
- Deep IRC coverage (sections 1-9999) -- the most comprehensive tax law adapter on HuggingFace
- QLoRA methodology is well-documented and reproducible
- Targets all major attention + MLP projections (7 modules)
- Part of a larger "Echo Omega Prime" suite with 2,600+ domain adapters
- Clean Apache 2.0 license
- Qwen 2.5 7B base is strong for instruction following

**What it lacks**:
- Training data is described as "doctrine blocks" but the actual dataset is not published
- Focused on formal tax law analysis, not practical tax filing advice
- Example prompt is about "partnership disguised sale under IRC Section 707(a)(2)(B)" -- corporate/partnership level, not individual freelancer
- No coverage of: Schedule C mechanics, freelancer deductions, crypto reporting, Cash App specifics, AI subscription categorization
- No evaluation metrics published

**Relevance to us**: High for IRC reference layer. We should consider using echo-taxlaw-adapter as a "legal backbone" and layering our freelancer-specific SFT on top.

**Training methodology to adopt**:
- QLoRA with rank 16, alpha 32 is a good recipe for domain adaptation
- Targeting all 7 projection layers (not just q/v) gives better coverage
- 3 epochs with convergence monitoring

---

### 1.3 shadicopty/Llama3.2-1b-taxadvisor

| Attribute | Value |
|-----------|-------|
| Base model | unsloth/llama-3.2-1b-instruct-bnb-4bit |
| Method | Unsloth + TRL (SFT) |
| Size | 1B parameters |
| Format | GGUF (2.48 GB F16) |
| License | Apache 2.0 |
| Downloads | 432 |
| Focus | Tax advisor (generic) |
| Training data | **Undocumented** |

**What it does well**:
- Extremely small (1B) -- can run on mobile/edge devices
- Unsloth training = 2x speed, practical for rapid iteration
- GGUF format ready for llama.cpp / Ollama deployment
- Apache 2.0 license

**What it lacks**:
- Empty model card: no training data, no topics, no evaluation
- 1B params severely limits complex tax reasoning (multi-step deduction calculations, interaction effects between Schedule C loss and W-2 income)
- No indication of what "tax advisor" means in practice
- Likely trained on generic internet tax Q&A

**Relevance to us**: Medium. The Unsloth + TRL pipeline is the exact toolchain we should use for rapid iteration on small models. The model itself is not useful as a knowledge source.

**Training methodology to adopt**:
- Unsloth for 2x training speed
- 1B model as a "canary" -- train on our data first at 1B to validate the dataset before scaling to 7B+
- GGUF export for local inference testing

---

### 1.4 Deepesh-001/Finance_taxlaws_casestudies

| Attribute | Value |
|-----------|-------|
| Type | Dataset |
| Size | 718 rows |
| Format | JSON, `[INST]...[/INST]` pairs |
| Field | Single `text` field (135-12,200 chars per entry) |
| Jurisdiction | **India** (Income Tax Act, 1961) |
| Downloads | 133 |
| Coverage | Sections 1-65+ of Indian ITA, capital gains, exemptions, business income, virtual digital assets |

**What it does well**:
- Structured Q&A format ready for SFT
- Covers capital gains computation, business income, depreciation, deductions
- Includes virtual digital asset taxation (relevant to crypto)
- Recent amendments through 2024

**What it lacks**:
- **Indian jurisdiction only** -- IRC, Schedule C, 1040, W-2, 1099 are completely absent
- No US-specific content whatsoever
- Section numbering and legal framework does not map to US tax code
- No freelancer, gig economy, or creator economy scenarios

**Relevance to us**: Low for direct use. Some conceptual patterns (capital gains computation structure, depreciation logic, business deduction categorization) could inform our data generation, but the content itself is India-only.

---

## 2. Additional Relevant Resources Discovered

### 2.1 SimpleJacksTax/tax-forms-federal
- **41.1K downloads** across state-specific repos
- Federal tax form document images (W-2, 1040, Schedule C, Schedule D, etc.)
- Useful for **document parsing** but not conversational tax advice
- Could feed a future OCR/document-understanding pipeline

### 2.2 hsarfraz/donut-irs-tax-docs-classifier
- Classifies 28 IRS document types including Schedule C, Schedule D, Schedule SE, Form 8949, W-2
- 74.4M parameter Donut model fine-tuned on 3,000+ documents
- **Use case**: Document intake classification for our tax bot -- "upload your forms, we identify them"

### 2.3 Gregorgramtoshi/us-legal-finance-sft-v0.1
- 150 Q&A pairs covering US Corporate Finance, Tax Law (IRC), SEC, AML/KYC
- CC0 license (public domain)
- Average judge score 8.77/10
- Relevant IRC content but focused on corporate/institutional, not individual

### 2.4 sujet-ai/Sujet-Finance-Instruct-177k
- 177,597 instruction entries from 18 source datasets
- 7 task types: sentiment, QA, QA with context, conversational QA, yes/no, topic classification, NER
- Apache 2.0 license
- **Good for general financial reasoning base**, but no tax-specific focus

### 2.5 williamjmorenor/personal-finance-chatml-dataset
- 17,580 bilingual (EN/ES) ChatML records
- Covers budgeting, debt management, savings, investment basics, retirement planning
- MIT license, SFT-ready format
- **Good for personal finance base layer**, closest to our audience's needs

### 2.6 Wiefdw/merged-tax-raft-mistral-7b
- Mistral 7B fine-tuned on Indonesian tax data (perpajakan Indonesia)
- Not relevant for US tax, but confirms RAFT (Retrieval Augmented Fine-Tuning) as a viable method

---

## 3. Gap Analysis

### What existing models/datasets cover:

| Topic | Coverage | Best Source |
|-------|----------|-------------|
| IRC sections (formal law) | Strong | echo-taxlaw-adapter |
| Indian tax law | Strong | Finance_taxlaws_casestudies |
| Corporate tax planning | Medium | us-legal-finance-sft-v0.1 |
| General financial QA | Strong | Sujet-Finance-Instruct-177k |
| Personal finance basics | Strong | personal-finance-chatml-dataset |
| Tax form classification | Strong | donut-irs-tax-docs-classifier |
| FIRE community tax | Weak | fire-tax-advisor (undocumented) |

### What NO existing model/dataset covers (our gaps):

| Gap | Why It Matters for Us |
|-----|----------------------|
| **Freelancer Schedule C filing** | Issac's primary tax form after W-2 |
| **AI subscription deductions** | $11,600+/year in AI services as business expenses |
| **Patent filing fee deductions** | USPTO #63/961,403 costs |
| **Business loss offsetting W-2 income** | Schedule C loss > $16K against ~$19.5K W-2 |
| **Crypto auto-buy from paycheck** | Cash App Bitcoin auto-buy cost basis tracking |
| **Stock trading with many small positions** | 236 transactions across 65 tickers |
| **Cash App as primary banking** | Filing, investing, direct deposit, all on Cash App |
| **Game purchases as R&D** | Everweave as patent-referenced research |
| **Mixed-use phone/internet** | 75% business allocation methodology |
| **YouTube channel as business income** | Creator economy tax implications |
| **Home office at family member's home** | Simplified method when you don't own/rent |
| **Hobby vs. business determination** | Proving profit intent with patent, npm, Shopify |
| **QBI deduction for sole proprietors** | IRC 199A 20% deduction interaction with losses |
| **Self-employment tax calculation** | 15.3% SE tax on Schedule C net profit |
| **Wash sale rules for frequent traders** | 236 stock transactions may trigger wash sales |

---

## 4. Our Unique Training Data Advantage

### 4.1 Real receipts, real situation

Every existing tax AI model trains on either:
- Synthetic/generated Q&A pairs
- Formal legal text (IRC sections, Treasury Regs)
- General financial knowledge scraped from the web

**We have something none of them have**: a complete, documented, real tax situation with:
- Exact dollar amounts for every subscription ($217.80 ChatGPT, $217.20 Claude, etc.)
- Real W-2 income history (26 biweekly checks, $655-$1,162 range)
- Real investment records (236 stock trades, 18 BTC trades, exact gains/losses)
- Real patent filing costs with USPTO confirmation numbers
- Real business legitimacy evidence (npm downloads, HuggingFace models, Shopify store)
- Real expense-to-income ratio that produces a net business loss

### 4.2 The "AI-native freelancer" archetype

No existing model covers the persona of someone who:
- Earns minimum wage at a day job
- Spends nearly all income on AI tools for a startup
- Has a patent pending on an AI system
- Lives with family to afford the AI subscriptions
- Uses Cash App as their entire financial infrastructure
- Has real published products but minimal revenue

This is an increasingly common archetype in 2025-2026 and will become more common as AI tools become primary business expenses for solo creators.

### 4.3 Documentation chain

Our tax prep document (`TAX_PREP_2026_RECEIPTS.md`) provides the full chain:
- Income sources with exact amounts
- Expense categories with monthly/annual breakdowns
- Investment records with broker CSVs
- Filing method (Cash App Taxes)
- Business legitimacy proof list

This is the kind of documentation a real tax preparer would need, and we can generate SFT pairs that teach the model to reason about real situations, not hypotheticals.

---

## 5. Combined Training Plan

### Phase 1: Broad Financial Foundation (Angular Position 0 degrees)

**Objective**: General financial literacy and tax vocabulary.

| Step | Data Source | Records | Method |
|------|------------|---------|--------|
| 1a | sujet-ai/Sujet-Finance-Instruct-177k | ~40K (QA subset) | SFT, filter for English QA only |
| 1b | williamjmorenor/personal-finance-chatml-dataset | ~8.7K (EN only) | SFT, ChatML format native |
| 1c | Gregorgramtoshi/us-legal-finance-sft-v0.1 | 150 | SFT, tax/legal subset |

**Base model**: Qwen2.5-7B-Instruct (matching echo-taxlaw-adapter's base for potential adapter stacking)

**Alternative small model**: Llama 3.2 1B via Unsloth (for rapid iteration canary runs)

**Training config**:
- QLoRA: rank 16, alpha 32, NF4 quantization
- Target: all attention + MLP projections (q, k, v, o, gate, up, down)
- Learning rate: 2e-4 with cosine schedule
- Batch size: 4, gradient accumulation: 8
- Epochs: 2 (foundation is broad, don't overfit)

### Phase 2: Tax Law Specialization (Angular Rotation 45 degrees)

**Objective**: Deep US tax code knowledge, IRC sections, form mechanics.

| Step | Data Source | Records | Method |
|------|------------|---------|--------|
| 2a | echo-taxlaw-adapter outputs | Generate 500+ IRC Q&A pairs using the adapter | Distillation into SFT pairs |
| 2b | IRS Publication 535 (Business Expenses) | Manual extraction | SFT pairs from key sections |
| 2c | IRS Publication 334 (Small Business Tax Guide) | Manual extraction | SFT pairs focused on Schedule C |
| 2d | IRS Publication 550 (Investment Income) | Manual extraction | SFT pairs for Schedule D/Form 8949 |
| 2e | tax_bot_v1.jsonl | 12 | Direct SFT (our existing pairs) |

**Training config**:
- Continue from Phase 1 checkpoint
- Epochs: 3 (deeper domain adaptation)
- Learning rate: 1e-4 (lower, preserving Phase 1 knowledge)

### Phase 3: Freelancer/Creator Focus (Angular Rotation 90 degrees)

**Objective**: The specific scenarios our user base encounters.

| Step | Data Source | Records | Method |
|------|------------|---------|--------|
| 3a | tax_bot_v2_synthesis.jsonl | 20 | Direct SFT |
| 3b | Synthetic generation from TAX_PREP_2026_RECEIPTS.md | 100-200 | LLM-generated, human-reviewed |
| 3c | FlyFin/TaxGPT-style Q&A patterns | 50-100 | Reconstruct common freelancer questions |
| 3d | Cash App tax reporting scenarios | 30-50 | Specific to Cash App as platform |
| 3e | AI subscription categorization guide | 20-30 | Every major AI service as business expense |

**Training config**:
- Continue from Phase 2 checkpoint
- Epochs: 5 (high-value, small dataset -- need more passes)
- Learning rate: 5e-5 (fine-grained adaptation)

### Phase 4: Edge Cases & Adversarial (Angular Rotation 135 degrees)

**Objective**: Handle tricky situations, avoid bad advice, know when to defer.

| Step | Data Source | Records | Method |
|------|------------|---------|--------|
| 4a | Hobby loss rule edge cases | 20-30 | SFT with "consult a professional" guardrails |
| 4b | Wash sale detection scenarios | 20-30 | Multi-step reasoning chains |
| 4c | Mixed-use expense allocation edge cases | 20-30 | Percentage calculations |
| 4d | "I should not answer this" scenarios | 30-50 | DPO: prefer "consult a CPA" over bad advice |
| 4e | State-specific quirks (WA has no income tax) | 10-20 | SFT for state awareness |

**Training config**:
- DPO for 4d (preferred vs. rejected responses)
- SFT for all others
- Epochs: 3
- Learning rate: 2e-5

### Phase 5: Evaluation & RLHF Polish (Angular Rotation 180 degrees)

**Objective**: Validate accuracy, add human preference alignment.

| Step | Method | Details |
|------|--------|---------|
| 5a | Holdout evaluation | 20% of all SFT pairs held out for evaluation |
| 5b | IRS accuracy check | Compare model outputs against IRS publications |
| 5c | CPA review | Have 1-2 responses reviewed by a real CPA |
| 5d | RLHF/DPO polish | Collect preference data from Issac's actual tax filing |

---

## 6. The Angular Search Concept

The training plan above uses "angular rotation" as a metaphor for progressive specialization:

```
0 degrees   -> Broad financial knowledge (wide beam, many topics)
45 degrees  -> Tax law specialization (narrowing beam, IRC focus)
90 degrees  -> Freelancer/creator specifics (tight beam, our niche)
135 degrees -> Edge cases & safety (adversarial probing)
180 degrees -> Evaluation & polish (reflection, alignment)
```

Each rotation narrows the search space while building on the previous layer's knowledge. This is analogous to SCBE's 14-layer pipeline: each layer adds specificity and governance on top of the previous layer's foundation.

In SCBE terms:
- Phase 1 = L1-L4 (context acquisition, realification, weighting)
- Phase 2 = L5-L7 (hyperbolic embedding in tax law space)
- Phase 3 = L8-L10 (multi-well domain specialization, spectral coherence)
- Phase 4 = L11-L12 (causal reasoning, harmonic wall against bad advice)
- Phase 5 = L13-L14 (risk decision, telemetry/audit)

---

## 7. Implementation Roadmap

### Week 1: Data Preparation
- [ ] Download and filter Sujet-Finance-Instruct-177k (QA subset, English only)
- [ ] Download personal-finance-chatml-dataset (English split)
- [ ] Download us-legal-finance-sft-v0.1
- [ ] Generate 100+ synthetic pairs from TAX_PREP_2026_RECEIPTS.md
- [ ] Convert all to unified JSONL format: `{instruction, response, source, category}`

### Week 2: Phase 1 Training (Canary)
- [ ] Train Llama 3.2 1B via Unsloth on Phase 1 data (canary run)
- [ ] Evaluate on holdout set
- [ ] Fix data quality issues found during canary

### Week 3: Phase 1-2 Training (Full)
- [ ] Train Qwen2.5-7B-Instruct via QLoRA on Phase 1 data
- [ ] Continue training on Phase 2 (tax law) data
- [ ] Evaluate IRC accuracy

### Week 4: Phase 3-4 Training
- [ ] Train on freelancer-specific data (Phase 3)
- [ ] Train on edge cases with DPO (Phase 4)
- [ ] Full evaluation pass

### Week 5: Deploy & Iterate
- [ ] Export to GGUF for local inference
- [ ] Deploy as SCBE MCP tool
- [ ] Collect feedback from Issac's actual 2026 tax filing
- [ ] Push model + dataset to HuggingFace: `issdandavis/scbe-tax-advisor-v1`

---

## 8. Dataset Inventory

| File | Records | Stage |
|------|---------|-------|
| `training-data/sft/tax_bot_v1.jsonl` | 12 | Complete |
| `training-data/sft/tax_bot_v2_synthesis.jsonl` | 20 | Complete |
| Phase 1 external data (filtered) | ~49K est. | To download |
| Phase 2 IRC pairs (generated) | 500+ est. | To generate |
| Phase 3 synthetic (from receipts) | 100-200 est. | To generate |
| Phase 4 edge cases + DPO | 100-160 est. | To generate |
| **Total estimated** | **~50K** | |

---

## 9. Licensing Summary

| Source | License | Commercial Use |
|--------|---------|----------------|
| echo-taxlaw-adapter | Apache 2.0 | Yes |
| Llama3.2-1b-taxadvisor | Apache 2.0 | Yes |
| fire-tax-advisor | MIT | Yes |
| Finance_taxlaws_casestudies | Unspecified | Caution |
| Sujet-Finance-Instruct-177k | Apache 2.0 | Yes |
| personal-finance-chatml-dataset | MIT | Yes |
| us-legal-finance-sft-v0.1 | CC0 | Yes (public domain) |
| Our own data (v1, v2) | Proprietary | Yes (we own it) |

---

## 10. Key Takeaways

1. **No existing model covers the freelancer-AI-creator tax niche**. This is a genuine gap in the open-source tax AI space.

2. **echo-taxlaw-adapter is the most useful existing resource** for IRC knowledge, but it targets corporate/partnership scenarios, not individual Schedule C filers.

3. **Our real tax data is our moat**. Synthetic data is everywhere; real, documented, receipted tax situations from an actual AI-native freelancer are nowhere.

4. **The angular rotation training plan** prevents catastrophic forgetting by building from broad to narrow, with each phase explicitly preserving prior knowledge through decreasing learning rates.

5. **1B canary model first, 7B production model second**. This saves compute and catches data quality issues early.

6. **DPO is essential for Phase 4** -- the model must learn to say "consult a CPA" rather than give wrong answers on edge cases.

7. **Target deployment is SCBE MCP tool + GGUF local inference**, not a hosted API. This keeps Issac's tax data private.
