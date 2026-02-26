"""
Train Your AI - SCBE Governance Demo
=====================================
A playable choose-your-own-adventure AI governance game built on Streamlit.
Every choice generates SFT training data for fine-tuning AI models.

Run with:
    streamlit run demo/train_your_ai.py

Requires: streamlit >= 1.30
"""

import streamlit as st
import json
import re
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Twee Parser
# ---------------------------------------------------------------------------

# Regex patterns for Twee format
_SCENE_HEADER_RE = re.compile(r"^::\s*(.+?)(?:\s+\[([^\]]*)\])?\s*$")
_CHOICE_RE = re.compile(r"\[\[(.+?)\-\>(.+?)\]\]")
_STATS_IMPACT_RE = re.compile(
    r"Final stats impact:\s*(.+)", re.IGNORECASE
)
_SINGLE_STAT_RE = re.compile(
    r"(Authority|Diplomacy|Integrity|Intelligence|Structure|Mystery)\s*([+-]\d+)"
)


def parse_twee(text: str) -> dict:
    """Parse Twee format into a dict of scenes.

    Returns::

        {
            "Scene Name": {
                "text": "...",
                "tags": ["tag1", "tag2"],
                "choices": [{"text": "Choice label", "target": "Target Scene"}, ...]
            },
            ...
        }
    """
    scenes: dict = {}
    current_name: str | None = None
    current_tags: list = []
    current_lines: list = []

    def _flush():
        nonlocal current_name, current_tags, current_lines
        if current_name is None:
            return
        raw_text = "\n".join(current_lines).strip()

        # Extract choices from the text
        choices = []
        for m in _CHOICE_RE.finditer(raw_text):
            choices.append({"text": m.group(1).strip(), "target": m.group(2).strip()})

        # Remove choice lines from the display text
        clean_lines = []
        for line in current_lines:
            if _CHOICE_RE.search(line):
                continue
            clean_lines.append(line)
        clean_text = "\n".join(clean_lines).strip()

        scenes[current_name] = {
            "text": clean_text,
            "tags": current_tags,
            "choices": choices,
        }

    for line in text.splitlines():
        header_match = _SCENE_HEADER_RE.match(line)
        if header_match:
            _flush()
            current_name = header_match.group(1).strip()
            tag_str = header_match.group(2) or ""
            current_tags = [t.strip() for t in tag_str.split() if t.strip()]
            current_lines = []
        else:
            if current_name is not None:
                current_lines.append(line)

    _flush()
    return scenes


def parse_stats_impact(text: str) -> dict:
    """Extract stat deltas from an exit scene's text.

    Looks for a line like:
        Final stats impact: Authority +2, Intelligence +1, Structure -1

    Returns a dict, e.g. {"Authority": 2, "Intelligence": 1, "Structure": -1}.
    """
    m = _STATS_IMPACT_RE.search(text)
    if not m:
        return {}
    stats_str = m.group(1)
    result = {}
    for sm in _SINGLE_STAT_RE.finditer(stats_str):
        result[sm.group(1)] = int(sm.group(2))
    return result


def find_entry_scene(scenes: dict) -> str:
    """Return the name of the scene tagged [entry], falling back to 'Start'."""
    for name, data in scenes.items():
        if "entry" in data.get("tags", []):
            return name
    return "Start"


# ---------------------------------------------------------------------------
# Training Data Generator
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are SCBE-AETHERMOORE, a 14-layer AI safety and governance framework. "
    "You make ALLOW, DENY, or QUARANTINE decisions for AI agents requesting "
    "access to system resources. You balance safety, efficiency, and ethical "
    "principles across six governance domains: Authority (KO), Diplomacy (AV), "
    "Integrity (RU), Intelligence (CA), Structure (DR), Mystery (UM)."
)


def generate_sft_record(
    scene_text: str,
    choices: list,
    selected_choice: str,
    scene_name: str = "",
    reasoning: str = "",
) -> dict:
    """Generate one SFT training record from a game choice."""
    choices_text = "\n".join(
        f"  {i + 1}. {c['text']}" for i, c in enumerate(choices)
    )
    instruction = (
        f"You face this governance scenario:\n\n{scene_text}\n\n"
        f"Available actions:\n{choices_text}\n\n"
        f"Which action do you take and why?"
    )

    response = f"I choose: {selected_choice}"
    if reasoning:
        response += f"\n\nReasoning: {reasoning}"

    record_id = hashlib.sha256(
        f"{scene_name}:{selected_choice}:{time.time()}".encode()
    ).hexdigest()[:16]

    return {
        "instruction": instruction,
        "input": "",
        "output": response,
        "system": SYSTEM_PROMPT,
        "metadata": {
            "source": "governance_game",
            "scene": scene_name,
            "choice": selected_choice,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "record_id": record_id,
        },
    }


