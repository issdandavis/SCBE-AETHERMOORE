# SCBE-AETHERMOORE Business Expense Notes — Tax Year 2026

> **Agent Context**: This file is structured so any AI agent (Claude, Codex, Gemini, or a
> future fine-tuned HuggingFace tax model) can pick up where we left off. All decisions,
> rules, and open items are documented below. See also: `TAX_EXPENSE_TRACKER_2026.csv`
> in this same directory for the line-item spreadsheet.

---

## Status Checklist
- [ ] Download bank statements (all accounts used for SCBE expenses)
- [ ] Go through statements month by month
- [ ] Fill in `TAX_EXPENSE_TRACKER_2026.csv` with actual dates and amounts
- [ ] Get an EIN from IRS.gov (free, optional but recommended)
- [ ] File Schedule C with tax return (or amend 2025 return if applicable)
- [ ] Start generating revenue before end of 2027 (hobby rule — see below)

---

## Do I Need a Business License?

**No. A business license is NOT required to deduct business expenses on your taxes.**

Key facts:
- The IRS does not require a business license to file **Schedule C** (Sole Proprietorship)
- Schedule C is about **business activity**, not about state/local licensing
- Millions of sole proprietors file Schedule C without a formal license
- A business license is a *state/local* requirement that varies by city/county — it's separate from federal tax filing
- You **can** get one later if your city requires it, but it does not affect your ability to claim deductions now

### What the IRS DOES care about:
1. **Profit motive** — You intend to make money (patent filed, active development, npm package, API plans)
2. **Regular activity** — Consistent work on the project (git commit history proves this)
3. **Records** — Bank/credit card statements showing expenses (that's what the CSV tracker is for)

### Optional but smart:
- **EIN (Employer Identification Number)** — Free from IRS.gov, takes 5 minutes online. Keeps your SSN off business documents. Not required for Schedule C filing.

---

## Key Deductions to Capture

| Category | Estimated Total | Notes |
|----------|----------------|-------|
| AI Subscriptions (Claude, GPT, etc.) | ~$10,000+ | Core development tools for SCBE |
| USPTO Patent Filing | ~$200-400 | Provisional patent for SCBE systems |
| Hosting (Hetzner VPS) | TBD | Server infrastructure |
| Dev Tools & Services | TBD | GitHub, domains, APIs, packages |
| HuggingFace | TBD | Model hosting, training compute |
| Training Data / Compute | TBD | Any paid GPU/cloud training costs |

---

## Supporting Documentation
- **Git commit history**: Project active since early 2025, continuous development through 2026
- **Bank/credit card statements**: Primary receipt source — download and cross-reference with CSV
- **USPTO filing confirmation**: Provisional patent application for SCBE systems
- **GitHub repo**: Public proof of ongoing business activity (commits, PRs, releases)
- **npm package**: Published as `scbe-aethermoore` — public distribution of product

---

## Patent Notes
- Provisional patent filed for SCBE systems (hyperbolic geometry safety framework)
- Will need to amend/update before filing non-provisional — rapid development has added significant improvements since filing
- 12-month window from provisional filing date to file non-provisional with full updates
- Patent filing fees are deductible as business expenses

---

## Tax Strategy

### Schedule C Filing
- File **Schedule C** (Sole Proprietorship) with $0 revenue and all expenses as business losses
- Net loss offsets W-2 income, reducing taxable income
- At 22% bracket: ~$10K expenses = ~$2,200 additional refund
- Current refund without Schedule C: ~$840
- Projected refund with Schedule C: ~$3,000+

### IRS Hobby Rule (Important)
- The IRS expects a business to show **profit in 3 out of 5 years**
- Year 1 (2026) with all expenses and no revenue is **normal for a startup**
- Must start generating some revenue in the next 1-2 years to build the case
- Even small amounts count (npm downloads, consulting, API fees)
- The git history, patent, and business planning docs all support profit motive

### What Could Trigger an Audit
- Consistently claiming large losses with zero revenue for multiple years
- Expenses that look personal (keep business and personal separate)
- No documentation to back up claims

### How to Stay Safe
- Keep all bank statements
- Use a separate card/account for business expenses if possible
- Document everything in this repo (git history is timestamped proof)
- Generate revenue as soon as feasible

---

## Revenue Path (for future tax years)
- **npm package publishing** — `scbe-aethermoore` already published
- **API subscriptions** — FastAPI server ready for paid tiers
- **Patent licensing** — License SCBE technology to other companies
- **Consulting/contracting** — AI safety consulting using SCBE framework
- **HuggingFace models** — Fine-tuned models (including the tax model!)
- **Shopify/e-commerce** — Digital products, courses, toolkits

---

## Future: HuggingFace Tax Agent Training

Plan to fine-tune a HuggingFace model on personal tax workflow:
- **Training data sources**: This file, the CSV tracker, IRS Schedule C instructions, tax code references
- **Goal**: Model that can categorize expenses, flag deductions, estimate refunds, and prepare Schedule C data
- **Method**: Use SCBE SFT training pipeline (`/scbe-training-pipeline`) to generate training pairs
- **Dataset structure**: Input = raw bank statement line → Output = categorized expense with tax treatment
- **Potential SFT pairs**:
  - "Anthropic $20.00 01/15/2026" → `{ category: "AI Subscription", deductible: true, schedule_c_line: 27a, purpose: "Development tools" }`
  - "Hetzner €4.51 02/01/2026" → `{ category: "Hosting/Cloud", deductible: true, schedule_c_line: 25, purpose: "Server infrastructure" }`
- **Training compute costs are also deductible** as business R&D expenses

---

## Agent Handoff Context

Any agent picking this up should:
1. Read this file and `TAX_EXPENSE_TRACKER_2026.csv` first
2. Check the Status Checklist above for what's done vs. pending
3. The owner (issdandavis) needs to download bank statements and fill in actual amounts
4. No business license exists — not needed for Schedule C (see section above)
5. EIN is optional but recommended — check if one has been obtained
6. Revenue generation is the key next step for hobby rule compliance
7. All expenses should tie back to SCBE-AETHERMOORE development activity
