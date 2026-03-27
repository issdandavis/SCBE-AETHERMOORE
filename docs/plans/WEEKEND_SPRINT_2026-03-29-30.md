# Weekend Sprint — March 29-30, 2026

**Goal**: Improve AI training quality + move toward first real revenue

---

## SATURDAY: Training Quality

### Morning — Combine + Clean All Training Data
- [ ] Merge the 470-pair session file with the mega corpus (43K pairs)
- [ ] Deduplicate across all sources
- [ ] Score every pair by quality (length, specificity, tongue coverage)
- [ ] Remove low-quality pairs (too short, too generic, duplicated)
- [ ] Push cleaned mega corpus to HuggingFace

### Afternoon — Fine-Tune AetherBot on SCBE Data
- [ ] Use the cleaned training data to fine-tune on Colab (free T4 GPU)
- [ ] Base: Qwen 2.5 0.5B or 1.8B (small enough for Colab free tier)
- [ ] Method: QLoRA (rank 16, alpha 32) — same recipe as echo-taxlaw-adapter
- [ ] Train on combined_session + governance + architecture + tax + security
- [ ] Push fine-tuned model to HuggingFace as `issdandavis/aetherbot-v1`
- [ ] Convert to GGUF for Ollama
- [ ] Update AetherBot Modelfile to use fine-tuned model instead of base llama3.2

### Evening — Evaluate
- [ ] Run the 20 biblical null-space probes against the fine-tuned model
- [ ] Run the adversarial benchmark (184 tests)
- [ ] Compare: base llama3.2 vs fine-tuned aetherbot-v1
- [ ] Document the delta

---

## SUNDAY: Revenue Push

### Morning — Products That Can Sell Today
1. **Shopify store** (aethermore-works.myshopify.com)
   - [ ] List the AI Governance Toolkit ($29)
   - [ ] List the Formula Vault ($0.50 enterprise / free individual)
   - [ ] List training data pack ($9.99 — the 470 curated SFT pairs)
   - [ ] List the book "The Six Tongues Protocol" with Amazon link

2. **Gumroad** (already has 1 sale)
   - [ ] Update the SCBE Framework listing with new training data
   - [ ] Add AetherBot as a product (Ollama model, free/tip)

### Afternoon — Content That Drives Traffic
- [ ] Post 10 Bluesky posts (spread across the day)
- [ ] Create 1 YouTube video: "I Built an AI That Knows When It's Blind" (null-space experiment)
   - Script from the biblical null-space research
   - Kokoro TTS narration
   - Upload via post_to_youtube.py
- [ ] Post to GitHub Discussions (announcement about AetherBot)

### Evening — Outreach
- [ ] Follow up on CISA JCDC auto-reply (they responded)
- [ ] Email 3 more AI safety researchers with the benchmark results
- [ ] Post the null-space experiment results to LessWrong or Alignment Forum
- [ ] Check Stripe balance, Shopify orders, KDP royalties

---

## Revenue Targets

| Source | This Weekend Goal | How |
|--------|------------------|-----|
| Shopify | 1 sale ($29) | AI Governance Toolkit |
| Gumroad | 2 sales | Framework + training data |
| Amazon KDP | Track royalties | Book is live |
| Stripe | Check $97.74 balance | Existing |
| YouTube | Monetization check | 11 videos, need 1K subs + 4K hours |

## What Already Exists (Don't Rebuild)

- 470 SFT pairs (combined, on HuggingFace)
- 43K mega corpus (mega_ingest_sft.jsonl)
- AetherBot on Ollama (live, working)
- AetherBrowser shell + API (13 endpoints)
- Android APK (66.8MB debug)
- Sales page at 10.0 score
- YouTube channel with 11 videos, new titles + descriptions
- Bluesky account with 20+ posts
- Shopify store enabled
- Stripe with pending balance

## What NOT To Do This Weekend

- Don't redesign the architecture
- Don't add new theoretical research
- Don't start new systems
- Don't refactor existing code
- Focus: train better model + sell what exists
