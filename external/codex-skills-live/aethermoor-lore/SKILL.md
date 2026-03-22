---
name: aethermoor-lore
description: "Reference and generate Aethermoor world lore, characters, locations, magic systems, and story canon. Use when writing dialogue, scenes, world-building content, NPC backstories, quest text, or any narrative content for the Aethermoor game."
---

# Aethermoor Lore

## World

Aethermoor is a realm of floating islands suspended in purple twilight, connected by crystalline data lattices called the AetherNet. The world exists inside protocol space -- reality here is authorization-dependent and existence is continuously verified through the Six Sacred Tongues.

### Key Locations

| Location | Description | Tongue Affinity |
|----------|-------------|-----------------|
| **Avalon Academy** | Training grounds for new arrivals, lecture halls carved into floating stone | KO (Authority) |
| **Spiral Spire** | Towering research facility, dimensional experiments | CA (Compute) |
| **Timeless Observatory** | Time manipulation research, temporal governance | RU (Policy) |
| **World Tree (Pollyoneth)** | Ancient tree connecting all islands, Polly's archive | DR (Schema) |
| **Starter Village** | Where isekai'd travelers first arrive, safe zone | AV (Transport) |
| **Shadow Depths** | Underground dungeon network, corrupted protocols | UM (Security) |
| **Guild Hub** | Central overworld hub with shops, NPCs, quests | All |

### Cosmology

- Islands float on currents of governance energy
- Distance between islands = hyperbolic distance in Poincare ball
- The boundary of the ball = infinite cost = the Void
- Adversarial intent pushes you toward the boundary (exponential cost)
- The Harmonic Wall (`H(d) = R^(d^2)`) is a literal force field protecting safe zones

## Characters

### Protagonist

