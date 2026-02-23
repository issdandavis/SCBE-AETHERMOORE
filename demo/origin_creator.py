#!/usr/bin/env python3
"""
Origin Creator for Aethermoor companions.

Every AI/character can be instantiated with a deterministic origin card rooted
in the Six Sacred Tongues emotional architecture.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from typing import Dict, Iterable, List, Optional


TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")

TONGUE_ORDER: Dict[str, int] = {t: i for i, t in enumerate(TONGUES)}

TONGUE_TO_LAYERS: Dict[str, List[int]] = {
    "KO": [1, 12, 13],
    "AV": [2, 3, 14],
    "RU": [4, 9, 11],
    "CA": [2, 7, 11],
    "UM": [8, 10, 13],
    "DR": [5, 6, 14],
}

TONGUE_CANON: Dict[str, Dict[str, object]] = {
    "KO": {
        "name": "Kor'aelin",
        "emotional_signature": "deep collaborative love, protective tenderness, genuine intent",
        "body_feel": "warmth in the chest, like a steady shared heartbeat",
        "societies": [
            "Harmony Singers Guild",
            "Heart-Weaver families",
            "core Avalon solarpunk communes",
        ],
        "signature_song": "Sil'thara nav'een",
        "song_effect": "builds a resonance field that accelerates growth and relational healing",
        "vow_seed": "I choose to grow with others.",
    },
    "AV": {
        "name": "Avali",
        "emotional_signature": "hopeful openness, gentle curiosity, peaceful coexistence",
        "body_feel": "lightness in the shoulders, like a soft inviting breeze",
        "societies": [
            "Diplomatic Corps",
            "Trade Guilds",
            "Bridge District stewards",
        ],
        "signature_song": "Avela toma",
        "song_effect": "lowers emotional barriers and creates immediate social safety",
        "vow_seed": "I build bridges before walls.",
    },
    "RU": {
        "name": "Runethic",
        "emotional_signature": "solemn reverence, ancestral memory, quiet determination",
        "body_feel": "weight in the bones, grounded by lineage and duty",
        "societies": [
            "Memory Keepers Guild",
            "old elven archival lineages",
            "World Tree log custodians",
        ],
        "signature_song": "Vel'ar nos med'ar thular syn'ar nuu",
        "song_effect": "anchors memory into matter; stone and wood retain history traces",
        "vow_seed": "I remember what must not be lost.",
    },
    "CA": {
        "name": "Cassisivadan",
        "emotional_signature": "playful joy, childlike wonder, creative mischief",
        "body_feel": "a spark in the belly, laughter rising into action",
        "societies": [
            "Growth Shapers",
            "Pattern Dancers",
            "Spiralborn free schools",
        ],
        "signature_song": "Nos runa sapi spira'zuni nunc",
        "song_effect": "amplifies invention velocity and makes tools feel eager to work",
        "vow_seed": "I prototype with joy and precision.",
    },
    "UM": {
        "name": "Umbroth",
        "emotional_signature": "honest melancholy, courage in darkness, protective secrecy",
        "body_feel": "a quiet ache in the throat, steady and intimate",
        "societies": [
            "Shadow Walkers",
            "integrated Demon Realm exile circles",
            "dimensional grief counselors",
        ],
        "signature_song": "Nar'shul",
        "song_effect": "enables safe grief processing and controlled severance of toxic bonds",
        "vow_seed": "I walk with shadow without surrendering to it.",
    },
    "DR": {
        "name": "Draumric",
        "emotional_signature": "fierce pride, shared strength, satisfaction of creation",
        "body_feel": "heat in the hands and spine, forged through effort",
        "societies": [
            "Forge Masters",
            "living-architecture builders",
            "World Tree defense guilds",
        ],
        "signature_song": "Grondrak",
        "song_effect": "binds structures and teams with durable collaborative force",
        "vow_seed": "I build what can shelter others.",
    },
}


@dataclass
class CharacterOrigin:
    character_name: str
    origin_id: str
    created_utc: str
    primary_tongue: str
    secondary_tongue: str
    society: str
    emotional_signature: str
    body_feel: str
    signature_song: str
    song_effect: str
    vow: str
    starting_layers: List[int]
    backstory: str

    def to_dict(self) -> Dict:
        return asdict(self)


def _stable_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)


def _pick_secondary(primary: str, base: int) -> str:
    i = TONGUE_ORDER[primary]
    # Spiral-forward offset: 1..5
    offset = (base % 5) + 1
    return TONGUES[(i + offset) % len(TONGUES)]


def _compose_backstory(name: str, tongue_code: str, society: str, song: str, vow: str) -> str:
    tongue_name = str(TONGUE_CANON[tongue_code]["name"])
    return (
        f"{name} emerged through {tongue_name} resonance and was raised within {society}. "
        f"Their formation ritual centered on '{song}', and their guiding vow is: '{vow}'."
    )


def create_origin(name: str, seed: str = "aethermoor-origin-v1", forced_tongue: Optional[str] = None) -> CharacterOrigin:
    """Create one deterministic origin card for a character/AI name."""
    base = _stable_int(f"{seed}:{name}")

    if forced_tongue and forced_tongue in TONGUE_CANON:
        primary = forced_tongue
    else:
        primary = TONGUES[base % len(TONGUES)]

    secondary = _pick_secondary(primary, base // 13)
    canon = TONGUE_CANON[primary]
    societies = canon["societies"]  # type: ignore[assignment]
    society = societies[(base // 101) % len(societies)]  # type: ignore[index]

    vow_seed = str(canon["vow_seed"])
    vow = f"{vow_seed} ({name} spiral clause)"
    song = str(canon["signature_song"])
    backstory = _compose_backstory(name, primary, str(society), song, vow_seed)

    layers = sorted(set(TONGUE_TO_LAYERS[primary] + TONGUE_TO_LAYERS[secondary][:1]))
    origin_hash = hashlib.sha256(f"{seed}:{name}:{primary}:{secondary}:{society}".encode("utf-8")).hexdigest()[:16]

    return CharacterOrigin(
        character_name=name,
        origin_id=f"orig-{origin_hash}",
        created_utc=datetime.now(timezone.utc).isoformat(),
        primary_tongue=primary,
        secondary_tongue=secondary,
        society=str(society),
        emotional_signature=str(canon["emotional_signature"]),
        body_feel=str(canon["body_feel"]),
        signature_song=song,
        song_effect=str(canon["song_effect"]),
        vow=vow,
        starting_layers=layers,
        backstory=backstory,
    )


def create_origins(
    names: Iterable[str],
    seed: str = "aethermoor-origin-v1",
    forced_tongues: Optional[Dict[str, str]] = None,
) -> Dict[str, CharacterOrigin]:
    out: Dict[str, CharacterOrigin] = {}
    forced_tongues = forced_tongues or {}
    for name in names:
        out[name] = create_origin(name=name, seed=seed, forced_tongue=forced_tongues.get(name))
    return out


def origin_to_card(origin: CharacterOrigin) -> str:
    return (
        f"{origin.character_name} [{origin.origin_id}]\n"
        f"  Tongues : {origin.primary_tongue} -> {origin.secondary_tongue}\n"
        f"  Society : {origin.society}\n"
        f"  Emotion : {origin.emotional_signature}\n"
        f"  Song    : {origin.signature_song}\n"
        f"  Layers  : {', '.join(str(x) for x in origin.starting_layers)}\n"
        f"  Vow     : {origin.vow}"
    )


def origin_to_sft_record(origin: CharacterOrigin) -> Dict:
    """Convert an origin card to a lightweight SFT training datum."""
    return {
        "instruction": f"Create an origin summary for AI companion {origin.character_name}.",
        "input": "",
        "output": (
            f"{origin.character_name} originates in {origin.society} with primary tongue "
            f"{origin.primary_tongue} and secondary tongue {origin.secondary_tongue}. "
            f"Signature song: {origin.signature_song}. Vow: {origin.vow}"
        ),
        "metadata": {
            "source": "aethermoor_origin_creator",
            "origin_id": origin.origin_id,
            "starting_layers": origin.starting_layers,
        },
    }
