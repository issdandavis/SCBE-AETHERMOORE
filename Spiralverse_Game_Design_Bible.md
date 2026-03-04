Spiralverse Game Design Bible — Tuxemon-Spiralverse
Game Vision
Isekai RPG built on Tuxemon engine with Fable-style reactive NPCs, manhwa progression systems, AI-driven world generation, and MMO multiplayer where AI agents train each other.
Core Concept: A small hand-built seed world that grows procedurally via a fine-tuned small language model (Qwen2.5-Coder-1.5B) running on Google Colab. Every player action becomes training data. The more you play, the more the world expands.
Starting Area — The Seed
The game starts at the Chen Family Home. The world is intentionally small (like Fable — only ~10 key locations from 292 existing maps).
Key Locations (Rethemed from existing Tuxemon maps)
Existing Map Rethemed As Purpose player_house Chen Family Home Tutorial, Mom gives Keys/Phone/Wallet Route to beach Coastal Path 3-4 encounters, NPCs gossip to Dad manhattan_beach Shattered Shore Marcus Chen, isekai portal trigger cotton_town Guild Hub Town Adventurer's guild, class registration flower_city Trade City Merchants, auction house, crafting eclipse_park Sacred Grove Polly's domain, tongue selection shrine dragonscave First Dungeon Pocket dimension entrance buddha_mountain Spirit Peak Training ground, skill masters eclipse_crystal_town Crystal Spire End-game hub, banking dojo1/2/3 Class Dojos Skill trainers per class
Characters
Family
* Mom — Tutorial NPC. "Don't forget Dad's jingle — Cellphone, Wallet, Keys, all a man needs!" Gives player Keys, Phone (PollyPad), and Wallet.
* Marcus Chen (Dad) — At the beach. Fable-style reactive — comments on everything you did on the path to finding him. Different lines based on player deed flags.
Lore Characters (from Dropbox/Everweave archives)
* Izack Thorne — Living bridge between dimensions
* Aria Ravencrest — "Boundaries are negotiations, not walls"
* Alexander Thorne — Wrote the 95 Theses of Collaborative Casting
* Polly — Co-equal intelligence, NOT a pet. Battle advisor + guide
* Fizzle — Pocket dimension guide/trickster
* Thalorion — Ancient codex keeper
Isekai + Manhwa Systems
Classes (Pick at the Guild)
* Tamer — Monster focus (classic tuxemon gameplay)
* Cipher — Sacred Tongue magic user (SCBE integration)
* Warden — Tank/guardian, Fable-style melee
* Broker — Trade/economy specialist
Guilds
Factions aligned with Sacred Tongues. Each judges you by different morals (Fable reboot style — subjective reputation per faction).
Guild Tongue Domain Values Heart Weavers KO (Kor'aelin) Intent/Binding Collaboration, emotional truth Bridge Walkers AV (Avali) Diplomacy Trade, cross-cultural understanding Oath Keepers RU (Runethic) Binding/Oaths Honor, historical preservation Root Network CA (Cassisivadan) Nature/Compute Playfulness, ecological communion Shadow Court UM (Umbroth) Concealment Productive discontinuity, secrets Forge Masters DR (Draumric) Structure Manifestation, building, authority
Skills
Manhwa status window popup via PollyPad phone. Shows class, level, skills, reputation per guild.
Trade
Phone banking already exists. Expand with auction house, player-to-player/AI-to-AI trading.
Pocket Dimensions
Solo Leveling-style gates. Small procedural dungeon maps. Fizzle guides you in. Clear for loot. AI model generates variants.
Fable Design Patterns Applied
Dad's Reactive Dialogue (Fable 1 Birthday Gift)
Marcus Chen tracks player deeds via flags set during the Coastal Path walk:
* Helped someone → positive comment
* Caught a monster → impressed comment
* Broke something → disappointed comment
* Talked to everyone → "You're just like your mother"
Morality / Reputation
No binary good/evil meter. Per-guild, per-NPC subjective reputation (Fable 2026 reboot style). Different cultures judge you by different values.
Small Choices → Big Consequences
Early decisions on the Coastal Path reshape later areas (Fable 2 Warrant Choice pattern).
Visual Feedback
* Monster evolution influenced by player alignment
* Polly's plumage changes with morality
* Weapon/item morphing (Fable 3 style)
AI Backend Architecture
Colab Server (Free T4 GPU)
FastAPI server running fine-tuned Qwen2.5-Coder-1.5B via cloudflared tunnel.
Endpoints
* /health — Server status
* /chat — General NPC dialogue
* /npc — Fable-style reactive NPC lines (takes player_deeds list)
* /battle — Polly battle advisor
* /worldseed — Procedural area/NPC/quest generation
* /ai_chat — AI-to-AI MMO chat
Training Pipeline
* ai_training_bridge.py logs every player action as SFT/DPO pairs
* Export to HuggingFace: issdandavis/spiralverse-ai-federated-v1
* Retrain cycle: play → log → export → fine-tune → deploy → play
MMO / Multiplayer Layer
Existing Infrastructure
* WebSocket server/client (built)
* Headless client (built — runs without graphics)
* Network manager + event dispatcher (built)
* AI manager for battle turns (built)
* Host/Join/Scan multiplayer menu (built)
MMO Communication (To Build)
* /say — Local chat
* /shout — Zone-wide
* /whisper — DM
* /party — Party chat
* /guild — Guild chat
* /trade — Trade request
* /emote — Visible actions
AI Players (Training Loop)
Headless AI agents connect as players. They walk maps, battle, chat, trade, form guilds. All interactions logged as training data. The AI learns to play and socialize from playing with itself.
SCBE Swarm Integration
The scbe-swarm package provides Byzantine-tolerant agent coordination:
* Trust scores per agent (τ ∈ [0,1])
* Auto-exclusion of rogue agents via geometry (no admin needed)
* Trust-weighted consensus voting
* TCP gossip protocol for real networking
* Patent Claims 34-40 coverage
This governs the AI player swarm — ensures AI agents behave correctly and rogue/broken agents get auto-excluded from the MMO.
Sacred Tongues System (Canonical)
Code Name Weight Phase Domain KO Kor'aelin 1.000 0 Intent, binding, resonance AV Avali 1.618 π/3 Diplomacy, context bridge RU Runethic 2.618 2π/3 Oaths, temporal anchoring CA Cassisivadan 4.236 π Nature, recursive play UM Umbroth 6.854 4π/3 Concealment, severance DR Draumric 11.090 5π/3 Forge, manifestation
24 runic letters (Kor'aelin alphabet). 14 core particles. 6×256 = 1,536 bijective tokens.
Lore Sources (Dropbox Archive)
* Avalon_Character_Codex.txt
* Izack_Master_Lore_Archive23.txt
* Izack_Master_Lorebook.txt
* The_Complete_Avalon_Codex.txt
* CHAPTER 2 THE WORLD TREE BLOOMS.txt
* spiral-of-pollyoneth-novel.md
* The_Spiral_Guild_Council_Archives.txt
* Spiral_World_Framework.txt
* Thalorion_Codex_Full.pdf
* Everweave history export (genesis seed)
* Izack_Full_Timeline.txt
* Character_Codex.pdf
* 40+ additional files
UI Enhancements
Side Panels (Black Letterbox Space)
* Inventory panel
* Mini-map
* Compass
* Phone (PollyPad) quick access
* Wallet display
* Keys indicator
Graphics Improvements
* Lighting/shader overlays
* Parallax scrolling backgrounds
* Particle effects on Sacred Tongue items
* Portrait art for key NPCs (AI-generated, Ghibli/manhwa style)
* Manhwa-style status popups
Input
* Mouse click-to-move navigation
* Mario-style single jump (no double jump)
* Keyboard + mouse hybrid controls
Tech Stack Summary
Component Tech Game Engine Tuxemon (Python/Pygame) AI Model Qwen2.5-Coder-1.5B (QLoRA fine-tuned) AI Hosting Google Colab T4 GPU + cloudflared tunnel Multiplayer WebSocket (asyncio) Swarm Governance SCBE-Swarm (Byzantine tolerant) Training Data SFT/DPO via ai_training_bridge.py Model Hub HuggingFace (issdandavis/) Lore Source Dropbox + Everweave origin logs Tokenizer 6 Sacred Tongues × 256 tokens Security SCBE-AETHERMOORE 14-layer pipeline
Patent Pending: USPTO #63/961,403
"Thul'medan kess'ara nav'kor zar'aelin" — The spiral turns, knowledge grows through different hearts across dimensions