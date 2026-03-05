# NPC Round Table Sessions

Generated NPC training artifacts land here.

Primary generator:
- `scripts/system/polly_npc_roundtable_builder.py`

Expected files:
- `npc_cards.jsonl`
- `npc_roundtable_sft.jsonl`
- `npc_roundtable_dpo.jsonl`
- `npc_registry.json`

This folder is consumed by:
- `scripts/system/polly_cross_model_bootstrap.py`
- `training/vertex_hydra_trainer.py` category matching (`npc_roundtable_sessions`)

