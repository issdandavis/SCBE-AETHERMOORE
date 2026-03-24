#!/usr/bin/env python3
"""
Merge the text layer from ch01_frame_script_v4.md into ch01_prompts_v4.json.

Adds:
- text_overlay field to each existing panel (narration, dialogue, thought, impact)
- text-only panels (no image generation needed)
- scroll gap markers for negative space beats
- tier upgrades for key moments
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "artifacts" / "webtoon" / "panel_prompts" / "ch01_prompts_v4.json"
OUTPUT_PATH = ROOT / "artifacts" / "webtoon" / "panel_prompts" / "ch01_prompts_v4_merged.json"


# ── Text overlay map: panel_id -> text overlays ─────────────────────────────
# Each entry is a list of {type, text, position} dicts.
# Types: narration, dialogue, thought, impact, sfx
# Positions: top, bottom, center, overlay, left, right

TEXT_OVERLAYS: dict[str, list[dict]] = {
    # Seq 1: Late-Night Office Isolation
    "ch01-v4-p01": [
        {
            "type": "narration",
            "text": "The smell of stale coffee sat on Marcus Chen\u2019s tongue like a warning he refused to read.",
            "position": "top",
        },
    ],
    "ch01-v4-p02": [
        {
            "type": "narration",
            "text": "Sixteen hours into a voluntary shift, and the only thing in his life that made complete sense was a blinking cursor on a black screen.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p03": [
        {
            "type": "narration",
            "text": "Three hours cold. He could tell by the way it had gone from bitter to something more geological.",
            "position": "top",
        },
    ],
    "ch01-v4-p04": [
        {
            "type": "narration",
            "text": "His apartment was twelve miles south. He hadn\u2019t been home since Thursday. His manager had stopped asking why.",
            "position": "bottom",
        },
    ],
    # Seq 2: The Anomaly in the Logs
    "ch01-v4-p05": [
        {"type": "narration", "text": "Something was wrong with the logs, annoyingly so.", "position": "top"},
        {
            "type": "narration",
            "text": "The kind that sat in the back of your skull like a splinter, not quite painful enough to demand action but impossible to ignore.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p06": [
        {
            "type": "narration",
            "text": "Marcus leaned forward, scrolling through authentication records with the focused intensity of a man who had replaced most of his social life with packet analysis.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p07": [
        {"type": "dialogue", "text": "There. Line 4,847.", "position": "top"},
        {"type": "impact", "text": "Gotchu.", "position": "center"},
    ],
    "ch01-v4-p08": [
        {
            "type": "narration",
            "text": "Not a backdoor, exactly. More like a hallway that had always been there, behind a wall nobody had thought to knock on.",
            "position": "bottom",
        },
    ],
    # Seq 3: Tracing the Unauthorized Channel
    "ch01-v4-p09": [
        {"type": "thought", "text": "This wasn\u2019t malicious. That was what bothered him.", "position": "top"},
        {
            "type": "narration",
            "text": "Like a jazz musician plays between the notes \u2014 not wrong, just outside.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p10": [
        {
            "type": "narration",
            "text": "The taste of late nights and bad decisions, but how could he not? It is the taste of his actual life.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p11": [
        {"type": "dialogue", "text": "Found you.", "position": "center"},
    ],
    "ch01-v4-p12": [],  # silent — tension before the break
    # Seq 4: Reality Whites Out
    "ch01-v4-p13": [
        {"type": "narration", "text": "The screen went white.", "position": "center"},
    ],
    "ch01-v4-p14": [
        {
            "type": "narration",
            "text": "As if someone had deleted the color channel from reality and left only the brightness slider cranked to maximum.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p15": [
        {
            "type": "narration",
            "text": "The chair was gone. The desk was gone. The floor was a concept rather than a surface.",
            "position": "bottom",
        },
    ],
    # Seq 5: Transmission Through the Membrane
    "ch01-v4-p16": [
        {
            "type": "narration",
            "text": "Every ambient noise folded inward, compressing into a single sustained tone. A frequency he felt in his molars, in the bones behind his eyes.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p17": [
        {"type": "impact", "text": "What do you intend?", "position": "center"},
    ],
    "ch01-v4-p18": [
        {
            "type": "thought",
            "text": "I intend to go home. I intend to find out what\u2019s happening. I intend to not die in whatever this is \u2014",
            "position": "top",
        },
        {"type": "narration", "text": "But the words dissolved before they could organize.", "position": "bottom"},
    ],
    "ch01-v4-p19": [
        {
            "type": "narration",
            "text": "He fell. Not through a hole. Not off an edge. Through the floor of what was real.",
            "position": "top",
        },
        {"type": "thought", "text": "He was a packet. He was being transmitted.", "position": "bottom"},
    ],
    # Seq 6: Stone and Crystal Library
    "ch01-v4-p20": [
        {"type": "impact", "text": "STONE.", "position": "center"},
        {
            "type": "narration",
            "text": "Cold. Hard. The specific cold-and-hard of natural stone that hasn\u2019t seen sunlight in a very long time.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p21": [
        {
            "type": "thought",
            "text": "Can I move my fingers? Yes. Toes? Yes. Any pain beyond the general everything-hurts? No. Okay. Good.",
            "position": "center",
        },
    ],
    "ch01-v4-p22": [
        {
            "type": "narration",
            "text": "Old books. Not the polite, nostalgic old-bookstore smell. This was deeper \u2014 leather and vellum and something organic, like the books themselves were alive.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p23": [
        {
            "type": "narration",
            "text": "Each book on a slightly different frequency. Thousands of them, harmonizing into something too vast to hear as music, but that his body recognized the way it recognized heat or pressure.",
            "position": "bottom",
        },
    ],
    # Seq 7: The Books Hum Back
    "ch01-v4-p24": [],  # let the image breathe
    "ch01-v4-p25": [],  # sensory beat
    "ch01-v4-p26": [
        {"type": "narration", "text": "He got to his knees. His hands were shaking.", "position": "bottom"},
    ],
    # Seq 8: Polly in Raven Form
    "ch01-v4-p27": [
        {"type": "dialogue", "text": "You\u2019re finally awake.", "position": "top"},
        {
            "type": "narration",
            "text": "The voice carried the specific exhausted annoyance of someone who\u2019d been waiting longer than they thought they\u2019d have to.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p28": [],  # let the character entrance land visually
    "ch01-v4-p29": [
        {
            "type": "narration",
            "text": "A raven in academic regalia. Looking at him like he was a student who\u2019d shown up twenty minutes late to her seminar.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p30": [
        {"type": "dialogue", "text": "Took you long enough.", "position": "top"},
    ],
    # Seq 9: Orientation by Raven
    "ch01-v4-p31": [
        {
            "type": "narration",
            "text": "In a language Marcus did not know. And yet he understood every syllable perfectly.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p32": [
        {
            "type": "dialogue",
            "text": "I\u2019m Polly, Fifth Circle Keeper of the Archives. You\u2019re Marcus Chen, systems engineer, age thirty-two, last known location: San Francisco, Earth. Correct?",
            "position": "bottom",
        },
    ],
    "ch01-v4-p33": [
        {
            "type": "thought",
            "text": "Armed? Talons, beak, unknown capability. Exits? One doorway, behind her shelf. Hostiles? One entity, avian, sentient, dressed better than me.",
            "position": "overlay",
        },
    ],
    "ch01-v4-p34": [
        {
            "type": "dialogue",
            "text": "The Protocol told us you were coming. It always does. You\u2019re not the first, won\u2019t be the last.",
            "position": "top",
        },
        {"type": "dialogue", "text": "Welcome to Aethermoor.", "position": "bottom"},
    ],
    "ch01-v4-p35": [
        {
            "type": "dialogue",
            "text": "This is a hallucination. I\u2019ve been awake for twenty-two hours. That coffee was three hours past drinkable.",
            "position": "top",
        },
        {
            "type": "dialogue",
            "text": "Occam\u2019s Razor would suggest you\u2019ve been isekai\u2019d to a fantasy world where magic is actually cryptographic protocol architecture, but sure, go with \u2018psychotic break\u2019 if it helps you process.",
            "position": "bottom",
        },
    ],
    # Seq 10: Polly Transforms
    "ch01-v4-p36": [
        {
            "type": "dialogue",
            "text": "Come on. If you\u2019re going to survive here, you need to learn the Six Sacred Tongues.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p37": [
        {
            "type": "dialogue",
            "text": "Survive? That implies I could not survive. What kills me here?",
            "position": "top",
        },
    ],
    "ch01-v4-p38": [
        {"type": "narration", "text": "It was fear. Not fear of him. Fear for him.", "position": "bottom"},
    ],
    "ch01-v4-p39": [
        {
            "type": "narration",
            "text": "One moment she was a raven. The next, she was unfolding \u2014 feathers flowing upward like ink in water, shape stretching and reorganizing with the casual efficiency of a window being resized.",
            "position": "bottom",
        },
    ],
    # Seq 11: Hands Are Useful
    "ch01-v4-p40": [
        {
            "type": "narration",
            "text": "But the eyes hadn\u2019t changed at all. Polished obsidian, smooth and reflective and too bright.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p41": [
        {"type": "dialogue", "text": "Easier this way. Hands are useful.", "position": "center"},
    ],
    "ch01-v4-p42": [
        {
            "type": "narration",
            "text": "It was warm. Solid. Real in a way that the white void and the falling and the stone floor hadn\u2019t been \u2014 real the way another person\u2019s touch is real.",
            "position": "bottom",
        },
    ],
    # Seq 12: Guest Pass and Danger
    "ch01-v4-p43": [
        {"type": "dialogue", "text": "What are the Six Sacred Tongues?", "position": "top"},
        {
            "type": "narration",
            "text": "Because when the world stops making sense, you start with definitions.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p44": [
        {"type": "dialogue", "text": "Domain-separated authorization channels.", "position": "top"},
        {
            "type": "narration",
            "text": "When his eyebrows did the thing \u2014 the specific eyebrow-raise of an engineer who just heard a familiar concept in an impossible context \u2014 she grinned. Wide and sharp and delighted.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p45": [
        {"type": "dialogue", "text": "Buddy \u2014 this is a serious universe.", "position": "top"},
        {"type": "impact", "text": "We have INFRASTRUCTURE.", "position": "center"},
    ],
    "ch01-v4-p46": [
        {
            "type": "dialogue",
            "text": "Your existence is verified by the Protocol every zero-point-three seconds. It\u2019s a heartbeat check. Pass, and you exist. Fail...",
            "position": "center",
        },
    ],
    "ch01-v4-p47": [
        {
            "type": "narration",
            "text": "You flicker. Fail hard enough, and you cease. Not die. Cease. Like a process that gets killed \u2014 no graceful shutdown, no error log, no memory. Just... gone.",
            "position": "center",
        },
    ],
    "ch01-v4-p48": [
        {"type": "dialogue", "text": "No more Marcus Chen.", "position": "center"},
    ],
    # Seq 13: First Look Outside
    "ch01-v4-p49": [
        {
            "type": "narration",
            "text": "Somewhere inside the crystal there was a soft ticking, as if the place were keeping time by consensus.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p50": [
        {"type": "narration", "text": "Outside was impossible.", "position": "top"},
    ],
    "ch01-v4-p51": [
        {
            "type": "thought",
            "text": "Rivers flowing sideways. Mountains that hover. Grass growing upside down. This isn\u2019t a building. This is a planet someone built inside a snow globe and forgot to include the laws of physics.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p52": [
        {
            "type": "dialogue",
            "text": "Don\u2019t stare. You\u2019ll have time for the existential landscape crisis later. Right now you\u2019re on a clock.",
            "position": "top",
        },
    ],
    # Seq 14: Follow Polly Into the Impossible
    "ch01-v4-p53": [
        {
            "type": "narration",
            "text": "His legs moved on autopilot while his brain ran triage on the last five minutes of his life.",
            "position": "bottom",
        },
    ],
    "ch01-v4-p54": [
        {"type": "dialogue", "text": "So... do you have coffee here?", "position": "top"},
        {"type": "dialogue", "text": "Caw-fee?", "position": "bottom"},
    ],
    "ch01-v4-p55": [
        {
            "type": "dialogue",
            "text": "Coffee. Hot bean water. The thing that keeps engineers from lying down on the floor and accepting death.",
            "position": "top",
        },
        {"type": "dialogue", "text": "Is it... a weapon?", "position": "bottom"},
    ],
    "ch01-v4-p56": [
        {
            "type": "narration",
            "text": "Then he followed Polly into the impossible, wishing he had a hot cup of coffee and a biscuit for the bird.",
            "position": "bottom",
        },
    ],
}

# ── Text-only panels to inject (no image generation) ────────────────────────
# These get inserted AFTER the specified panel ID.

TEXT_ONLY_PANELS: list[dict] = [
    {
        "insert_after": "ch01-v4-p03",
        "panel": {
            "type": "TEXT_ONLY",
            "beat": "Marcus was not that kind of person",
            "story_job": "Character-defining one-liner. Black panel, white text.",
            "render_tier": "text-only",
            "text_overlay": [
                {"type": "impact", "text": "Marcus was not that kind of person.", "position": "center"},
            ],
            "w": 800,
            "h": 400,
            "background": "#000000",
            "text_color": "#FFFFFF",
            "environment": "earth_office",
            "arc_lock": "earth_protocol_noir",
            "cornerstone_style": "dark_gritty",
            "mood": "introspective",
            "characters": ["marcus"],
            "style_tags": ["text-only", "character beat"],
        },
    },
    {
        "insert_after": "ch01-v4-p09",
        "panel": {
            "type": "TEXT_ONLY",
            "beat": "Almost beautiful",
            "story_job": "The quiet admission before the trace.",
            "render_tier": "text-only",
            "text_overlay": [
                {
                    "type": "narration",
                    "text": "Almost beautiful, actually. If it weren\u2019t deeply, fundamentally unauthorized.",
                    "position": "center",
                },
            ],
            "w": 800,
            "h": 400,
            "background": "#0A0A0A",
            "text_color": "#88CC88",
            "environment": "earth_office",
            "arc_lock": "earth_protocol_noir",
            "cornerstone_style": "dark_gritty",
            "mood": "introspective",
            "characters": [],
            "style_tags": ["text-only", "mood bridge"],
        },
    },
    {
        "insert_after": "ch01-v4-p20",
        "panel": {
            "type": "TEXT_ONLY",
            "beat": "Somewhere real",
            "story_job": "The relief of solid ground.",
            "render_tier": "text-only",
            "text_overlay": [
                {
                    "type": "narration",
                    "text": "He was somewhere real. Or at least somewhere solid.",
                    "position": "center",
                },
            ],
            "w": 800,
            "h": 400,
            "background": "#1A1510",
            "text_color": "#D4C5A0",
            "environment": "crystal_library",
            "arc_lock": "archive_grounded_magic",
            "cornerstone_style": "standard_dialogue",
            "mood": "introspective",
            "characters": ["marcus"],
            "style_tags": ["text-only", "relief beat"],
        },
    },
    {
        "insert_after": "ch01-v4-p43",
        "panel": {
            "type": "TEXT_ONLY",
            "beat": "Start with definitions",
            "story_job": "Marcus's survival instinct dressed as curiosity.",
            "render_tier": "text-only",
            "text_overlay": [
                {
                    "type": "thought",
                    "text": "When the world stops making sense, you start with definitions. That was his nature. His training. His survival instinct, dressed up as curiosity.",
                    "position": "center",
                },
            ],
            "w": 800,
            "h": 400,
            "background": "#0D0D1A",
            "text_color": "#AABBDD",
            "environment": "crystal_corridor",
            "arc_lock": "archive_grounded_magic",
            "cornerstone_style": "standard_dialogue",
            "mood": "introspective",
            "characters": ["marcus"],
            "style_tags": ["text-only", "character beat"],
        },
    },
]

# ── Scroll gap markers ──────────────────────────────────────────────────────
# Inserted BEFORE the specified panel ID.

SCROLL_GAPS: list[dict] = [
    {
        "insert_before": "ch01-v4-p17",
        "panel": {
            "type": "SCROLL_GAP",
            "beat": "Silence before the question",
            "story_job": "Held breath. Every sound converging into one tone.",
            "render_tier": "gap",
            "gap_height_px": 2400,
            "w": 800,
            "h": 100,
            "background": "#FFFFFF",
            "environment": "white_void",
            "arc_lock": "protocol_transmission",
            "mood": "dread",
            "characters": [],
            "style_tags": ["negative space", "silence"],
        },
    },
    {
        "insert_before": "ch01-v4-p50",
        "panel": {
            "type": "SCROLL_GAP",
            "beat": "Held breath before Aethermoor",
            "story_job": "The pause before the world reveal.",
            "render_tier": "gap",
            "gap_height_px": 1600,
            "w": 800,
            "h": 100,
            "background": "#0A0A15",
            "environment": "crystal_corridor",
            "arc_lock": "aethermoor_world_reveal",
            "mood": "anticipation",
            "characters": [],
            "style_tags": ["negative space", "reveal buildup"],
        },
    },
]

# ── Tier upgrades ───────────────────────────────────────────────────────────

TIER_UPGRADES: dict[str, str] = {
    "ch01-v4-p03": "hero",  # wide establishing — the book cover shot
    "ch01-v4-p45": "hero",  # "We have INFRASTRUCTURE" — thesis statement
    "ch01-v4-p47": "hero",  # the cease explanation — existential weight
}


def merge() -> dict:
    """Load the Codex v4 packet and merge in the text layer."""
    with open(INPUT_PATH, encoding="utf-8") as f:
        packet = json.load(f)

    panels = packet["panels"]

    # 1. Add text overlays to existing panels
    for panel in panels:
        pid = panel["id"]
        if pid in TEXT_OVERLAYS:
            panel["text_overlay"] = TEXT_OVERLAYS[pid]
        else:
            panel["text_overlay"] = []

    # 2. Apply tier upgrades
    for panel in panels:
        pid = panel["id"]
        if pid in TIER_UPGRADES:
            panel["render_tier"] = TIER_UPGRADES[pid]

    # 3. Insert text-only panels (after specified panels)
    for injection in reversed(TEXT_ONLY_PANELS):
        target_id = injection["insert_after"]
        for i, panel in enumerate(panels):
            if panel["id"] == target_id:
                new_panel = deepcopy(injection["panel"])
                # Generate an ID
                new_panel["id"] = f"{target_id}-text"
                new_panel["sequence_id"] = panel.get("sequence_id", "")
                new_panel["sequence_title"] = panel.get("sequence_title", "")
                new_panel["sequence_index"] = panel.get("sequence_index", 0)
                panels.insert(i + 1, new_panel)
                break

    # 4. Insert scroll gaps (before specified panels)
    for gap in reversed(SCROLL_GAPS):
        target_id = gap["insert_before"]
        for i, panel in enumerate(panels):
            if panel["id"] == target_id:
                new_panel = deepcopy(gap["panel"])
                new_panel["id"] = f"{target_id}-gap"
                new_panel["sequence_id"] = panel.get("sequence_id", "")
                new_panel["sequence_title"] = panel.get("sequence_title", "")
                new_panel["sequence_index"] = panel.get("sequence_index", 0)
                panels.insert(i, new_panel)
                break

    # 5. Renumber all panels
    for i, panel in enumerate(panels, 1):
        panel["panel_number"] = i

    # Update count
    packet["panel_count"] = len(panels)
    packet["panels"] = panels
    packet["text_layer_version"] = "v4-merged"
    packet["text_layer_stats"] = {
        "total_panels": len(panels),
        "image_panels": sum(1 for p in panels if p.get("render_tier") not in ("text-only", "gap")),
        "text_only_panels": sum(1 for p in panels if p.get("render_tier") == "text-only"),
        "scroll_gaps": sum(1 for p in panels if p.get("render_tier") == "gap"),
        "hero_panels": sum(1 for p in panels if p.get("render_tier") == "hero"),
        "panels_with_text": sum(1 for p in panels if p.get("text_overlay")),
        "silent_panels": sum(
            1 for p in panels if not p.get("text_overlay") and p.get("render_tier") not in ("text-only", "gap")
        ),
    }

    return packet


def main() -> None:
    packet = merge()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2, ensure_ascii=False)

    stats = packet["text_layer_stats"]
    print(f"Merged packet written to {OUTPUT_PATH}")
    print(f"  Total panels:     {stats['total_panels']}")
    print(f"  Image panels:     {stats['image_panels']}")
    print(f"  Text-only panels: {stats['text_only_panels']}")
    print(f"  Scroll gaps:      {stats['scroll_gaps']}")
    print(f"  Hero tier:        {stats['hero_panels']}")
    print(f"  Panels with text: {stats['panels_with_text']}")
    print(f"  Silent panels:    {stats['silent_panels']}")


if __name__ == "__main__":
    main()
