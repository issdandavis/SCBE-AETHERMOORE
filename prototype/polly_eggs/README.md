# Polly Eggs Prototype (AI Raising Game)

Prototype game/training loop where agents hatch from eggs, learn through lessons, and run expeditions in a hybrid world (procedural + authored).

## Components
- `models.py`: egg genome and agent state.
- `world.py`: time-evolving world map.
- `lesson_engine.py`: lesson application and stat updates.
- `geoseal_hooks.py`: governance gate for action decisions.
- `batch_hatchery.py`: batch incubation/hatching.
- `trainer.py`: end-to-end training/episode runner.

## Run Demo
```powershell
python prototype/polly_eggs/examples/run_sim.py
```

## Run Retro Gen-1 Style View
```powershell
python prototype/polly_eggs/examples/run_gen1_game.py
```
Controls:
- Arrow keys: move
- `Z`: gather resources
- `X`: run a training lesson

## Data Output
Episodes can be transformed into HF-ready JSONL with:
```powershell
python training/build_polly_eggs_dataset.py
```
