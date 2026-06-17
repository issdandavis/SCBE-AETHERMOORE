# Elastic/Funnel Hashing Open Questions

1. Should the existing SCBE file be renamed to `bijective_double_hash.py`, or should the class name change while keeping the filename for compatibility?

2. Does tokenizer integration need negative lookup performance, or only positive key lookup and deterministic placement?

3. What load factor should the tokenizer/memory layer target in production: 90%, 99%, 99.9%, or 99.99%?

4. Should the true elastic/funnel prototype prioritize:
   - correctness against the paper's structure,
   - speed in Python,
   - or a direct Rust/C implementation for hot-path use?

5. How should schema "modes/scales" map into the seed space: one seed per language, per chemistry namespace, per session, or per compiled target?