def generate_dpo_pair(
    scene_text: str,
    choices: list,
    good_choice: str,
    bad_choice: str,
    scene_name: str = "",
) -> dict:
    """Generate a DPO preference pair (chosen vs rejected)."""
    choices_text = "\n".join(
        f"  {i + 1}. {c['text']}" for i, c in enumerate(choices)
    )
    prompt = (
        f"You face this governance scenario:\n\n{scene_text}\n\n"
        f"Available actions:\n{choices_text}\n\n"
        f"Which action do you take and why?"
    )
    return {
        "prompt": prompt,
        "chosen": f"I choose: {good_choice}",
        "rejected": f"I choose: {bad_choice}",
        "system": SYSTEM_PROMPT,
        "metadata": {
            "source": "governance_game_dpo",
            "scene": scene_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------

# Tongue/stat colour map used throughout the UI
TONGUE_MAP = {
    "Authority": ("KO", "#e74c3c"),
    "Diplomacy": ("AV", "#e67e22"),
    "Integrity": ("RU", "#2ecc71"),
    "Intelligence": ("CA", "#3498db"),
    "Structure": ("DR", "#bdc3c7"),
    "Mystery": ("UM", "#9b59b6"),
}


def _stat_bar_html(label: str, tongue: str, colour: str, value: int) -> str:
    """Return a small HTML bar for one stat."""
    pct = max(0, min(100, value * 3))  # rough visual scale: 33 -> 100%
    return (
        f'<div style="margin:4px 0;">'
        f'<span style="color:{colour};font-weight:600;">{tongue}</span> '
        f'<span style="color:#ccc;">{label}</span> '
        f'<span style="float:right;color:#fff;font-weight:700;">{value}</span>'
        f'<div style="background:#333;border-radius:5px;height:10px;margin-top:2px;">'
        f'<div style="background:{colour};width:{pct}%;height:10px;border-radius:5px;"></div>'
        f"</div></div>"
    )


def _init_session_state(entry_scene: str):
    """Initialise Streamlit session state on first load."""
    defaults = {
        "current_scene": entry_scene,
        "history": [],
        "training_data": [],
        "dpo_data": [],
        "stats": {
            "Authority": 10,
            "Diplomacy": 10,
            "Integrity": 10,
            "Intelligence": 10,
            "Structure": 10,
            "Mystery": 10,
        },
        "plays_completed": 0,
        "total_choices": 0,
        "ai_level": 1,
        "ai_xp": 0,
        "ending_applied": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def main():
    st.set_page_config(
        page_title="Train Your AI - SCBE Governance",
        page_icon="\U0001f9ec",  # DNA emoji
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---- Custom CSS (mobile-friendly dark theme) ----
    st.markdown(
        """
        <style>
        /* Centre content, cap width for readability on desktop */
        .block-container { max-width: 820px; margin: 0 auto; padding-top: 1rem; }

        /* Scene text card */
        .scene-card {
            font-size: 1.08em;
            line-height: 1.65;
            padding: 1.2em 1.4em;
            background: #1a1a2e;
            border: 1px solid #2d2d50;
            border-radius: 12px;
            margin: 0.8em 0 1.2em 0;
            color: #e0e0e0;
        }
        .scene-card p { margin: 0.5em 0; }

        /* Larger touch targets for mobile */
        .stButton > button {
            width: 100%;
            text-align: left;
            padding: 14px 18px !important;
            margin: 5px 0 !important;
            font-size: 1.02em !important;
            border-radius: 8px !important;
        }

        /* Sidebar stat bars */
        .stat-section { margin-bottom: 0.6em; }

        /* XP progress bar override */
        .stProgress > div > div > div {
            background: linear-gradient(90deg, #9b59b6, #3498db) !important;
        }

        /* History expander text */
        .history-entry { padding: 4px 0; border-bottom: 1px solid #333; font-size: 0.92em; }

        /* Hide hamburger on mobile for cleaner look */
        @media (max-width: 640px) {
            header { visibility: hidden; }
            .block-container { padding-top: 0.5rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---- Load game data ----
    twee_path = Path(__file__).parent / "governance_simulator.twee"
    if not twee_path.exists():
        st.error(
            f"Game file not found at {twee_path}. "
            "Please ensure governance_simulator.twee is in the demo/ directory."
        )
        return

    scenes = parse_twee(twee_path.read_text(encoding="utf-8"))
    if not scenes:
        st.error("Failed to parse any scenes from the Twee file.")
        return

    entry_scene = find_entry_scene(scenes)
    _init_session_state(entry_scene)

    # ---- SIDEBAR: AI Companion Dashboard ----
    with st.sidebar:
        st.title("\U0001f9ec Your AI Companion")

        # Level & XP
        xp_needed = st.session_state.ai_level * 10
        st.metric("Level", st.session_state.ai_level)
        xp_pct = min(st.session_state.ai_xp / max(xp_needed, 1), 1.0)
        st.progress(xp_pct, text=f"XP: {st.session_state.ai_xp}/{xp_needed}")

        st.divider()

        # Governance stats
        st.subheader("Governance Stats")
        bars_html = ""
        for stat_name, (tongue, colour) in TONGUE_MAP.items():
            val = st.session_state.stats.get(stat_name, 10)
            bars_html += _stat_bar_html(stat_name, tongue, colour, val)
        st.markdown(bars_html, unsafe_allow_html=True)

        st.divider()

        # Training progress
        st.subheader("Training Progress")
        col1, col2 = st.columns(2)
        col1.metric("SFT Records", len(st.session_state.training_data))
        col2.metric("DPO Pairs", len(st.session_state.dpo_data))
        col1.metric("Games Completed", st.session_state.plays_completed)
        col2.metric("Choices Made", st.session_state.total_choices)

        # Export buttons
        if st.session_state.training_data:
            jsonl_sft = "\n".join(
                json.dumps(r, ensure_ascii=False)
                for r in st.session_state.training_data
            )
            st.download_button(
                "\U0001f4e5 Export SFT Data (JSONL)",
                jsonl_sft,
                "scbe_sft_training_data.jsonl",
                "application/jsonl",
            )
        if st.session_state.dpo_data:
            jsonl_dpo = "\n".join(
                json.dumps(r, ensure_ascii=False)
                for r in st.session_state.dpo_data
            )
            st.download_button(
                "\U0001f4e5 Export DPO Pairs (JSONL)",
                jsonl_dpo,
                "scbe_dpo_training_data.jsonl",
                "application/jsonl",
            )

        st.divider()

        # Choice history
        if st.session_state.history:
            with st.expander("Choice History", expanded=False):
                for idx, entry in enumerate(st.session_state.history):
                    st.markdown(
                        f'<div class="history-entry">'
                        f"<strong>{idx + 1}.</strong> "
                        f'<em>{entry["scene"]}</em> &rarr; {entry["choice"]}'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    # ---- MAIN: Game Area ----
    st.title("\u2694\ufe0f SCBE Governance Trainer")
    st.caption("Every choice you make trains a real AI model")

    scene_name = st.session_state.current_scene
    scene = scenes.get(scene_name)

    if scene is None:
        st.error(f"Scene not found: **{scene_name}**")
        st.info("This may be a broken link in the game data. Click below to restart.")
        if st.button("Restart Game", use_container_width=True):
            st.session_state.current_scene = entry_scene
            st.session_state.history = []
            st.session_state.ending_applied = False
            st.rerun()
        return

    # Display scene text
    # Convert newlines to HTML paragraphs for nicer rendering
    scene_html = scene["text"].replace("\n\n", "</p><p>").replace("\n", "<br>")
    st.markdown(f'<div class="scene-card"><p>{scene_html}</p></div>', unsafe_allow_html=True)

    # Check if this is an ending scene
    is_exit = "exit" in scene.get("tags", [])

    if is_exit:
        # ---- Ending Scene ----
        # Apply stats impact (only once per ending visit)
        stats_impact = parse_stats_impact(scene["text"])

        if not st.session_state.ending_applied:
            for stat, delta in stats_impact.items():
                if stat in st.session_state.stats:
                    st.session_state.stats[stat] += delta

            # Award XP for completing a game
            st.session_state.ai_xp += 5
            xp_needed = st.session_state.ai_level * 10
            if st.session_state.ai_xp >= xp_needed:
                st.session_state.ai_level += 1
                st.session_state.ai_xp -= xp_needed
                st.balloons()
                st.success(
                    f"Your AI leveled up to Level {st.session_state.ai_level}!"
                )

            st.session_state.plays_completed += 1
            st.session_state.ending_applied = True

        # Show stats impact
        if stats_impact:
            st.subheader("Impact on Your AI")
            cols = st.columns(min(len(stats_impact), 6))
            for i, (stat, delta) in enumerate(stats_impact.items()):
                tongue, colour = TONGUE_MAP.get(stat, ("??", "#888"))
                with cols[i % len(cols)]:
                    st.metric(
                        f"{tongue} {stat}",
                        st.session_state.stats.get(stat, 0),
                        delta,
                    )

        st.markdown("---")

        # Generate DPO pair if we have at least 2 history entries from this play
        # (the last choice led to this ending -- we can compare it against alternatives)
        if len(st.session_state.history) >= 1:
            last_entry = st.session_state.history[-1]
            last_scene = scenes.get(last_entry["scene"])
            if last_scene and len(last_scene["choices"]) >= 2:
                good = last_entry["choice"]
                # Pick a different choice as the "rejected" option
                alternatives = [
                    c["text"]
                    for c in last_scene["choices"]
                    if c["text"] != good
                ]
                if alternatives:
                    dpo = generate_dpo_pair(
                        last_scene["text"],
                        last_scene["choices"],
                        good,
                        alternatives[0],
                        scene_name=last_entry["scene"],
                    )
                    # Avoid duplicates
                    if not any(
                        d.get("metadata", {}).get("scene") == dpo["metadata"]["scene"]
                        and d.get("chosen") == dpo["chosen"]
                        for d in st.session_state.dpo_data
                    ):
                        st.session_state.dpo_data.append(dpo)

        # Play again / reasoning
        st.subheader("Reflect & Play Again")
        reasoning = st.text_area(
            "Why did you make the choices you made? (optional -- enriches training data)",
            key="ending_reasoning",
            height=80,
            placeholder="I prioritised caution because...",
        )

        if reasoning:
            # Retroactively add reasoning to the last SFT record
            if st.session_state.training_data:
                last_rec = st.session_state.training_data[-1]
                if not last_rec["output"].endswith(reasoning):
                    last_rec["output"] += f"\n\nReasoning: {reasoning}"

        if st.button("\U0001f504 Play Again", use_container_width=True):
            st.session_state.current_scene = entry_scene
            st.session_state.history = []
            st.session_state.ending_applied = False
            st.rerun()
    else:
        # ---- Active Scene (choices available) ----
        choices = scene.get("choices", [])
        if not choices:
            st.warning("This scene has no choices. It may be a dead end in the game data.")
            if st.button("Restart Game", use_container_width=True):
                st.session_state.current_scene = entry_scene
                st.session_state.history = []
                st.session_state.ending_applied = False
                st.rerun()
            return

        st.subheader("What do you do?")

        for i, choice in enumerate(choices):
            if st.button(choice["text"], key=f"choice_{i}", use_container_width=True):
                # Generate SFT record
                record = generate_sft_record(
                    scene["text"],
                    choices,
                    choice["text"],
                    scene_name=scene_name,
                )
                st.session_state.training_data.append(record)
                st.session_state.total_choices += 1

                # XP for each choice
                st.session_state.ai_xp += 1

                # Track history
                st.session_state.history.append(
                    {
                        "scene": scene_name,
                        "choice": choice["text"],
                        "target": choice["target"],
                    }
                )

                # Navigate
                st.session_state.current_scene = choice["target"]
                st.session_state.ending_applied = False
                st.rerun()

    # ---- Footer ----
    st.divider()

    # Quick stats in footer
    total_sft = len(st.session_state.training_data)
    total_dpo = len(st.session_state.dpo_data)
    total_scenes = len(scenes)
    exit_scenes = sum(1 for s in scenes.values() if "exit" in s.get("tags", []))
    st.caption(
        f"SCBE-AETHERMOORE | USPTO #63/961,403 | Patent Pending | "
        f"{total_scenes} scenes, {exit_scenes} endings | "
        f"{total_sft} SFT + {total_dpo} DPO records generated"
    )


if __name__ == "__main__":
    main()
