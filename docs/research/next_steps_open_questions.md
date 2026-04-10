# Open Questions — Next Steps Research

**Date**: 2026-04-07

## Unresolved

1. **SAM.gov activation**: Registration submitted 2026-04-03, CAGE code pending. Federal activation can take 7-10 business days. Will it clear before CLARA deadline (April 17)? Check status at sam.gov.

2. **TriTera code release**: Paper says "TriTera suite and TriRun inference kernels will be released." Check GitHub/HuggingFace for availability. If released, test SCBE governance on their ternary models.

3. **Blank-slate data volume**: 107M tokens (current SFT corpus) vs 10B+ recommended for pre-training. Options to investigate:
   - Can curriculum learning compensate for smaller corpus? (No published evidence found)
   - Would a 125M param model train adequately on 107M tokens? (Chinchilla scaling suggests ~2.5B tokens needed for 125M params)
   - Can we augment with filtered Common Crawl or C4 to reach threshold?

4. **Tokenizer type for Sacred Tongues**: BPE (GPT-style), Unigram (SentencePiece), or fully custom phi-scaled? No precedent for phi-scaled tokenizers in literature. This is novel territory — may need to prototype all three and compare.

5. **MATHBAC solicitation format**: Proposers Day is April 21. The actual solicitation (PA/BAA/OT) will likely drop afterward. Unknown: award size, team requirements, period of performance, security clearance needs.

6. **Qwen3.5 vs Qwen2.5 for next training run**: Qwen3.5 just released with improved multilingual. Worth switching base model? Requires new adapter config and potentially different tokenizer handling.

7. **Maneuver engine architecture**: Runtime navigation is conceptually defined but no reference implementation exists in literature for "inference as navigation" distinct from "inference as weight forward pass." This is genuinely novel — which means no guide to follow.

## Next Checks

- [ ] Check sam.gov status for UEI J4NXHM6N5F59
- [ ] Search HuggingFace/GitHub for TriTera model releases
- [ ] Register for MATHBAC webcast at darpa.mil
- [ ] Check if APEX Accelerator can assist with CLARA OT proposal format
- [ ] Benchmark current Polly adapter on pop quiz before next training run
