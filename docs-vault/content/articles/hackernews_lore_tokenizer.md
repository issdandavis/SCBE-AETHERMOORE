# Show HN: Lore-Seeded Tokenizer – 1,536 tokens trained on AI D&D game logs instead of web scrapes

I built a tokenizer where the training seed isn't Wikipedia or Common Crawl, but 12,596 paragraphs of AI-generated D&D campaign logs from Everweave (https://everweave.ai/).

**Why**: Standard tokenizer seeds are statistically massive but carry no narrative structure, emotional texture, or internal consistency. Game logs have all three — characters that persist across thousands of messages, emotional arcs, world rules that stay consistent.

**What**: Sacred Tongues tokenizer — 6 semantic domains (intent, transport, policy, compute, security, attestation), 256 tokens each, weighted by the golden ratio. Total: 1,536 tokens.

**The interesting part**: Context-drift detection. If someone generates token sequences without knowing the lore seed, their tokens measurably drift from canonical embeddings (measured via hyperbolic distance in a Poincare ball). This isn't primary auth — it's a contextual fingerprint layer.

**The math**: Adversarial cost scales as H(d,R) = R^(d^2). Each step toward adversarial behavior costs exponentially more. The six tongues form a Clifford algebra Cl(6,0) with 64 components.

**The backstory**: I played an AI D&D game for months, expanded the lore into books with ChatGPT, built a Replit workflow, and one weird vibe coding session later realized my magic system — where collaboration was cheap and unilateral force was expensive — was a security architecture.

Code: https://github.com/issdandavis/SCBE-AETHERMOORE
Dataset: https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data
Patent: USPTO #63/961,403

Built with TypeScript (canonical) + Python (reference). 14-layer security pipeline. Post-quantum crypto (ML-KEM-768, ML-DSA-65).

Happy to discuss the math, the tokenizer architecture, or the surprisingly productive intersection of fantasy worldbuilding and AI safety.
