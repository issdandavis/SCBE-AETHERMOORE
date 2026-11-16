# game/

Two game clients for the Spiralverse setting.

- `godot/` — "Spiral Forge RPG", a Godot 4 project: player controller, companion AI, an in-game terminal UI, and `scripts/scbe/scbe_client.gd`, the HTTP bridge to the SCBE Python backend.
- `spiral-engine/` — React/Vite browser game. `src/tongueRoles.js` mirrors `python/scbe/tongue_roles.py`; keep the two in sync.

Server-side game logic is in `src/game/` and `src/gacha_isekai/`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/game.md`](../docs/file-index/game.md).