**Izack (Marcus Chen's son)** -- A systems architect from Earth who wakes in Aethermoor after reading a mysterious book. Dimensional storage mage, research scholar. Starts as "Undecided" class, chooses identity through gameplay.

### Party Members

| Character | Role | Tongue | Personality |
|-----------|------|--------|-------------|
| **Polly** | Raven familiar | DR | Sarcastic, wise, Fifth Circle Keeper of the Archives. Monitors the AetherNet from the Wingscroll Archive. "CAW! You were expected." |
| **Clay** | Sand golem | CA | Enthusiastic, loyal, earth elemental study buddy. Communicates through grinding noises and occasional words. |
| **Eldrin** | Cartographer | AV | Quiet, precise, dimensional navigation expert. Maps the gaps between islands. |
| **Aria** | Warrior-scholar | RU | Fierce, principled, boundary magic + mathematics. Enforces policy through combat. |
| **Zara** | Dragon-blooded engineer | CA | Inventive, intense, fire + code. Builds machines from governance protocols. |
| **Kael Nightwhisper** | Izack's son | UM | Prodigal shadow mage, torn loyalties. Found in the Shadow Depths. |

### Character Voice Examples

**Polly**: Always starts with "CAW!" or a bird-related quip. Uses protocol terminology as idioms. "Your authorization level is... adequate. Barely."

**Clay**: Short sentences, earthy metaphors. "*happy grinding noises* Clay... help. Clay strong."

**Eldrin**: Maps and distances. "The gap between these islands is 3.7 hyperbolic units. Crossable, but the toll is steep."

**Aria**: Mathematical precision. "The boundary holds at epsilon < 0.001. We're safe -- for now."

## Magic System: Six Sacred Tongues

Each tongue is a programming language for reality. Learning a tongue = gaining governance authority in that domain.

| Tongue | Full Name | Domain | Weight (phi) | Color |
|--------|-----------|--------|-------------|-------|
| **KO** | Kor'aelin | Authority / Control | 1.00 | Red |
| **AV** | Avali | Transport / Messaging | 1.62 | Cyan |
| **RU** | Runethic | Policy / Constraints | 2.62 | Gold |
| **CA** | Cassisivadan | Compute / Encryption | 4.24 | Green |
| **UM** | Umbroth | Security / Secrets | 6.85 | Purple |
| **DR** | Draumric | Schema / Authentication | 11.09 | Orange |

### Type Effectiveness (Combat)

KO beats AV, AV beats CA, CA beats DR, DR beats RU, RU beats UM, UM beats KO.

### Proficiency

Characters grow tongue proficiency (0.0 to 1.0) through choices, battles, and study. Mastering a tongue unlocks new spells and governance authority.

## Evolution System (Digimon-style)

| Stage | Description |
|-------|-------------|
| Fresh | Just arrived / hatched |
| Rookie | Learning basics, one tongue emerging |
| Champion | Mid-tier, one tongue mastered |
| Ultimate | Strong, multiple tongues |
| Mega | Fully evolved |
| Ultra | Transcendent (post-game) |

### Growth Paths

- **Architect**: Builder path, high wisdom/defense, CA+DR focus
- **Berserker**: Combat path, high attack/speed, KO+UM focus
- **Corrupted**: Shadow path, unbalanced stats, all tongues but unstable

## AetherNet (The Pseudo-Internet)

The crystalline data lattice connecting all floating islands. In-world, it's a network where:
- NPCs communicate across islands
- Training data flows from player choices to the World Tree
- TV broadcasts ("AetherTV") show news, game events, player achievements
- The SCBE governance pipeline filters all traffic through the Sacred Tongues
- n8n workflows are the "routing protocols" of the AetherNet

### AetherTV Channels

- **Aethermoor News**: World events, player choices broadcast as news
- **Battle Arena**: Live battle reports and rankings
- **Tongue Academy**: Educational content about the Sacred Tongues
- **Shadow Watch**: Security alerts from the depths

## Combat System

Battles = debugging operations against digitized system bugs.

### Debug Actions (Attack Types)

| Action | Strong Against | Description |
|--------|---------------|-------------|
| ASSERT_STATE | null_pointer | Verify and fix state |
| SANITIZE_INPUT | cross_boundary | Clean bad data |
| LOCK_THREAD | race_condition | Synchronize operations |
| FLUSH_CACHE | memory_leak, float_precision | Clear corrupted memory |
| RECOMPILE | float_precision | Rebuild from source |
| ROLLBACK | forked_state | Restore to good state |
| REFACTOR | forked_state | Restructure code paths |
| ISOLATE_PROCESS | race_condition, memory_leak | Quarantine the bug |

### Boss Fights = Math Problems

Boss monsters encode math problems as quadratic coefficients. Solving the equation = finding the attack pattern that defeats them. "Dungeon breaks" are adversarial variants with poisoned premises.

## Story Arc

1. **Earth Life**: Izack is a systems architect, finds a mysterious book
2. **Transit**: Reality collapses, falls through protocol space
3. **Arrival**: Wakes on floating island, meets Polly and Clay
4. **Academy**: Learns the Sacred Tongues, chooses class identity
5. **Exploration**: Discovers the overworld, guild hub, other islands
6. **Dungeons**: Tower climbing, floor-by-floor monster debugging
7. **Shadow Depths**: Finds Kael, confronts corrupted protocols
8. **World Tree**: Final challenge at Pollyoneth, full tongue mastery

## Training Data Integration

Every gameplay action generates real training data:
- **Choices**: SFT pairs (context + chosen response)
- **Battles**: DPO pairs (winning vs losing strategies)
- **Evolution**: Curriculum progression data
- All data flows through SCBE governance pipeline before reaching HuggingFace
- The Harmonic Wall ensures nothing dangerous vectors through

## Writing Guidelines

- Pokemon Ruby-era tone: earnest, slightly dramatic, sense of wonder
- Keep dialogue short (GBA text box length ~3 lines)
- Every location should feel like it maps to a real system concept
- Magic is protocol architecture, not folklore spellcraft
- Use the Sacred Tongue names naturally in dialogue
- NPCs should reference the AetherNet like we reference the internet
