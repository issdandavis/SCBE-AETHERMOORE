#!/usr/bin/env python3
"""
CSide ChoiceScript Exporter
============================
Exports Aethermoor game scenes to ChoiceScript format for compatibility
with the CSide IDE (https://choicescriptdev.fandom.com/).

ChoiceScript is a simple scripting language for writing interactive fiction.
This module converts the internal scene representation into valid
ChoiceScript source files that can be opened, edited, and run in CSide.

Pure Python, no external dependencies.
"""

from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Lightweight scene dataclass (mirrors engine.py patterns)
# ---------------------------------------------------------------------------
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


@dataclass
class SceneChoice:
    """A single selectable option inside a scene."""

    label: str
    target_scene_id: str
    tongue: str = "CA"
    stat_delta: float = 5.0       # how much to bump tongue stat
    extra_sets: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnhancedScene:
    """One narrative scene with text, choices, and metadata."""

    scene_id: str
    title: str = ""
    text: str = ""
    choices: List[SceneChoice] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    location: str = ""
    time_of_day: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_]")


def _safe_label(raw: str) -> str:
    """Convert an arbitrary string into a valid ChoiceScript label."""
    return _SAFE_ID_RE.sub("_", raw.strip()).strip("_").lower()


def _wrap_text(text: str, width: int = 78) -> str:
    """Wrap long narrative text to *width* columns."""
    paragraphs = text.strip().split("\n")
    wrapped: List[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            wrapped.append("")
            continue
        wrapped.append(textwrap.fill(para, width=width))
    return "\n".join(wrapped)


# ---------------------------------------------------------------------------
# CsideExporter
# ---------------------------------------------------------------------------
class CsideExporter:
    """Export Aethermoor scenes to ChoiceScript format."""

    # Default tongue stats tracked in startup.txt
    TRACKED_STATS = [f"tongue_{t}" for t in TONGUES]
    EXTRA_STATS = ["day", "location_flag", "intent"]

    # ------------------------------------------------------------------
    # Single scene
    # ------------------------------------------------------------------
    def export_scene(self, scene: EnhancedScene) -> str:
        """Convert a single *EnhancedScene* to ChoiceScript source.

        Produces a block starting with ``*label scene_id``, the narrative
        text, and a ``*choice`` section with ``#`` options.
        """
        lines: List[str] = []
        label = _safe_label(scene.scene_id)
        lines.append(f"*label {label}")

        # Optional comment header
        if scene.title:
            lines.append(f"*comment --- {scene.title} ---")

        # Narrative body
        if scene.text:
            lines.append("")
            lines.append(_wrap_text(scene.text))
            lines.append("")

        # Choices
        if scene.choices:
            lines.append("*choice")
            for ch in scene.choices:
                lines.append(f"  #{ch.label}")
                # Tongue stat bump
                tongue_var = f"tongue_{ch.tongue}"
                sign = "+" if ch.stat_delta >= 0 else ""
                lines.append(f"    *set {tongue_var} {sign}{int(ch.stat_delta)}")
                # Extra sets (arbitrary key=value)
                for var, val in ch.extra_sets.items():
                    if isinstance(val, str):
                        lines.append(f'    *set {var} "{val}"')
                    else:
                        s = "+" if val >= 0 else ""
                        lines.append(f"    *set {var} {s}{val}")
                target = _safe_label(ch.target_scene_id)
                lines.append(f"    *goto {target}")
        else:
            # No choices -- end-of-file / terminal scene
            lines.append("*finish")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # All scenes into one file
    # ------------------------------------------------------------------
    def export_all(self, scenes: Dict[str, EnhancedScene]) -> str:
        """Export all scenes into a single ChoiceScript file.

        Scenes are separated by blank lines and ordered by dict insertion.
        """
        blocks: List[str] = []
        for scene in scenes.values():
            blocks.append(self.export_scene(scene))
        return "\n\n".join(blocks) + "\n"

    # ------------------------------------------------------------------
    # startup.txt
    # ------------------------------------------------------------------
    def export_startup(self, scenes: Dict[str, EnhancedScene]) -> str:
        """Generate ``startup.txt`` with ``*create`` statements.

        Sets up tongue stats, day counter, and the initial ``*goto``.
        """
        lines: List[str] = []
        lines.append("*comment Aethermoor: Six Tongues Protocol")
        lines.append("*comment Auto-generated by cside_export.py")
        lines.append("")

        lines.append("*title Aethermoor: Six Tongues Protocol")
        lines.append("*author Issac Davis")
        lines.append("")

        # Create tongue stats
        for stat in self.TRACKED_STATS:
            lines.append(f"*create {stat} 0")
        for stat in self.EXTRA_STATS:
            if stat == "day":
                lines.append(f"*create {stat} 1")
            elif stat == "location_flag":
                lines.append(f'*create {stat} "earth"')
            elif stat == "intent":
                lines.append(f'*create {stat} "unknown"')
            else:
                lines.append(f"*create {stat} 0")

        lines.append("")

        # Jump to first scene
        if scenes:
            first_id = _safe_label(next(iter(scenes)))
            lines.append(f"*goto_scene scenes")
        else:
            lines.append("*finish")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Save to directory
    # ------------------------------------------------------------------
    def save_to_directory(
        self,
        scenes: Dict[str, EnhancedScene],
        output_dir: str,
    ) -> List[str]:
        """Save as a proper ChoiceScript project.

        Creates:
        - ``<output_dir>/startup.txt``
        - ``<output_dir>/scenes.txt`` (all scenes combined)

        Returns a list of file paths written.
        """
        os.makedirs(output_dir, exist_ok=True)
        written: List[str] = []

        startup_path = os.path.join(output_dir, "startup.txt")
        with open(startup_path, "w", encoding="utf-8") as f:
            f.write(self.export_startup(scenes))
        written.append(startup_path)

        scenes_path = os.path.join(output_dir, "scenes.txt")
        with open(scenes_path, "w", encoding="utf-8") as f:
            f.write(self.export_all(scenes))
        written.append(scenes_path)

        return written


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _build_sample_scenes() -> Dict[str, EnhancedScene]:
    """Construct a small set of sample Aethermoor scenes for testing."""
    scenes: Dict[str, EnhancedScene] = {}

    scenes["earth_morning"] = EnhancedScene(
        scene_id="earth_morning",
        title="Earth Morning",
        text=(
            "Day 1. Your alarm goes off at 6:47 AM.\n"
            "The apartment is small but functional.\n"
            "Terminal glowing in the corner."
        ),
        choices=[
            SceneChoice(
                label="Check the terminal first",
                target_scene_id="earth_work",
                tongue="CA",
                stat_delta=5,
            ),
            SceneChoice(
                label="Get coffee, messages can wait",
                target_scene_id="earth_work_casual",
                tongue="RU",
                stat_delta=3,
            ),
            SceneChoice(
                label="Go back to sleep (5 more minutes...)",
                target_scene_id="earth_morning_late",
                tongue="AV",
                stat_delta=2,
                extra_sets={"day": 1},
            ),
        ],
        tags=["earth", "morning"],
        location="Izack's Apartment",
        time_of_day="morning",
    )

    scenes["earth_work"] = EnhancedScene(
        scene_id="earth_work",
        title="Research Lab",
        text=(
            "The lab hums with server racks and the soft glow of monitors.\n"
            "You're debugging an authentication anomaly in the routing logs.\n"
            "Something feels off. The patterns don't match any known protocol."
        ),
        choices=[
            SceneChoice(
                label="Trace the anomaly deeper",
                target_scene_id="earth_evening",
                tongue="CA",
                stat_delta=5,
            ),
            SceneChoice(
                label="Document and escalate to security",
                target_scene_id="earth_evening",
                tongue="RU",
                stat_delta=4,
            ),
        ],
        tags=["earth", "work"],
        location="Research Lab",
        time_of_day="afternoon",
    )

    scenes["earth_evening"] = EnhancedScene(
        scene_id="earth_evening",
        title="Evening Return",
        text=(
            "Home. The apartment feels different tonight.\n"
            "A book on the shelf catches your eye."
        ),
        choices=[
            SceneChoice(
                label="Read the book",
                target_scene_id="transit",
                tongue="DR",
                stat_delta=5,
            ),
        ],
        tags=["earth", "evening"],
        location="Izack's Apartment",
        time_of_day="evening",
    )

    scenes["transit"] = EnhancedScene(
        scene_id="transit",
        title="The Crossing",
        text=(
            "Reality collapses.\n"
            "You feel yourself falling through protocol space.\n"
            "You wake on a floating island, bathed in purple light."
        ),
        choices=[],
        tags=["transit"],
    )

    return scenes


def selftest() -> None:
    """Verify exporter produces valid ChoiceScript syntax."""
    print(f"\n{'=' * 60}")
    print("  CSide ChoiceScript Exporter -- Self-Test")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    scenes = _build_sample_scenes()
    exporter = CsideExporter()

    # --- 1. Single scene export ---
    morning_cs = exporter.export_scene(scenes["earth_morning"])
    check("*label present", "*label earth_morning" in morning_cs)
    check("*choice present", "*choice" in morning_cs)
    check("# option present", "#Check the terminal first" in morning_cs)
    check("*set tongue stat", "*set tongue_CA +5" in morning_cs)
    check("*goto present", "*goto earth_work" in morning_cs)
    check("Narrative text present", "alarm goes off" in morning_cs)
    check("Extra set for day", "*set day +1" in morning_cs)

    # --- 2. Terminal scene ---
    transit_cs = exporter.export_scene(scenes["transit"])
    check("Terminal scene has *finish", "*finish" in transit_cs)
    check("Terminal scene has *label", "*label transit" in transit_cs)
    check("Terminal scene has no *choice", "*choice" not in transit_cs)

    # --- 3. Export all ---
    all_cs = exporter.export_all(scenes)
    for sid in scenes:
        check(f"All export contains *label {sid}",
              f"*label {_safe_label(sid)}" in all_cs)
    check("All export has multiple labels", all_cs.count("*label") == len(scenes))

    # --- 4. Startup ---
    startup = exporter.export_startup(scenes)
    check("Startup has *title", "*title" in startup)
    check("Startup has *author", "*author" in startup)
    for t in TONGUES:
        check(f"Startup creates tongue_{t}", f"*create tongue_{t} 0" in startup)
    check("Startup creates day", "*create day 1" in startup)
    check('Startup creates location_flag', '*create location_flag "earth"' in startup)
    check('Startup creates intent', '*create intent "unknown"' in startup)

    # --- 5. Save to directory ---
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="cside_test_")
    written = exporter.save_to_directory(scenes, tmpdir)
    check("Two files written", len(written) == 2)
    for path in written:
        check(f"File exists: {os.path.basename(path)}", os.path.isfile(path))
    # Read back and verify
    with open(os.path.join(tmpdir, "startup.txt"), encoding="utf-8") as f:
        startup_disk = f.read()
    check("Startup on disk matches", "*create tongue_KO" in startup_disk)
    with open(os.path.join(tmpdir, "scenes.txt"), encoding="utf-8") as f:
        scenes_disk = f.read()
    check("Scenes on disk has all labels", scenes_disk.count("*label") == len(scenes))

    # --- 6. Safe label ---
    check("safe_label strips special chars", _safe_label("foo-bar baz!") == "foo_bar_baz")
    check("safe_label lowercases", _safe_label("Earth_Morning") == "earth_morning")
    check("safe_label handles empty", _safe_label("") == "")

    # --- 7. Round-trip consistency ---
    morning_cs2 = exporter.export_scene(scenes["earth_morning"])
    check("Deterministic output", morning_cs == morning_cs2)

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")
    if failed == 0:
        print("  ChoiceScript exporter fully operational.\n")
    else:
        print(f"  WARNING: {failed} check(s) failed.\n")


if __name__ == "__main__":
    selftest()
