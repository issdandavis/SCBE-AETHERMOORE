# Product Launch Readiness Checklist
## SCBE AI Security Training Vault ($29)
### Date: 2026-03-28

---

## The Product

**SCBE AI Security Training Vault** -- a downloadable package for AI/ML practitioners who want to fine-tune models for AI safety and security tasks.

### What the buyer gets:
- 478+ supervised fine-tuning (SFT) pairs covering AI safety, governance, adversarial detection
- Semantic projector weights (pre-trained on SCBE's 14-layer pipeline)
- Google Colab QLoRA fine-tuning notebook (ready to run on free T4 GPU)
- Benchmark suite (compare your fine-tuned model against baselines)
- Sacred Tongues tokenizer seed data (6 languages, 256 tokens each)
- Documentation: architecture overview, data format specs, training recipes

### What the buyer can do with it:
- Fine-tune any open LLM (Llama, Mistral, Qwen, etc.) for AI safety tasks
- Build AI guardrails using real training data (not synthetic slop)
- Benchmark their models against SCBE's F1=0.813 adversarial detection score
- Learn the hyperbolic geometry approach to AI safety
- Use the data commercially (MIT-licensed)

### Price: $29 one-time purchase
### Delivery: Instant digital download (ZIP file via Gumroad)

---

## Pre-Launch Checklist

### Product Packaging
- [ ] Create ZIP archive with all training data
  - [ ] Include `training-data/sft/` directory (all JSONL files)
  - [ ] Include `training-data/merged_sft.jsonl` (master dataset)
  - [ ] Include `training-data/schemas/` (data format documentation)
  - [ ] Include `training-data/metadata.json`
  - [ ] Include semantic projector weights from `artifacts/`
  - [ ] Include benchmark scripts from `scripts/benchmark/`
  - [ ] Include Colab notebook `scripts/train_lora_colab.ipynb`
- [ ] Add README.md to ZIP root with quickstart instructions
- [ ] Add LICENSE file (MIT) to ZIP root
- [ ] Add CHANGELOG.md showing data provenance
- [ ] Test: unzip on clean machine, verify all files present
- [ ] Test: run Colab notebook end-to-end on free T4 GPU
- [ ] Verify ZIP size is under 500MB (Gumroad limit for free plan)

### Gumroad Setup
- [ ] Create Gumroad account (or verify existing)
- [ ] Create new product: "SCBE AI Security Training Vault"
- [ ] Upload ZIP file
- [ ] Set price: $29 USD
- [ ] Write product description (see template below)
- [ ] Upload cover image (use SCBE logo or generate one)
- [ ] Add product tags: AI safety, machine learning, fine-tuning, SFT, guardrails
- [ ] Set up "Thank You" page with:
  - [ ] Download link
  - [ ] Quickstart guide (first 3 steps)
  - [ ] Link to GitHub repo for updates
  - [ ] Link to Discord/community for support
- [ ] Test purchase flow (use Gumroad test mode)
- [ ] Verify download works after test purchase
- [ ] Enable Gumroad analytics

### Website Integration
- [ ] Add "Buy Training Vault - $29" button to aethermoore.com homepage
- [ ] Add product page at aethermoore.com/training-vault
- [ ] Update GitHub README.md with purchase link
- [ ] Update HuggingFace model cards with purchase link
- [ ] Add Gumroad embed widget (or direct link)
- [ ] Test purchase flow from website

### Content Preparation
- [ ] Write Dev.to article: "478 SFT Pairs for AI Safety Fine-Tuning"
- [ ] Write GitHub Discussion announcement
- [ ] Write HuggingFace community post
- [ ] Draft X/Twitter thread (5-7 tweets):
  - Tweet 1: Problem (AI safety training data is scarce)
  - Tweet 2: What we built (14-layer pipeline, 6134 tests)
  - Tweet 3: What's in the vault (478 SFT pairs, projector weights, Colab notebook)
  - Tweet 4: Benchmark results (F1=0.813)
  - Tweet 5: Price and link ($29, Gumroad link)
- [ ] Draft LinkedIn post (professional angle: patent pending, benchmarked)
- [ ] Prepare HuggingFace model card update
- [ ] Create a 60-second demo video (screen recording of Colab notebook)

---

## Launch Day Checklist

### Morning (before announcement)
- [ ] Final check: Gumroad product is live and purchasable
- [ ] Final check: Website buy button works
- [ ] Final check: Download works after purchase
- [ ] Set up Stripe webhook notifications to phone

### Posts (stagger throughout the day)
- [ ] 9:00 AM PT: Post on X/Twitter (thread)
- [ ] 10:00 AM PT: Post on Dev.to
- [ ] 11:00 AM PT: Post on GitHub Discussions
- [ ] 12:00 PM PT: Post on HuggingFace
- [ ] 1:00 PM PT: Post on LinkedIn
- [ ] 2:00 PM PT: Share in relevant Discord servers / Slack communities
- [ ] 3:00 PM PT: Post on Reddit r/MachineLearning (if account has enough karma)

### Monitor
- [ ] Watch Gumroad dashboard for first sale
- [ ] Monitor X/Twitter for mentions and replies
- [ ] Check email for customer questions
- [ ] Respond to any GitHub issues within 2 hours

---

## Post-Launch Checklist (First 7 Days)

### Day 1
- [ ] Respond to every comment, reply, and question
- [ ] Track: page views, conversion rate, revenue
- [ ] Screenshot first sale for social proof
- [ ] Post "thank you" update if any sales happen

### Day 2-3
- [ ] Analyze traffic sources (where did buyers come from?)
- [ ] If zero sales: adjust pricing, improve description, post in more places
- [ ] If any sales: ask buyer for feedback via Gumroad follow-up email
- [ ] Cross-post to any platforms missed on launch day

### Day 4-7
- [ ] Collect feedback from buyers
- [ ] Fix any issues reported
- [ ] Write a "lessons learned" post about the launch
- [ ] Plan v2 of the product based on feedback
- [ ] Consider: should the price go up? down? bundle with other products?

### Week 2+
- [ ] Set up weekly content cadence (1 post per week mentioning the product)
- [ ] Explore affiliate partnerships (AI/ML bloggers, YouTubers)
- [ ] Plan next product (Outreach Sandbox? Enterprise SDK?)
- [ ] If revenue > $100: reinvest in Product Hunt launch ($0, just time)

---

## Product Description Template (for Gumroad)

```
SCBE AI Security Training Vault

Train AI models that actually understand safety.

Most AI safety datasets are synthetic, small, or generic.
This vault contains 478+ real supervised fine-tuning pairs
generated from a 14-layer hyperbolic security pipeline with
6,134+ passing tests and an F1 score of 0.813 on adversarial
benchmarks.

WHAT YOU GET:
- 478+ SFT pairs (AI safety, governance, adversarial detection)
- Pre-trained semantic projector weights
- Google Colab QLoRA notebook (runs on free T4 GPU)
- Benchmark suite (test your fine-tuned model)
- Sacred Tongues tokenizer seed data
- Full documentation and training recipes

WHO THIS IS FOR:
- ML engineers building AI guardrails
- Researchers studying AI safety
- Companies deploying LLMs who need safety fine-tuning
- Students learning AI security

WHAT MAKES THIS DIFFERENT:
- Built on patented hyperbolic geometry approach (USPTO #63/961,403)
- Not a GPT wrapper -- novel math, real code, real tests
- Benchmarked against DeBERTa and Llama Guard
- MIT licensed -- use commercially

$29 one-time purchase. Instant download.

Questions? Open an issue at github.com/issdandavis/SCBE-AETHERMOORE
```

---

## Pricing Rationale

| Consideration | Analysis |
|---------------|----------|
| Cost to create | 6+ months of development, $0 marginal cost per sale |
| Comparable products | AI training datasets on HuggingFace: free. Curated datasets on Gumroad: $19-$99 |
| Target buyer | ML engineers, researchers ($80K-$200K salary range) |
| Price sensitivity | $29 is an impulse buy for professionals. No approval needed. |
| Volume target | 10 sales/month = $290/month. 100 sales/month = $2,900/month |
| Future upsell | Training Vault buyers become leads for Outreach Sandbox ($29/month) and Enterprise SDK |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Zero sales | Reduce to $9 and A/B test. Add free preview (first 50 SFT pairs). |
| Refund requests | Gumroad handles refunds. Product is clearly described. Low risk. |
| Data quality complaints | Include benchmark results. Be transparent about limitations. |
| Someone pirates it | MIT licensed anyway. Free marketing if it spreads. |
| Competitor undercuts | Patent protects the method. Data is unique. |

---

## Success Metrics

| Metric | Week 1 Target | Month 1 Target | Month 3 Target |
|--------|---------------|----------------|----------------|
| Page views | 500 | 2,000 | 10,000 |
| Conversion rate | 1-2% | 2-3% | 3-5% |
| Sales | 5-10 | 20-60 | 100-500 |
| Revenue | $145-$290 | $580-$1,740 | $2,900-$14,500 |
| Customer feedback | 1-2 responses | 5-10 responses | Newsletter list |
