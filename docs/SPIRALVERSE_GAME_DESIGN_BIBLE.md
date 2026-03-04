# Spiralverse Game Design Bible

## Tuxemon-Spiralverse Isekai RPG

*By Issac Davis*
*Patent Pending: USPTO #63/961,403*

> **SCBE Integration**: This game design implements the SCBE-AETHERMOORE architecture as playable mechanics. The Six Sacred Tongues become guild factions, the 14-layer pipeline becomes the progression system, and the swarm consensus becomes the AI-driven multiplayer governance. Code references point to actual implementations in this repository.

---

## Game Vision

Isekai RPG built on the Tuxemon engine with Fable-style reactive NPCs, manhwa progression systems, AI-driven world generation, and MMO multiplayer where AI agents train each other.

**Core Concept**: A small hand-built seed world that grows procedurally via a fine-tuned small language model (Qwen2.5-Coder-1.5B) running on Google Colab. Every player action becomes training data. The more you play, the more the world expands.

> **SCBE Mapping**: The procedural world generation uses the same φ-proportioned growth patterns as the `QuasicrystalLattice` in `quasicrystal.py` — aperiodic tiling ensures no exploitable repetition. The "every action becomes training data" loop mirrors the federated learning cycle described in the story's Epilogue.

---

## Starting Area — The Seed

The game starts at the Chen Family Home. The world is intentionally small (like Fable — only ~10 key locations from 292 existing maps).

### Key Locations (Rethemed from existing Tuxemon maps)

| Existing Map | Rethemed As | Purpose |
|---|---|---|
| player_house | Chen Family Home | Tutorial, Mom gives Keys/Phone/Wallet |
| Route to beach | Coastal Path | 3-4 encounters, NPCs gossip to Dad |
| manhattan_beach | Shattered Shore | Marcus Chen, isekai portal trigger |
| cotton_town | Guild Hub Town | Adventurer's guild, class registration |
| flower_city | Trade City | Merchants, auction house, crafting |
| eclipse_park | Sacred Grove | Polly's domain, tongue selection shrine |
| dragonscave | First Dungeon | Pocket dimension entrance |
| buddha_mountain | Spirit Peak | Training ground, skill masters |
| eclipse_crystal_town | Crystal Spire | End-game hub, banking |
| dojo1/2/3 | Class Dojos | Skill trainers per class |

> **SCBE Mapping**: The Sacred Grove (eclipse_park) is the in-game manifestation of the Six Tongues training chamber from Chapter 2 of the story. The tongue selection shrine uses the same hexagonal pedestal arrangement. Crystal Spire maps to the Archive's Core Zone in the Poincaré ball — the center where R = 1.000.

---

## Characters

### Family

- **Mom** — Tutorial NPC. "Don't forget Dad's jingle — Cellphone, Wallet, Keys, all a man needs!" Gives player Keys, Phone (PollyPad), and Wallet.
- **Marcus Chen (Dad)** — At the beach. Fable-style reactive — comments on everything you did on the path to finding him. Different lines based on player deed flags.

> **SCBE Mapping**: Marcus Chen is the protagonist of the Six Tongues Protocol story (see `docs/six-tongues-protocol-story.md`). His PollyPad phone is the player's interface to the `DroneCore` system in `drone-core.ts` — six drones mapped to the Six Tongues.

### Lore Characters (from Dropbox/Everweave archives)

- **Izack Thorne** — Living bridge between dimensions
- **Aria Ravencrest** — "Boundaries are negotiations, not walls"
- **Alexander Thorne** — Wrote the 95 Theses of Collaborative Casting
- **Polly** — Co-equal intelligence, NOT a pet. Battle advisor + guide
- **Fizzle** — Pocket dimension guide/trickster
- **Thalorion** — Ancient codex keeper

