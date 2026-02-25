# SPIRAL FORGE RPG — Locked Game Design Document v1.0

**Codename:** Spiralverse
**Engine:** Godot 4 · 3D Tile-Based · Six Sacred Tongues
**Date Locked:** 2026-02-24

---

## 0. IP Safety

### What We Use (aesthetic feel, NOT mechanics/assets):
- Ruby/Sapphire → GBA-era color saturation, town warmth
- Digimon → branching evolution, companion depth
- Zelda → real-time sword combat, dungeon exploration
- Solo Leveling → manhwa tower system, rank badges

### What We DON'T Copy:
- Any route layouts, gym structures, battle UI from Nintendo/Bandai
- Fire/Water/Grass triangle (ours = Hodge dual pairs via Cl(4,0))
- Level-based evolution (ours = behavioral selection in R^6)
- Rock-paper-scissors type chart (ours = bivector commutator)

---

## 1. Engine: Godot 4 + GridMap

Low-poly 3D tiles. Camera: 3/4 top-down. Grid: 1x1x1 meter cubes.
Character models: 400-800 tris, 2.5-head chibi proportions.
Target: 480x270 internal, x3/x4 scale for modern displays.

## 2. Story: You Are Marcus Chen's Child

- **Tutorial (Hearthstone Landing):** Help townsfolk, meet Polly, meet Marcus
- **Act 1 (Academy):** Meet Izack, Zara, Aria. Classes unlock Tongues.
- **Act 2+ (Open World):** Six tongue regions, dungeons, guild quests, Void Seed

## 3. Companion System: 21D Seal Entities

Each companion IS a canonical state vector. Evolution = behavioral, not level.
Network graph with Laplacian emergent bonuses.

## 4. Dual Combat

- Overworld: Zelda-style real-time (sword + tongue magic + companion assists)
- Arena: Tactical fleet battles (Storm/Phalanx/Lance/Web formations)
- Type advantage: Cl(4,0) bivector commutator (continuous, geometric)

## 5. Math-as-Monsters

Monsters are problem entities. Attacks are formal transforms.
SymPy oracle validates correctness. SCBE gates reasoning steps.

## 6. 100-Floor Tower (Manhwa)

Floors 1-10: Arithmetic → Floors 91-99: Open research.
Rank badges: F through Transcendent.

## 7. Real Internet via SCBE

Codex terminals provide gated internet. 14-layer pipeline per request.
Green=ALLOW, Yellow=QUARANTINE, Red=DENY.

## 8. Connected Services

Anthropic, HuggingFace, Notion, Linear, Stripe, Suno, GitHub, etc.

---

*See full specification in src/game/ TypeScript + Python implementations.*
