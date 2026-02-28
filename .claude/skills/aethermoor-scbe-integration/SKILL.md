---
name: aethermoor-scbe-integration
description: "Build and extend the SCBE-Tuxemon bridge — battle telemetry hooks, combat blockchain, AI NPC schedules, deed tracking, Sacred Tongue resonance, DPO training data generation, and Colab/Gemini AI backends. Use when wiring SCBE governance into gameplay, adding training data generation, or connecting AI backends to in-game NPCs."
---

# Aethermoor SCBE Integration

Use this skill when working on the SCBE-to-Tuxemon bridge modules at `demo/tuxemon_src/mods/aethermoor/`.

## Architecture

```
Player Action -> Battle Hook (patches damage formula)
  -> Combat Blockchain (14-layer telemetry per block)
    -> SFT/DPO Training Pairs (JSONL)
  -> Combat Bridge (EventBus subscriber)
    -> AI Schedules (spin-coherence NPC routines)
    -> Deed Tracking (Fable-style reputation)
  -> AI Reactive NPCs (Colab Qwen / Gemini / Scripted)
```

## Module Map

| Module | File | Purpose |
|---|---|---|
| Battle Hook | `battle_hook.py` | Patches `formula.simple_damage_calculate` |
| Combat Blockchain | `combat_blockchain.py` | Immutable chain, 14-layer data per block |
| Combat Bridge | `combat_bridge.py` | Patches CombatState + EventBus subscription |
| AI Schedules | `ai_schedule.py` | Spin-coherence NPC daily routines |
| AI Reactive | `ai_reactive.py` | Deed tracking + LLM NPC dialogue |
| SCBE Core | `scbe_core.py` | L5/L6/L8/L9/L11/L12/L13 math |
| PollyPad | `pollypad.py` | In-game PC terminal |
| Event Actions | `event/actions/track_deed.py` | YAML -> PlayerDeeds bridge |
| Event Actions | `event/actions/track_tongue.py` | YAML -> Tongue tracking |

## Sacred Tongue Weights (phi-powered)

```python
TONGUE_WEIGHTS = {
    "KO": PHI**0,  # 1.000 - Binding
    "AV": PHI**1,  # 1.618 - I/O
    "RU": PHI**2,  # 2.618 - Oaths
    "CA": PHI**3,  # 4.236 - Compute
    "UM": PHI**4,  # 6.854 - Shadow
    "DR": PHI**5,  # 11.090 - Schema
}
```

## Type -> Tongue Mapping

fire=KO, water=AV, earth=RU, metal=CA, shadow=UM, aether=DR, frost=AV, lightning=CA, wood=UM, sky=AV, heroic=KO

## Deed Tracking

| Prefix | Effect |
|---|---|
| `helped_` | +0.05 trust |
| `stole_`/`attacked_` | -0.10 trust |
| `caught_` | +1 monsters_caught |
| `won_`/`lost_` | +1 battles |

## AI Backends (priority order)

1. Colab Tunnel (`COLAB_TUNNEL_URL`) - local Qwen via cloudflared
2. Gemini Flash (`GEMINI_API_URL`) - Google Gemini 2.5
3. Scripted fallback - hardcoded reactions

## Data Output

`mods/aethermoor/data/combat_chains/` - blockchain JSONL + DPO pairs per battle

## Adding New Integrations

1. Create `.py` in `mods/aethermoor/`
2. Use monkey-patching or EventBus (don't modify engine)
3. Add `import mods.aethermoor.your_module` to `run_aethermoor.py`
4. For event actions: `EventAction` subclass in `event/actions/`
5. For PC features: `MenuProvider` subclass + `PCMenuRegistry.register()`