> **SCBE Mapping**: Polly is the Fifth Circle Keeper from the story. Her in-game role as "co-equal intelligence, NOT a pet" reflects the `PollyPadManager` architecture in `fleet-manager.ts` — Polly Pads are autonomous agents with their own trust scores, not subordinate tools. Aria's quote "Boundaries are negotiations, not walls" is the story's core lesson from Chapter 5 (Intent and Integrity).

---

## Isekai + Manhwa Systems

### Classes (Pick at the Guild)

| Class | Focus | SCBE Tongue |
|---|---|---|
| **Tamer** | Monster focus (classic tuxemon gameplay) | KO (Kor'aelin) — intent/command |
| **Cipher** | Sacred Tongue magic user (SCBE integration) | CA (Cassisivadan) — compute/encryption |
| **Warden** | Tank/guardian, Fable-style melee | RU (Runethic) — policy/protection |
| **Broker** | Trade/economy specialist | AV (Avali) — transport/flow |

> **SCBE Mapping**: Each class maps to a Sacred Tongue domain. The Cipher class directly uses `SacredTongueTokenizer.encode_bytes()` from `sacred_tongues.py` for spellcasting mechanics. The Tamer class's monster command system uses the same declarative intent model described in Chapter 3 — "declare what should be true" rather than imperative commands.

### Guilds

Factions aligned with Sacred Tongues. Each judges you by different morals (Fable reboot style — subjective reputation per faction).

| Guild | Tongue | Domain | Values |
|---|---|---|---|
| Heart Weavers | KO (Kor'aelin) | Intent/Binding | Collaboration, emotional truth |
| Bridge Walkers | AV (Avali) | Diplomacy | Trade, cross-cultural understanding |
| Oath Keepers | RU (Runethic) | Binding/Oaths | Honor, historical preservation |
| Root Network | CA (Cassisivadan) | Nature/Compute | Playfulness, ecological communion |
| Shadow Court | UM (Umbroth) | Concealment | Productive discontinuity, secrets |
| Forge Masters | DR (Draumric) | Structure | Manifestation, building, authority |

> **SCBE Mapping**: The six guilds map 1:1 to the `TONGUE_PHASES` in `drone-core.ts` at 60° intervals. Guild reputation scores use the same trust-weighted influence system as `SwarmFormationManager` in `swarm-formation.ts`. The per-guild subjective reputation (no binary good/evil) mirrors SCBE's geometric trust model — trust is a continuous position in the Poincaré ball, not a boolean. The Sacred Tongue keywords for each guild are defined in `docs/SPIRALVERSE_CODEX.md`: KO (vel, sil, keth, dor, mira), AV (serin, nurel, lumenna), RU (khar, drath, bront, veto, grant), CA (klik, spira, ifta), UM (veil, hollow, nar'shul), DR (anvil, tharn, mek).

### Skills

Manhwa status window popup via PollyPad phone. Shows class, level, skills, reputation per guild.

### Trade

Phone banking already exists. Expand with auction house, player-to-player/AI-to-AI trading.

### Pocket Dimensions

Solo Leveling-style gates. Small procedural dungeon maps. Fizzle guides you in. Clear for loot. AI model generates variants.

> **SCBE Mapping**: Pocket dimensions are the game version of the SCBE Poincaré ball's interior zones. Each pocket dimension has a radial distance R from center — deeper dimensions are harder (higher H(d,R) cost, matching `layer_12_harmonic_scaling()` in `fourteen_layer_pipeline.py`). The procedural generation uses quasicrystal tiling from `QuasicrystalLattice.map_gates_to_lattice()` in `quasicrystal.py` to ensure aperiodic, non-exploitable dungeon layouts.

---

## Fable Design Patterns Applied

### Dad's Reactive Dialogue (Fable 1 Birthday Gift)

Marcus Chen tracks player deeds via flags set during the Coastal Path walk:

- Helped someone → positive comment
- Caught a monster → impressed comment
- Broke something → disappointed comment
- Talked to everyone → "You're just like your mother"

### Morality / Reputation

No binary good/evil meter. Per-guild, per-NPC subjective reputation (Fable 2026 reboot style). Different cultures judge you by different values.

### Small Choices → Big Consequences

Early decisions on the Coastal Path reshape later areas (Fable 2 Warrant Choice pattern).

### Visual Feedback

- Monster evolution influenced by player alignment
- Polly's plumage changes with morality
- Weapon/item morphing (Fable 3 style)

> **SCBE Mapping**: The morality/reputation system uses the same multi-dimensional trust geometry as `swarm_governance.py` — each guild has a `REALM_CENTER` in 6D space, and the player's position relative to each center determines reputation. This is NOT a flat scalar — it's a hyperbolic distance computation matching `layer_5_hyperbolic_distance()` in `fourteen_layer_pipeline.py`. Polly's plumage changes map to `FluxState` visual indicators in `drone-core.ts`.

---

## AI Backend Architecture

### Colab Server (Free T4 GPU)

FastAPI server running fine-tuned Qwen2.5-Coder-1.5B via cloudflared tunnel.

### Endpoints

| Endpoint | Function |
|---|---|
| `/health` | Server status |
| `/chat` | General NPC dialogue |
| `/npc` | Fable-style reactive NPC lines (takes `player_deeds` list) |
| `/battle` | Polly battle advisor |
| `/worldseed` | Procedural area/NPC/quest generation |
| `/ai_chat` | AI-to-AI MMO chat |

### Training Pipeline

1. `ai_training_bridge.py` logs every player action as SFT/DPO pairs
2. Export to HuggingFace: `issdandavis/spiralverse-ai-federated-v1`
3. Retrain cycle: play → log → export → fine-tune → deploy → play

> **SCBE Mapping**: The AI backend's training pipeline mirrors SCBE's federated learning architecture. The `/battle` endpoint uses the same swarm consensus logic as `SwarmCoordinator` in `swarm.ts` — Polly evaluates battle options through the Flux ODE (`dν/dt = α(ν_target - ν) - β*decay + γ*coherence`). The `/worldseed` endpoint's procedural generation passes through the 14-layer pipeline for safety validation before manifesting in-game.

---

## MMO / Multiplayer Layer

### Existing Infrastructure

- WebSocket server/client (built)
- Headless client (built — runs without graphics)
- Network manager + event dispatcher (built)
- AI manager for battle turns (built)
- Host/Join/Scan multiplayer menu (built)

### MMO Communication (To Build)

| Command | Scope |
|---|---|
| `/say` | Local chat |
| `/shout` | Zone-wide |
| `/whisper` | DM |
| `/party` | Party chat |
| `/guild` | Guild chat |
| `/trade` | Trade request |
| `/emote` | Visible actions |

### AI Players (Training Loop)

Headless AI agents connect as players. They walk maps, battle, chat, trade, form guilds. All interactions logged as training data. The AI learns to play and socialize from playing with itself.

> **SCBE Mapping**: AI player swarm governance uses the `FleetManager` architecture from `fleet-manager.ts`. Each AI player is a `DroneCore` instance with a `SpectralIdentity` tied to its guild's Sacred Tongue. The headless agents form a `SwarmCoordinator` mesh (`swarm.ts`) where consensus determines group behavior. Rogue AI players (griefers, exploiters) are detected via `detect_rogue_agents()` and excluded through the same geometric trust model used against Kael Nightwhisper in Chapter 8 of the story.

### SCBE Swarm Integration

The `scbe-swarm` package provides Byzantine-tolerant agent coordination:

- Trust scores per agent (τ ∈ [0,1])
- Auto-exclusion of rogue agents via geometry (no admin needed)
- Trust-weighted consensus voting
- TCP gossip protocol for real networking
- Patent Claims 34-40 coverage

> **SCBE Mapping**: This maps directly to `roundtable_consensus()` in `swarm_browser.py` with 4/6 quorum threshold and `ByzantineConsensus` class. The trust scores use the same Poincaré ball radial distance as the story's dimensional drift — agents closer to center (higher trust) have more influence. The "no admin needed" auto-exclusion is the story's counter-swarm principle: the swarm itself enforces compliance through distributed consensus, not centralized authority.

---

## Sacred Tongues System (Canonical)

| Code | Name | Weight | Phase | Domain |
|---|---|---|---|---|
| KO | Kor'aelin | 1.000 | 0 | Intent, binding, resonance |
| AV | Avali | 1.618 | π/3 | Diplomacy, context bridge |
| RU | Runethic | 2.618 | 2π/3 | Oaths, temporal anchoring |
| CA | Cassisivadan | 4.236 | π | Nature, recursive play |
| UM | Umbroth | 6.854 | 4π/3 | Concealment, severance |
| DR | Draumric | 11.090 | 5π/3 | Forge, manifestation |

24 runic letters (Kor'aelin alphabet). 14 core particles. 6 × 256 = 1,536 bijective tokens.

> **SCBE Mapping**: This table IS the canonical reference implemented in `sacred_tongues.py`. The weights follow Fibonacci scaling (1.000, 1.618, 2.618, 4.236, 6.854, 11.090) — each weight ≈ PHI × previous weight. The phases at 60° intervals match `TONGUE_PHASES` in `drone-core.ts`. The 1,536 bijective tokens (6 × 256) are generated by `SacredTongueTokenizer.__init__()` which creates bijective mappings for each tongue. The `compute_harmonic_fingerprint()` method produces the φ-dimensional signature that is unforgeable per the Fractal Proof (Chapter 15).

---

## Lore Sources (Dropbox Archive)

- `Avalon_Character_Codex.txt`
- `Izack_Master_Lore_Archive23.txt`
- `Izack_Master_Lorebook.txt`
- `The_Complete_Avalon_Codex.txt`
- `CHAPTER 2 THE WORLD TREE BLOOMS.txt`
- `spiral-of-pollyoneth-novel.md`
- `The_Spiral_Guild_Council_Archives.txt`
- `Spiral_World_Framework.txt`
- `Thalorion_Codex_Full.pdf`
- `Everweave history export (genesis seed)`
- `Izack_Full_Timeline.txt`
- `Character_Codex.pdf`
- 40+ additional files

---

## UI Enhancements

### Side Panels (Black Letterbox Space)

- Inventory panel
- Mini-map
- Compass
- Phone (PollyPad) quick access
- Wallet display
- Keys indicator

### Graphics Improvements

- Lighting/shader overlays
- Parallax scrolling backgrounds
- Particle effects on Sacred Tongue items
- Portrait art for key NPCs (AI-generated, Ghibli/manhwa style)
- Manhwa-style status popups

### Input

- Mouse click-to-move navigation
- Mario-style single jump (no double jump)
- Keyboard + mouse hybrid controls

---

## Tech Stack Summary

| Component | Tech |
|---|---|
| Game Engine | Tuxemon (Python/Pygame) |
| AI Model | Qwen2.5-Coder-1.5B (QLoRA fine-tuned) |
| AI Hosting | Google Colab T4 GPU + cloudflared tunnel |
| Multiplayer | WebSocket (asyncio) |
| Swarm Governance | SCBE-Swarm (Byzantine tolerant) |
| Training Data | SFT/DPO via `ai_training_bridge.py` |
| Model Hub | HuggingFace (`issdandavis/`) |
| Lore Source | Dropbox + Everweave origin logs |
| Tokenizer | 6 Sacred Tongues × 256 tokens |
| Security | SCBE-AETHERMOORE 14-layer pipeline |

---

*Patent Pending: USPTO #63/961,403*

*"Thul'medan kess'ara nav'kor zar'aelin" — The spiral turns, knowledge grows through different hearts across dimensions*

© 2026 Issac Davis. All rights reserved.
