A DnD campaign accidentally produced a working AI governance framework -- here's how

I played Everweave (AI-powered DnD) for months. 12,596 paragraphs of game logs accumulated. When I analyzed the invented languages from those sessions, they had internal linguistic structure -- consistent phoneme patterns and morphological rules -- that nobody intentionally designed.

Six distinct linguistic patterns emerged. I built a tokenizer from them. Then I asked: what if those six patterns were dimensions in a geometric space where distance corresponds to trust?

That became **SCBE-AETHERMOORE**: a 14-layer AI governance pipeline that uses hyperbolic geometry to make adversarial behavior exponentially expensive.

**The approach**: Instead of detecting bad AI behavior after it happens (classifiers, RLHF), embed agent behavior in the Poincare ball model of hyperbolic space. Trusted behavior clusters near the origin. Adversarial drift toward the boundary costs exponentially more:

- Distance 1: cost ~1.6x
- Distance 3: cost ~75x
- Distance 5: cost ~57,665x

The six "sacred tongues" from the game logs became six trust dimensions, weighted by the golden ratio. Governance dimensions carry higher weight -- an agent deviating in its governance behavior triggers the cost wall faster.

**Practical results**:
- 95.3% adversarial prompt injection detection
- Zero false denials on compliance suite
- Under 8ms for all 14 layers on commodity hardware
- Post-quantum crypto (ML-KEM-768, ML-DSA-65) for every signed governance decision

The EU AI Act enforcement begins August 2026. This pipeline produces exactly the kind of signed, auditable governance artifacts that regulators will demand.

MIT licensed. Install with `npm install scbe-aethermoore` or `pip install scbe-aethermoore`.

GitHub: https://github.com/issdandavis/SCBE-AETHERMOORE

The game logs also became a novel -- *The Six Tongues Protocol* -- and a manhwa in production. Same origin, dual outputs: fiction and infrastructure.
