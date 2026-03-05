# DM Sessions

Drop DM/game-master session logs here as JSONL.

Recommended shape:

```json
{"instruction":"...", "input":"scene context", "output":"DM/NPC response", "source":"dm_sessions", "tongue":"UM"}
```

or chat format:

```json
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

This folder is included in cross-model funnel bootstrap and HYDRA UM training categories.

