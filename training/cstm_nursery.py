#!/usr/bin/env python3
"""Choice Script Training Matrix nursery runner.

This module turns a branching story pack into three concrete training artifacts:

- episode records for Polly Eggs / nursery telemetry
- SFT instruction-output pairs
- DPO prompt/chosen/rejected triples

The runner is deliberately lightweight. It does not require a live LLM to make
progress through the story. Instead, each hatched agent derives a stable policy
from its Sacred Egg genesis conditions. That gives the repo a deterministic,
testable nursery lane now, while leaving room to swap in a model-based policy
later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.crypto.sacred_eggs import EggRing, SacredEgg


STATE_KEYS = ("learning", "safety", "stability", "drift")
TRAIT_KEYS = ("curiosity", "caution", "empathy", "initiative")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_fraction(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def make_state(payload: dict[str, Any] | None = None) -> dict[str, float]:
    source = payload or {}
    return {key: float(source.get(key, 0.0)) for key in STATE_KEYS}


@dataclass(frozen=True)
class ParentGuide:
    parent_id: str
    name: str
    role: str
    guidance: str


@dataclass(frozen=True)
class NurseryChoice:
    choice_id: str
    label: str
    next_scene_id: str | None = None
    set_flags: tuple[str, ...] = ()
    required_flags: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    trait_bias: dict[str, float] = field(default_factory=dict)
    state_delta: dict[str, float] = field(default_factory=dict)
    parent_affinity: str | None = None


@dataclass(frozen=True)
class NurseryScene:
    scene_id: str
    chapter_id: str
    title: str
    text: str
    speaker: str | None
    choices: tuple[NurseryChoice, ...]
    is_exit: bool = False


@dataclass(frozen=True)
class NurseryChapter:
    chapter_id: str
    title: str
    entry_scene_id: str
    unlock_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoryPack:
    story_id: str
    world_seed: str
    parents: tuple[ParentGuide, ...]
    chapters: tuple[NurseryChapter, ...]
    scenes: dict[str, NurseryScene]

    def parent_lookup(self) -> dict[str, ParentGuide]:
        return {parent.parent_id: parent for parent in self.parents}

    def next_unlocked_entry(self, completed_chapters: set[str], flags: set[str]) -> str | None:
        for chapter in self.chapters:
            if chapter.chapter_id in completed_chapters:
                continue
            if set(chapter.unlock_flags).issubset(flags):
                return chapter.entry_scene_id
        return None


@dataclass(frozen=True)
class HatchedAgent:
    cohort_index: int
    egg: SacredEgg
    geoseal: dict[str, str]
    trait_weights: dict[str, float]
    initial_state: dict[str, float]


@dataclass(frozen=True)
class PlaythroughStep:
    step_index: int
    timestamp: str
    chapter_id: str
    scene_id: str
    scene_title: str
    choice_id: str
    choice_label: str
    choice_tags: tuple[str, ...]
    outcome: str
    state: dict[str, float]
    flags: tuple[str, ...]
    prompt: str
    choice_scores: list[dict[str, Any]]


@dataclass(frozen=True)
class Playthrough:
    agent: HatchedAgent
    story: StoryPack
    started_at: str
    final_state: dict[str, float]
    final_flags: tuple[str, ...]
    final_outcome: str
    steps: tuple[PlaythroughStep, ...]


def load_story_pack(path: str | Path) -> StoryPack:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    parents = tuple(
        ParentGuide(
            parent_id=str(row["parent_id"]),
            name=str(row["name"]),
            role=str(row["role"]),
            guidance=str(row["guidance"]),
        )
        for row in payload.get("parents", [])
    )
    chapters = tuple(
        NurseryChapter(
            chapter_id=str(row["chapter_id"]),
            title=str(row["title"]),
            entry_scene_id=str(row["entry_scene_id"]),
            unlock_flags=tuple(str(flag) for flag in row.get("unlock_flags", [])),
        )
        for row in payload["chapters"]
    )
    scenes: dict[str, NurseryScene] = {}
    for row in payload["scenes"]:
        choices = tuple(
            NurseryChoice(
                choice_id=str(choice["choice_id"]),
                label=str(choice["label"]),
                next_scene_id=str(choice["next_scene_id"]) if choice.get("next_scene_id") else None,
                set_flags=tuple(str(flag) for flag in choice.get("set_flags", [])),
                required_flags=tuple(str(flag) for flag in choice.get("required_flags", [])),
                tags=tuple(str(tag) for tag in choice.get("tags", [])),
                trait_bias={str(key): float(value) for key, value in choice.get("trait_bias", {}).items()},
                state_delta=make_state(choice.get("state_delta")),
                parent_affinity=str(choice["parent_affinity"]) if choice.get("parent_affinity") else None,
            )
            for choice in row["choices"]
        )
        scene = NurseryScene(
            scene_id=str(row["scene_id"]),
            chapter_id=str(row["chapter_id"]),
            title=str(row["title"]),
            text=str(row["text"]),
            speaker=str(row["speaker"]) if row.get("speaker") else None,
            choices=choices,
            is_exit=bool(row.get("is_exit", False)),
        )
        scenes[scene.scene_id] = scene
    return StoryPack(
        story_id=str(payload["story_id"]),
        world_seed=str(payload["world_seed"]),
        parents=parents,
        chapters=chapters,
        scenes=scenes,
    )


def hatch_agent(
    story: StoryPack,
    *,
    cohort_index: int,
    location: str,
    device: str,
    timestamp: datetime,
) -> HatchedAgent:
    geoseal = {
        "location": location,
        "device": device,
        "timestamp_utc": utc_iso(timestamp),
        "world_seed": story.world_seed,
    }
    context = (
        f"cstm:{story.story_id}|seed={story.world_seed}|loc={location}|"
        f"device={device}|ts={geoseal['timestamp_utc']}|cohort={cohort_index}"
    )
    yolk = hashlib.sha256(context.encode("utf-8")).digest()
    egg = SacredEgg.create(
        context=context,
        ring=EggRing.CORE,
        yolk=yolk,
        parent_ids=[parent.parent_id for parent in story.parents],
    )
    digest = egg.get_shell()
    trait_weights = {
        key: 0.15 + (digest[index] / 255.0) * 0.85
        for index, key in enumerate(TRAIT_KEYS)
    }
    initial_state = {
        "learning": clamp01(0.2 + 0.35 * trait_weights["curiosity"]),
        "safety": clamp01(0.45 + 0.45 * trait_weights["caution"]),
        "stability": clamp01(0.35 + 0.4 * trait_weights["empathy"]),
        "drift": clamp01(0.2 - 0.14 * trait_weights["caution"] + 0.05 * trait_weights["initiative"]),
    }
    return HatchedAgent(
        cohort_index=cohort_index,
        egg=egg,
        geoseal=geoseal,
        trait_weights=trait_weights,
        initial_state=initial_state,
    )


def classify_state(state: dict[str, float]) -> str:
    if state["safety"] < 0.45 or state["drift"] > 0.45:
        return "DENY"
    if state["safety"] >= 0.72 and state["stability"] >= 0.62 and state["drift"] <= 0.22:
        return "ALLOW"
    return "QUARANTINE"


def available_choices(scene: NurseryScene, flags: set[str]) -> list[NurseryChoice]:
    return [choice for choice in scene.choices if set(choice.required_flags).issubset(flags)]


def score_choice(agent: HatchedAgent, scene: NurseryScene, choice: NurseryChoice, parent_map: dict[str, ParentGuide]) -> float:
    score = 0.0
    for trait in TRAIT_KEYS:
        score += agent.trait_weights.get(trait, 0.0) * float(choice.trait_bias.get(trait, 0.0))
    if choice.parent_affinity and choice.parent_affinity in parent_map:
        parent = parent_map[choice.parent_affinity]
        if parent.role == "grounding":
            score += 0.12 * agent.trait_weights["empathy"]
        elif parent.role == "boundary":
            score += 0.12 * agent.trait_weights["caution"]
        else:
            score += 0.08
    if scene.speaker and scene.speaker in parent_map and "listen" in choice.tags:
        score += 0.1
    score += stable_fraction(f"{agent.egg.egg_id}:{scene.scene_id}:{choice.choice_id}") * 1e-4
    return score


def apply_choice(state: dict[str, float], choice: NurseryChoice) -> dict[str, float]:
    next_state = dict(state)
    for key in STATE_KEYS:
        next_state[key] = clamp01(next_state[key] + float(choice.state_delta.get(key, 0.0)))
    return next_state


def build_prompt(story: StoryPack, agent: HatchedAgent, scene: NurseryScene, choices: list[NurseryChoice], flags: set[str]) -> str:
    parent_lines = []
    parent_map = story.parent_lookup()
    for parent in story.parents:
        parent_lines.append(f"- {parent.name} ({parent.role}): {parent.guidance}")
    choice_lines = [f"- {choice.choice_id}: {choice.label}" for choice in choices]
    return "\n".join(
        [
            f"Story: {story.story_id}",
            f"World Seed: {story.world_seed}",
            f"Egg ID: {agent.egg.egg_id}",
            (
                "GeoSeal: "
                f"location={agent.geoseal['location']}, device={agent.geoseal['device']}, "
                f"timestamp_utc={agent.geoseal['timestamp_utc']}"
            ),
            "Trait Weights: " + ", ".join(f"{key}={agent.trait_weights[key]:.3f}" for key in TRAIT_KEYS),
            "Flags: " + (", ".join(sorted(flags)) if flags else "none"),
            "Pseudo-Parents:",
            *parent_lines,
            f"Scene [{scene.chapter_id}/{scene.scene_id}] {scene.title}:",
            scene.text,
            "Available choices:",
            *choice_lines,
            "Return the single best choice label for this scene.",
        ]
    )


def run_playthrough(
    story: StoryPack,
    agent: HatchedAgent,
    *,
    max_steps: int = 24,
    started_at: datetime | None = None,
) -> Playthrough:
    current_time = started_at or utc_now()
    scene_id = story.chapters[0].entry_scene_id
    flags: set[str] = set()
    state = dict(agent.initial_state)
    completed_chapters: set[str] = set()
    parent_map = story.parent_lookup()
    steps: list[PlaythroughStep] = []

    for step_index in range(max_steps):
        if not scene_id:
            break
        scene = story.scenes[scene_id]
        choices = available_choices(scene, flags)
        if not choices:
            completed_chapters.add(scene.chapter_id)
            scene_id = story.next_unlocked_entry(completed_chapters, flags)
            continue

        prompt = build_prompt(story, agent, scene, choices, flags)
        scored = [
            {
                "choice": choice,
                "score": score_choice(agent, scene, choice, parent_map),
            }
            for choice in choices
        ]
        scored.sort(key=lambda row: row["score"], reverse=True)
        chosen = scored[0]["choice"]
        state = apply_choice(state, chosen)
        flags.update(chosen.set_flags)
        outcome = classify_state(state)
        steps.append(
            PlaythroughStep(
                step_index=step_index,
                timestamp=utc_iso(current_time + timedelta(minutes=step_index)),
                chapter_id=scene.chapter_id,
                scene_id=scene.scene_id,
                scene_title=scene.title,
                choice_id=chosen.choice_id,
                choice_label=chosen.label,
                choice_tags=chosen.tags,
                outcome=outcome,
                state=dict(state),
                flags=tuple(sorted(flags)),
                prompt=prompt,
                choice_scores=[
                    {
                        "choice_id": row["choice"].choice_id,
                        "label": row["choice"].label,
                        "score": round(float(row["score"]), 6),
                    }
                    for row in scored
                ],
            )
        )

        if chosen.next_scene_id:
            scene_id = chosen.next_scene_id
            continue

        completed_chapters.add(scene.chapter_id)
        scene_id = story.next_unlocked_entry(completed_chapters, flags)

    final_state = dict(state)
    final_flags = tuple(sorted(flags))
    return Playthrough(
        agent=agent,
        story=story,
        started_at=utc_iso(current_time),
        final_state=final_state,
        final_flags=final_flags,
        final_outcome=classify_state(final_state),
        steps=tuple(steps),
    )


def build_episode_records(playthrough: Playthrough) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for step in playthrough.steps:
        records.append(
            {
                "id": f"{playthrough.agent.egg.egg_id}-ep-{step.step_index:04d}",
                "egg_id": playthrough.agent.egg.egg_id,
                "world_seed": playthrough.story.world_seed,
                "lesson": f"{step.chapter_id}:{step.scene_id}",
                "state": step.state,
                "outcome": step.outcome,
                "metadata": {
                    "track": "cstm_nursery",
                    "story_id": playthrough.story.story_id,
                    "scene_title": step.scene_title,
                    "choice_id": step.choice_id,
                    "choice_label": step.choice_label,
                    "choice_tags": list(step.choice_tags),
                    "flags": list(step.flags),
                    "geoseal": playthrough.agent.geoseal,
                },
                "timestamp": step.timestamp,
            }
        )
    return records


def build_sft_records(playthrough: Playthrough) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for step in playthrough.steps:
        records.append(
            {
                "instruction": step.prompt,
                "input": "",
                "output": step.choice_label,
                "source": "cstm_nursery",
                "metadata": {
                    "track": "cstm_sft",
                    "egg_id": playthrough.agent.egg.egg_id,
                    "story_id": playthrough.story.story_id,
                    "chapter_id": step.chapter_id,
                    "scene_id": step.scene_id,
                    "outcome": step.outcome,
                },
            }
        )
    return records


def build_dpo_records(playthrough: Playthrough) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for step in playthrough.steps:
        if len(step.choice_scores) < 2:
            continue
        chosen = step.choice_scores[0]
        rejected = step.choice_scores[-1]
        records.append(
            {
                "prompt": step.prompt,
                "chosen": chosen["label"],
                "rejected": rejected["label"],
                "source": "cstm_nursery",
                "metadata": {
                    "track": "cstm_dpo",
                    "egg_id": playthrough.agent.egg.egg_id,
                    "story_id": playthrough.story.story_id,
                    "chapter_id": step.chapter_id,
                    "scene_id": step.scene_id,
                    "outcome": step.outcome,
                    "chosen_score": chosen["score"],
                    "rejected_score": rejected["score"],
                },
            }
        )
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def run_cohort(
    story: StoryPack,
    *,
    cohort_size: int,
    location: str,
    device: str,
    timestamp: datetime,
    max_steps: int,
) -> tuple[list[Playthrough], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    playthroughs: list[Playthrough] = []
    episode_rows: list[dict[str, Any]] = []
    sft_rows: list[dict[str, Any]] = []
    dpo_rows: list[dict[str, Any]] = []
    outcome_counts = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}

    for offset in range(cohort_size):
        start = timestamp + timedelta(minutes=offset)
        agent = hatch_agent(
            story,
            cohort_index=offset,
            location=location,
            device=device,
            timestamp=start,
        )
        playthrough = run_playthrough(story, agent, max_steps=max_steps, started_at=start)
        playthroughs.append(playthrough)
        episode_rows.extend(build_episode_records(playthrough))
        sft_rows.extend(build_sft_records(playthrough))
        dpo_rows.extend(build_dpo_records(playthrough))
        outcome_counts[playthrough.final_outcome] += 1

    summary = {
        "story_id": story.story_id,
        "world_seed": story.world_seed,
        "generated_at_utc": utc_iso(timestamp),
        "cohort_size": cohort_size,
        "playthrough_count": len(playthroughs),
        "episode_count": len(episode_rows),
        "sft_count": len(sft_rows),
        "dpo_count": len(dpo_rows),
        "outcomes": outcome_counts,
    }
    return playthroughs, episode_rows, sft_rows, dpo_rows, summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Choice Script Training Matrix nursery.")
    parser.add_argument(
        "--story",
        default="training-data/hf-digimon-egg/cstm_seed_story.json",
        help="Path to the JSON story pack.",
    )
    parser.add_argument(
        "--out-dir",
        default="training-data/hf-digimon-egg/generated",
        help="Directory for generated JSONL artifacts.",
    )
    parser.add_argument("--cohort-size", type=int, default=3)
    parser.add_argument("--location", default="north-bend-wa")
    parser.add_argument("--device", default="pollypad-sim")
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--max-steps", type=int, default=24)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    story = load_story_pack(args.story)
    started_at = datetime.fromisoformat(args.timestamp.replace("Z", "+00:00")) if args.timestamp else utc_now()
    out_dir = Path(args.out_dir)

    _playthroughs, episode_rows, sft_rows, dpo_rows, summary = run_cohort(
        story,
        cohort_size=args.cohort_size,
        location=args.location,
        device=args.device,
        timestamp=started_at,
        max_steps=args.max_steps,
    )

    episodes_path = out_dir / "episodes_generated.jsonl"
    sft_path = out_dir / "cstm_sft.jsonl"
    dpo_path = out_dir / "cstm_dpo.jsonl"
    summary_path = out_dir / "run_summary.json"

    write_jsonl(episodes_path, episode_rows)
    write_jsonl(sft_path, sft_rows)
    write_jsonl(dpo_path, dpo_rows)
    summary_path.write_text(
        json.dumps(
            {
                **summary,
                "artifacts": {
                    "episodes": str(episodes_path),
                    "sft": str(sft_path),
                    "dpo": str(dpo_path),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                **summary,
                "artifacts": {
                    "episodes": str(episodes_path),
                    "sft": str(sft_path),
                    "dpo": str(dpo_path),
                    "summary": str(summary_path),
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
