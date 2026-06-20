#!/usr/bin/env python3
"""
Integrate Pass 46 (Stones In Her Skirt), Pass 47 (Lamps Of The Maccabees),
and Pass 48 (The Hour Before Procedure) into the canonical manuscript.

Three new chapters are inserted into Part III "Jerusalem Narrows":
  - Ch 11 = Pass 46 (Sukkot, woman caught in adultery)
  - Ch 12 = Pass 47 (Hanukkah, Roman patrol)
  - Ch 16 = Pass 48 (tense peace, night before crucifixion)

Existing chapters 11-39 are renumbered:
  - Ch 11-13 -> Ch 13-15 (shift +2)
  - Ch 14-39 -> Ch 17-42 (shift +3)

Renumbering uses a two-pass placeholder substitution so inline references
("Used in Chapter 38", etc.) update consistently with the headings.

Three new Endnote Packet entries are added to the back matter.
A timestamped backup of the manuscript is written before overwrite.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MAN_DIR = REPO / "content" / "projects" / "miracle-memory"
MANUSCRIPT = MAN_DIR / "the-miracle-was-the-memory-v1.md"
PASSES_DIR = MAN_DIR / "passes"

PASS_FILES = {
    46: PASSES_DIR / "pass-46-stones-in-her-skirt.md",
    47: PASSES_DIR / "pass-47-lamps-of-the-maccabees.md",
    48: PASSES_DIR / "pass-48-the-hour-before-procedure.md",
}

# Renumber map: old chapter number -> new chapter number.
# Ch 0-10 unchanged. Ch 11-13 shift +2. Ch 14-39 shift +3.
RENUMBER: dict[int, int] = {}
for _old in range(11, 14):
    RENUMBER[_old] = _old + 2
for _old in range(14, 40):
    RENUMBER[_old] = _old + 3


def extract_prose(pass_file: Path) -> tuple[str, str]:
    """Extract the prose body (and scene title) from a pass file.

    Pass files contain editorial scaffolding (status header, scene note,
    optional textual note) followed by the prose, headed by a line of the form
    '## Scene: <Title>'. This function returns (title, prose).
    """
    text = pass_file.read_text(encoding="utf-8")
    match = re.search(r"^## Scene:\s*(.+)$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"No '## Scene:' header in {pass_file.name}")
    title = match.group(1).strip()
    prose = text[match.end() :].lstrip()
    # Strip trailing whitespace
    prose = prose.rstrip() + "\n"
    return title, prose


def renumber_chapters(manuscript: str) -> str:
    """Renumber 'Chapter NN' references using placeholder substitution.

    Operates in two passes:
      1. Replace each old 'Chapter NN' with a unique placeholder
         (processed in reverse order to avoid prefix collisions, though
         word boundaries should make this unnecessary).
      2. Replace each placeholder with the new 'Chapter NN'.
    """
    # Pass 1: old -> placeholder
    for old in sorted(RENUMBER.keys(), reverse=True):
        placeholder = f"__MMCHAP_PLACEHOLDER_{old:03d}__"
        pat = re.compile(rf"\bChapter {old}\b")
        manuscript = pat.sub(placeholder, manuscript)

    # Pass 2: placeholder -> new
    for old, new in RENUMBER.items():
        placeholder = f"__MMCHAP_PLACEHOLDER_{old:03d}__"
        manuscript = manuscript.replace(placeholder, f"Chapter {new}")

    # Sanity: no stray placeholders should remain
    if "__MMCHAP_PLACEHOLDER_" in manuscript:
        raise RuntimeError("stray chapter placeholder remained after renumbering")

    return manuscript


def insert_new_chapters(
    manuscript: str,
    title46: str,
    prose46: str,
    title47: str,
    prose47: str,
    title48: str,
    prose48: str,
) -> str:
    """Insert the three new chapters at their target positions in Part III."""

    # Block A: insert Ch 11 (Pass 46) and Ch 12 (Pass 47) right after the
    # Part III header and before the renumbered Ch 13 (was Ch 11, Temple Moment).
    # Manuscript convention: 2 blank lines between Part header and chapter,
    # 3 blank lines between adjacent chapters.
    anchor_a = "# Part III. Jerusalem Narrows\n\n\n## Chapter 13. The Temple Moment"
    block_a = (
        "# Part III. Jerusalem Narrows\n\n\n"
        f"## Chapter 11. {title46}\n\n{prose46}\n\n\n"
        f"## Chapter 12. {title47}\n\n{prose47}\n\n\n"
        "## Chapter 13. The Temple Moment"
    )
    if anchor_a not in manuscript:
        raise RuntimeError("Part III anchor for Pass 46/47 insertion not found")
    manuscript = manuscript.replace(anchor_a, block_a, 1)

    # Block B: insert Ch 16 (Pass 48) right before the renumbered Ch 17
    # (was Ch 14, Rome Has Procedure). 3 blank lines after Pass 48 prose
    # before the next chapter heading.
    anchor_b = "## Chapter 17. Rome Has Procedure"
    block_b = f"## Chapter 16. {title48}\n\n{prose48}\n\n\n" "## Chapter 17. Rome Has Procedure"
    if anchor_b not in manuscript:
        raise RuntimeError("Ch 17 anchor for Pass 48 insertion not found")
    manuscript = manuscript.replace(anchor_b, block_b, 1)

    return manuscript


# Endnote Packet entries for the three new chapters.

ENDNOTE_CH11 = (
    "**Chapter 11. The Stones In Her Skirt.** *Source:* John 7:53-8:11 "
    "(the *Pericope Adulterae*); John 7:2 places the surrounding discourse "
    "during the Feast of Tabernacles (Sukkot). *Kept:* the Temple-court "
    "setting, the dragging of a woman accused of adultery, the appeal to "
    "Moses's command of stoning, Jesus bending and writing in the dust "
    "twice, the *let any one of you who is without sin be the first to "
    "throw a stone* saying, the elders departing first, the concluding "
    "exchange (*Has no one condemned you? / No one, sir. / Then neither do "
    "I condemn you. Go now and leave your life of sin.*). *Set aside:* the "
    "broader Johannine discourse in John 7-8 surrounding the pericope, "
    "which is not narrated. *Added:* Dagan's outsider position in the "
    "crowd, the wrong-knot detail in the woman's skirt, the small stones "
    "in the dust at men's feet after the crowd disperses, the woman's "
    "shaking right hand, Dagan's interior recognition that he had not "
    "even thought of picking up a stone, and the older-Dagan reflection "
    "on whatever was written in the dust. The chapter also leans into the "
    "second clause of the closing line — *go and leave your life of sin* "
    "— as mercy that asks everything of the spared person, against the "
    "thinner reading that takes only the first clause as 'mercy.' *Contested:* "
    "John 7:53-8:11 is absent from the earliest Greek manuscripts of John "
    "and floats among different positions in the textual tradition. Most "
    "modern critical editions print it in double brackets or set it as "
    "an appendix. The story is attested in Papias of Hierapolis (c. 110 CE) "
    "according to Eusebius, well before the manuscripts that omit it were "
    "copied; Augustine knew it by the late fourth century and defended "
    "its absence in some copies as a deletion by scribes worried it would "
    "license adultery. The book carries the story not as guaranteed "
    "authentic Johannine text but as a memory the early church preserved "
    "deliberately. Bruce Metzger represents the careful-but-receptive "
    "position; Bart Ehrman, the more skeptical. Both are worth reading."
)

ENDNOTE_CH12 = (
    "**Chapter 12. Lamps Of The Maccabees.** *Source:* John 10:22-23 "
    "(Jesus at the Feast of Dedication in Solomon's Portico, the only "
    "explicit New Testament mention of the festival); 1 Maccabees 4:36-59 "
    "and 2 Maccabees 10:1-8 (the rededication of the temple and the "
    "institution of the festival); Josephus *Antiquities* 12.7.6-7 (his "
    "account of the festival under the name *Lights*). *Kept:* the "
    "eight-night festival, household lamp practice (one lamp added each "
    "night), the Maccabean memory of throwing off a foreign Hellenistic "
    "occupier (1 Maccabees 4), the festival's name in Greek (*Hanukkah* / "
    "*Feast of Dedication* / *Festival of Lights*). *Set aside:* the John "
    "10:22-39 *I and the Father are one* discourse and the stone-pickup "
    "against Jesus that follows are brought into the household by Tirzah's "
    "rumor rather than by direct Dagan witness. *Added:* the Roman decanus "
    "Crispus, his grandmother Antonia, the cousin Tirzah, the four-year-old "
    "Eliezer, the household scene with festival cake, the patrol's "
    "investigative visit, Dagan's naming of every knife in the house, the "
    "fifth-night lamp lit on the fourth night for a Latin grandmother, "
    "Mara's *you spoke to him the way you used to wish someone had "
    "spoken to Hanan* coda, and the older-Dagan retrospective that "
    "Crispus survives his rotation and later names his second son "
    "Antonius. *Contested:* Second-Temple-period observance of Hanukkah "
    "was less formalized than later rabbinic and medieval Jewish practice; "
    "precise household ritual details in the chapter are reconstructed "
    "from the literary tradition without claiming archaeological certainty. "
    "The festival's existence and its political resonance for first-century "
    "Jews under Roman rule are firm."
)

ENDNOTE_CH16 = (
    "**Chapter 16. The Hour Before Procedure.** No specific source. "
    "Composite-witness chamber piece set on the night of Jesus's arrest "
    "(Mark 14:32-52, Matt 26:36-56, Luke 22:39-53, John 18:1-12 all place "
    "the arrest in the Garden of Gethsemane after the Last Supper). "
    "*Kept:* the timing immediately before the procedural execution "
    "narrated in the following chapter; the fact of the arrest reaching "
    "Dagan and Mara by runner rather than by their presence in the garden. "
    "*Set aside:* the Gethsemane scene itself, which the book does not "
    "depict from any disciple's interior POV; the trials before the "
    "Sanhedrin and Pilate, which the book references obliquely in Ch 17 "
    "but does not narrate. *Added:* the chamber-piece between Dagan and "
    "Mara, the lamp from Ch 12 (Crispus's lamp for Antonia) burning at "
    "the center of the scene, Mara's four observations of Dagan's earned "
    "changes (the Roman in the doorway with the cloth, the morning Hosea's "
    "cough broke, the Temple stones not picked up, the staying hand), and "
    "Mara's *it is the same as Sepphoris* line that reaches back to Ch 2 "
    "and decides the shape of Dagan's non-attendance at the cross. The "
    "chapter's structural function is to give the reader a hand to hold "
    "before the procedural horror of the following chapter."
)


def insert_endnotes(manuscript: str) -> str:
    """Insert the three new Endnote Packet entries in the back matter."""

    # Insert Ch 11 and Ch 12 endnotes at the start of Part III of the
    # Endnote Packets. The renumbering pass has already changed the
    # existing "Chapter 11 (Temple Moment)" entry to "Chapter 13".
    anchor_c = "### Part III — Jerusalem\n\n**Chapter 13. The Temple Moment.**"
    block_c = (
        "### Part III — Jerusalem\n\n" f"{ENDNOTE_CH11}\n\n" f"{ENDNOTE_CH12}\n\n" "**Chapter 13. The Temple Moment.**"
    )
    if anchor_c not in manuscript:
        raise RuntimeError("Endnote Part III anchor not found")
    manuscript = manuscript.replace(anchor_c, block_c, 1)

    # Insert Ch 16 endnote between renumbered Ch 15 (Mary Brings Oil) entry
    # and renumbered Ch 17 (Rome Has Procedure) entry.
    anchor_d = "**Chapter 17. Rome Has Procedure.**"
    block_d = f"{ENDNOTE_CH16}\n\n**Chapter 17. Rome Has Procedure.**"
    if anchor_d not in manuscript:
        raise RuntimeError("Endnote Ch 17 anchor not found")
    if manuscript.count(anchor_d) != 1:
        raise RuntimeError(
            f"Endnote Ch 17 anchor appears {manuscript.count(anchor_d)} times " "after renumbering; expected exactly 1"
        )
    manuscript = manuscript.replace(anchor_d, block_d, 1)

    return manuscript


def main() -> None:
    if not MANUSCRIPT.exists():
        raise SystemExit(f"manuscript not found at {MANUSCRIPT}")

    # Backup
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = MANUSCRIPT.with_suffix(f".pre-pass-integration.{ts}.bak.md")
    shutil.copy2(MANUSCRIPT, backup_path)
    print(f"Backup written: {backup_path}")

    # Read manuscript
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    before_words = len(manuscript.split())
    print(f"Manuscript before: {before_words:,} words")

    # Extract prose from passes
    title46, prose46 = extract_prose(PASS_FILES[46])
    title47, prose47 = extract_prose(PASS_FILES[47])
    title48, prose48 = extract_prose(PASS_FILES[48])
    print(f"Pass 46: {title46} ({len(prose46.split()):,} words)")
    print(f"Pass 47: {title47} ({len(prose47.split()):,} words)")
    print(f"Pass 48: {title48} ({len(prose48.split()):,} words)")

    # Step 1: renumber existing chapter references (headings + endnotes + inline)
    manuscript = renumber_chapters(manuscript)

    # Step 2: insert new chapter bodies in the main manuscript
    manuscript = insert_new_chapters(
        manuscript,
        title46,
        prose46,
        title47,
        prose47,
        title48,
        prose48,
    )

    # Step 3: insert new Endnote Packet entries in the back matter
    manuscript = insert_endnotes(manuscript)

    # Write
    MANUSCRIPT.write_text(manuscript, encoding="utf-8")
    after_words = len(manuscript.split())
    print(f"Manuscript after:  {after_words:,} words " f"(+{after_words - before_words:,})")

    # Verify final chapter count
    chapter_headers = re.findall(r"^## Chapter \d+\. ", manuscript, re.MULTILINE)
    print(f"Final chapter heading count: {len(chapter_headers)} (expected 43)")


if __name__ == "__main__":
    main()
