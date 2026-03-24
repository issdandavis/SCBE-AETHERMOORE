#!/usr/bin/env python3
"""
Build the beat-expanded Chapter 1 prompt packet for the Imagen router lane.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "artifacts" / "webtoon" / "panel_prompts" / "ch01_prompts_v4.json"
PREVIEW_DIR = ROOT / "artifacts" / "webtoon" / "ch01" / "v4_preview"
SHOTLIST_PATH = PREVIEW_DIR / "ch01_v4_shotlist.md"
REVIEW_HTML_PATH = PREVIEW_DIR / "ch01_v4_review_sheet.html"
RENDERED_IMAGE_DIR = ROOT / "artifacts" / "webtoon" / "generated_router_hf_full_book" / "ch01"

CHARACTER_ANCHORS = {
    "marcus": "Asian-American man early 30s, short dark messy hair, lean desk-worker build, tired eyes, rumpled dress shirt and hoodie, competence under exhaustion.",
    "polly_raven": "oversized raven with black-violet gloss feathers, obsidian mineral eyes, miniature graduation cap, monocle, black silk bowtie, academic authority with corvid irritation.",
    "polly_human": "young woman with black feather-hair, folded wings, obsidian mineral eyes, dark formal robes, precise posture, slightly too-long fingers, practical care under dry wit.",
    "patrol_creature": "many-legged patrol creature with quiet purposeful gait, bridge-scale silhouette, non-human infrastructure fauna moving like routine maintenance.",
}

CHARACTER_NEGATIVE_ANCHORS = {
    "marcus": "white man, caucasian, european features, blond hair, blue eyes, square-jawed superhero, fashion model, glamorous hero pose, action-cover poster framing",
    "polly_raven": "speech bubbles, mascot bird, cute pet raven, cartoon animal face, human lips, comic dialogue balloon",
    "polly_human": "white fantasy princess, gothic idol glamour, oversized anime doll face, angel cosplay, pin-up posing",
    "patrol_creature": "cute mascot bug, toy robot, harmless cartoon pet",
}

STYLE_SYSTEM = {
    "version": 4,
    "prompt_compilation_mode": "compact_visual",
    "global_tags": [
        "arc-level world continuity",
        "story-first panel design",
        "beat expansion pacing",
        "reader should feel the mental images between lines",
    ],
    "cornerstone_styles": [
        "standard_dialogue",
        "ethereal_divine",
        "chibi_sd",
        "dark_gritty",
        "infographic",
    ],
    "panel_flex_rule": "Expand key beats into short visual sequences while keeping character anchors and environment logic stable.",
    "narration_lane_rule": "Narration lives in recap text lanes; image prompts should prioritize visible action and emotional orientation.",
}

STYLE_BIBLE = {
    "visual_language": "Korean webtoon / manhwa with readable acting, strong environmental storytelling, grounded material detail, and cinematic panel flow.",
    "rules": [
        "Marcus stays visibly consistent: Asian-American man, early 30s, short dark messy hair, lean desk-worker build, tired eyes, rumpled dress shirt and hoodie.",
        "Polly raven form keeps academic regalia and obsidian mineral eyes; human form keeps feather-hair, wings, obsidian eyes, and precise posture.",
        "Earth scenes stay materially human and corporate before spectacle begins.",
        "Crystal spaces feel architectural, physical, and old rather than generic fantasy glow.",
        "Awe panels need breathing room but must not erase the human beat that causes them.",
    ],
}

GENERATION_PROFILE = {
    "model_id": "imagen-router",
    "default_steps": 1,
    "guidance_scale": 0.0,
    "seed_mode": "panel-index-offset",
    "trigger_phrases": ["sixtongues_ch01_pilot"],
    "style_adapter": {
        "path": "docs/specs/WEBTOON_CH01_VISUAL_MEMORY_PACKET.md",
        "mode": "visual-memory-packet",
        "trigger_word": "sixtongues_ch01_pilot",
    },
}

ROUTER_PROFILE = {
    "hero_backend": "imagen-ultra",
    "batch_backend": "imagen",
    "fallback_backend": "hf",
    "output_root": "artifacts/webtoon/generated_router",
}

BASE_PACKET: dict[str, Any] = {
    "chapter_id": "ch01",
    "episode_id": "ep01",
    "title": "Chapter 1: Protocol Handshake",
    "section_title": "Chapter 1: Protocol Handshake",
    "section_type": "chapter",
    "source_markdown": "content/book/reader-edition/ch01.md",
    "key_script": "artifacts/webtoon/ch1_panel_script.md",
    "reference_chapter": True,
    "reference_goal": "Use this packet as the beat-expanded pacing and visual anchor for the Imagen-first Chapter 1 lane.",
    "visual_memory_packet": "docs/specs/WEBTOON_CH01_VISUAL_MEMORY_PACKET.md",
    "status": "packet-ready-v4",
    "adaptation_mode": "beat-expansion",
    "target_panel_min": 50,
    "target_panel_max": 65,
    "default_negative_prompt": "speech bubbles, dialogue balloons, caption boxes, text overlays, subtitles, lettering, watermarks, logos, signatures, comic page borders, multi-panel page layout, poster composition, splash illustration, heroic glamour pose, generic anime pinup framing, western comic-book cover look, superhero inking, vector art, plastic skin, mannequin pose, stiff posing, stock illustration",
    "generation_profile": GENERATION_PROFILE,
    "generation_router_profile": ROUTER_PROFILE,
    "character_anchors": CHARACTER_ANCHORS,
    "character_negative_anchors": CHARACTER_NEGATIVE_ANCHORS,
    "style_system": STYLE_SYSTEM,
    "style_bible": STYLE_BIBLE,
    "visual_anchors": [
        "stale coffee ring and terminal glow for Earth office reality",
        "books hum like signal, not ambience",
        "Polly raven form lands as academic authority with corvid irritation",
        "Aethermoor geography must feel impossible but operational",
        "Marcus is grounded by engineering instincts, not fantasy awe alone",
    ],
    "beat_expansion_schema": {
        "approach": "B with disciplined selective expansion",
        "rule": "Expand only the beats that earn multi-panel treatment and keep pure transitions compact.",
        "panel_fields": ["beat_id", "sequence_id", "sequence_role", "expansion_reason"],
        "sequence_roles": ["solo", "setup", "build", "pivot", "bridge", "payoff", "close"],
    },
}

CAMERA_ANGLES = {
    "ch01-v4-p01": "extreme macro desk-level insert",
    "ch01-v4-p02": "extreme close-up terminal insert straight-on",
    "ch01-v4-p05": "tight three-quarter close-up over monitor glow",
    "ch01-v4-p10": "tight profile insert with mug in foreground",
    "ch01-v4-p11": "tight three-quarter close-up with reflected monitor light",
    "ch01-v4-p21": "ground-level close-up on hands and boots",
    "ch01-v4-p22": "sensory macro insert with shallow focus",
    "ch01-v4-p24": "upward-looking environmental insert",
    "ch01-v4-p29": "extreme close-up regalia insert",
    "ch01-v4-p38": "extreme close-up micro-expression",
    "ch01-v4-p46": "side-tracking medium two-shot",
    "ch01-v4-p47": "tight reaction two-shot with light collapse",
    "ch01-v4-p48": "tight close-up deadline reaction",
    "ch01-v4-p49": "over-the-shoulder reveal toward corridor break",
    "ch01-v4-p51": "telephoto exterior insert across bridge",
    "ch01-v4-p53": "rear tracking medium-wide follow shot",
}

DEFAULT_CAMERA_BY_TYPE = {
    "ESTABLISHING": "wide establishing shot",
    "DETAIL": "insert close-up",
    "IMPACT": "compressed wide impact frame",
    "KINETIC": "tall vertical kinetic frame",
    "REVEAL": "two-beat reveal frame",
    "SPECTACLE": "landscape spectacle panel",
    "QUIET": "breathing panel with negative space",
    "DIALOGUE": "shot-reverse-shot with clear acting",
    "EXPOSITION": "medium explanatory frame",
    "SPLASH": "full splash composition",
    "TRANSITION": "tracking transition frame",
    "CLOSING": "closing beat frame with forward momentum",
}


def panel(
    *,
    type: str,
    beat: str,
    story_job: str,
    scene_prompt: str,
    continuity: str,
    environment: str,
    arc_lock: str,
    cornerstone_style: str,
    mood: str | list[str],
    characters: list[str],
    render_tier: str = "batch",
    w: int = 720,
    h: int = 1280,
    style_tags: list[str] | None = None,
    panel_flex: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": type,
        "beat": beat,
        "story_job": story_job,
        "scene_prompt": scene_prompt,
        "scene_summary": beat,
        "continuity": continuity,
        "environment": environment,
        "arc_lock": arc_lock,
        "cornerstone_style": cornerstone_style,
        "mood": mood,
        "characters": characters,
        "render_tier": render_tier,
        "w": w,
        "h": h,
    }
    if style_tags:
        payload["style_tags"] = style_tags
    if panel_flex:
        payload["panel_flex"] = panel_flex
    return payload


SEQUENCES: list[dict[str, Any]] = []

SEQUENCES.extend(
    [
        {
            "sequence_id": "ch01-seq01",
            "sequence_title": "Late-Night Office Isolation",
            "panels": [
                panel(
                    type="DETAIL",
                    beat="Stale coffee ring",
                    story_job="Open on the tactile misery of Marcus's working life.",
                    scene_prompt="Extreme close-up of Marcus's stale coffee mug at his elbow, the brown residue ring marking the tidal line of the last sip, green monitor glow turning ceramic into something sickly and mineral.",
                    continuity="The coffee has been cold for hours and Marcus is too tired to care.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="dark_gritty",
                    mood="introspective",
                    characters=["marcus"],
                    style_tags=["macro object shot", "late-night office residue"],
                ),
                panel(
                    type="DETAIL",
                    beat="3:14 AM cursor blink",
                    story_job="Establish time and the room's machine rhythm.",
                    scene_prompt="Terminal close-up with green-on-black cursor blinking beside stacked authentication logs, tiny `3:14 AM` readout visible in the corner, the rest of the room held together by that one pulse of light.",
                    continuity="The blinking cursor is the only stable thing in the room.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="infographic",
                    mood="exposition",
                    characters=["marcus"],
                    style_tags=["UI close-up", "forensic terminal framing"],
                    panel_flex="infographic_overlay",
                ),
                panel(
                    type="ESTABLISHING",
                    beat="Marcus alone under three monitors",
                    story_job="Show his whole physical situation before the anomaly escalates.",
                    scene_prompt="Wide office panel of Marcus Chen hunched under three green-lit monitors, dead fluorescents overhead, empty desks falling away into darkness, the whole room feeling pressurized and lonely.",
                    continuity="Marcus is alone in the building except for a distant security guard somewhere below.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="dark_gritty",
                    mood="introspective",
                    characters=["marcus"],
                    w=1280,
                    h=720,
                    style_tags=["wide establishing shot", "corporate submarine mood"],
                ),
                panel(
                    type="QUIET",
                    beat="He has not gone home",
                    story_job="Humanize Marcus before the rupture.",
                    scene_prompt="Medium character beat of Marcus rubbing his face at the desk, compliance reports and cheap life clutter nearby, the posture of a man who has quietly stopped going home on time and barely notices anymore.",
                    continuity="His manager has stopped asking; this is a habitual lonely shift.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="standard_dialogue",
                    mood="introspective",
                    characters=["marcus"],
                    style_tags=["quiet burnout beat", "human before spectacle"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq02",
            "sequence_title": "The Anomaly in the Logs",
            "panels": [
                panel(
                    type="DETAIL",
                    beat="Wrongness too subtle for alarms",
                    story_job="Shift from fatigue into forensic obsession.",
                    scene_prompt="Marcus narrows his eyes at authentication records, not seeing a dramatic breach but a subtle wrongness that lives in the pattern itself, too clean to trip alarms and too irritating to ignore.",
                    continuity="This is the splinter in his brain, not a loud incident response event.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="dark_gritty",
                    mood="tension",
                    characters=["marcus"],
                    style_tags=["face lit by logs", "pattern itch"],
                ),
                panel(
                    type="KINETIC",
                    beat="Scrolling forensic intensity",
                    story_job="Show Marcus acting on instinct.",
                    scene_prompt="Vertical panel of Marcus leaning in and scrolling through authentication records with focused intensity, green light flashing across his fingers and cheekbones as the logs race upward.",
                    continuity="He replaces normal social life with packet analysis and is good at it.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="dark_gritty",
                    mood=["tension", "action"],
                    characters=["marcus"],
                    style_tags=["hands in motion", "security engineer tunnel vision"],
                ),
                panel(
                    type="REVEAL",
                    beat="Line 4,847",
                    story_job="Land the first concrete anomaly.",
                    scene_prompt="Tight terminal reveal of line 4,847 highlighted among clean auth logs, valid signed tokens sitting in the stack with impossible calm, as if they belong and absolutely do not.",
                    continuity="The tokens are valid, timestamped, signed, and still impossible.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="infographic",
                    mood="exposition",
                    characters=["marcus"],
                    style_tags=["highlighted line item", "valid but impossible auth pattern"],
                    panel_flex="infographic_overlay",
                ),
                panel(
                    type="REVEAL",
                    beat="Undocumented routing channel",
                    story_job="Translate the anomaly from curiosity into mystery.",
                    scene_prompt="Routing table close-up showing one undocumented channel threading inside otherwise normal traffic, a hallway hidden behind the wall of the network that should not exist on any diagram.",
                    continuity="It is not obviously malicious, which makes it worse.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="infographic",
                    mood="exposition",
                    characters=["marcus"],
                    style_tags=["routing table callout", "infrastructure hidden in plain sight"],
                    panel_flex="infographic_overlay",
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq03",
            "sequence_title": "Tracing the Unauthorized Channel",
            "panels": [
                panel(
                    type="QUIET",
                    beat="Elegant and not malicious",
                    story_job="Clarify the anomaly's signature.",
                    scene_prompt="Marcus studies the traffic with troubled admiration, realizing the pattern is deliberate, elegant, and not malicious, threaded through the rules like a jazz line between notes.",
                    continuity="He has seen attacks before; this feels like something else entirely.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="standard_dialogue",
                    mood="tension",
                    characters=["marcus"],
                    style_tags=["admiration mixed with dread", "clean impossible routing"],
                ),
                panel(
                    type="DETAIL",
                    beat="Dead-cold sip",
                    story_job="Keep the chapter physically grounded.",
                    scene_prompt="Marcus takes a dead-cold sip of the stale coffee anyway, eyes still on the logs, the taste visibly awful but too familiar to interrupt the work.",
                    continuity="He reaches for the only ritual he still understands.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="dark_gritty",
                    mood="introspective",
                    characters=["marcus"],
                    style_tags=["small human ritual", "coffee as survival"],
                ),
                panel(
                    type="DETAIL",
                    beat="Found you",
                    story_job="Mark the exact moment he commits to the trace.",
                    scene_prompt="Close on Marcus highlighting the impossible sequence with one hand, mouth barely moving around the words `Found you`, green light cutting his features into quiet certainty.",
                    continuity="This is the last normal sentence he says before reality breaks.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="dark_gritty",
                    mood="tension",
                    characters=["marcus"],
                    style_tags=["highlighted token sequence", "small muttered victory"],
                ),
                panel(
                    type="KINETIC",
                    beat="Forensic trace launched",
                    story_job="Build motion into the moment before impact.",
                    scene_prompt="Dynamic vertical of Marcus launching a forensic trace, both hands moving over the keyboard while one unauthorized pathway glows across the monitors like a thread being followed back to its source.",
                    continuity="He is tracing the anomaly instead of backing away from it.",
                    environment="earth_office",
                    arc_lock="earth_protocol_noir",
                    cornerstone_style="dark_gritty",
                    mood=["action", "tension"],
                    characters=["marcus"],
                    style_tags=["typing motion", "routing path visualized on monitors"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq04",
            "sequence_title": "Reality Whites Out",
            "panels": [
                panel(
                    type="IMPACT",
                    beat="Monitor goes pure white",
                    story_job="Start the rupture sharply.",
                    scene_prompt="Straight-on impact panel as Marcus's monitor turns pure white, not crash-white but impossible bright reality-white, his face caught at the first instant he realizes this is not a normal failure.",
                    continuity="The screen is not failing. Something larger is taking over.",
                    environment="white_void",
                    arc_lock="protocol_transmission",
                    cornerstone_style="ethereal_divine",
                    mood="action",
                    characters=["marcus"],
                    style_tags=["first impossible light hit", "monitor as breach point"],
                    panel_flex="painterly_impact",
                ),
                panel(
                    type="IMPACT",
                    beat="White eats the room",
                    story_job="Escalate from screen anomaly to total reality erasure.",
                    scene_prompt="Hero panel as the white spreads from the monitors into the walls, ceiling, Marcus's hands, desk, chair, and floor until every object loses its edge and shadow under overexposed erasure.",
                    continuity="The room is not lit up; it is being deleted into brightness.",
                    environment="white_void",
                    arc_lock="protocol_transmission",
                    cornerstone_style="ethereal_divine",
                    mood=["action", "awe"],
                    characters=["marcus"],
                    render_tier="hero",
                    w=1280,
                    h=720,
                    style_tags=["world erasure", "desk and hands dissolving"],
                    panel_flex="painterly_impact",
                ),
                panel(
                    type="KINETIC",
                    beat="Marcus tries to stand",
                    story_job="Keep the body present inside the cosmic event.",
                    scene_prompt="Marcus lurches upward to stand while the chair, desk, and room lose all boundary, his body searching for stable floor in a world that has stopped honoring surfaces.",
                    continuity="He reacts physically before he can understand the phenomenon.",
                    environment="white_void",
                    arc_lock="protocol_transmission",
                    cornerstone_style="ethereal_divine",
                    mood="action",
                    characters=["marcus"],
                    style_tags=["body in destabilized space", "last instinctive attempt at control"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq05",
            "sequence_title": "Transmission Through the Membrane",
            "panels": [
                panel(
                    type="QUIET",
                    beat="All sound compresses into one tone",
                    story_job="Switch from visual shock to protocol sensation.",
                    scene_prompt="White field panel with Marcus half-silhouetted as every ambient sound folds inward into one sustained tone, the frequency vibrating through teeth, bones, and spine rather than through air.",
                    continuity="This is convergence, not silence.",
                    environment="white_void",
                    arc_lock="protocol_transmission",
                    cornerstone_style="ethereal_divine",
                    mood="tension",
                    characters=["marcus"],
                    style_tags=["sound made physical", "teeth-rattling tone"],
                ),
                panel(
                    type="REVEAL",
                    beat="What do you intend",
                    story_job="Introduce the core protocol question.",
                    scene_prompt="Minimal high-tension panel where the question `What do you intend?` arrives beneath language itself, not heard so much as experienced like gravity pressing on Marcus from every direction.",
                    continuity="The question is not asking for speech but for something deeper than speech.",
                    environment="white_void",
                    arc_lock="protocol_transmission",
                    cornerstone_style="infographic",
                    mood="exposition",
                    characters=["marcus"],
                    style_tags=["textless interrogation", "protocol-level demand"],
                    panel_flex="infographic_overlay",
                ),
                panel(
                    type="QUIET",
                    beat="He cannot answer correctly",
                    story_job="Show the failure to respond at the right layer.",
                    scene_prompt="Marcus strains to answer with ordinary thoughts and words, but they break apart before reaching the shape the question wants, leaving him suspended and untranslatable.",
                    continuity="Human language is the wrong interface for this moment.",
                    environment="white_void",
                    arc_lock="protocol_transmission",
                    cornerstone_style="ethereal_divine",
                    mood="tension",
                    characters=["marcus"],
                    style_tags=["language dissolving", "human interface mismatch"],
                ),
                panel(
                    type="KINETIC",
                    beat="Falling like a routed packet",
                    story_job="Launch the transmission sequence.",
                    scene_prompt="Tall kinetic fall panel of Marcus dropping through symbols, frequencies, geodesic frameworks, and routing geometry like a packet being transmitted between layers of reality.",
                    continuity="He is not merely falling; he is being routed.",
                    environment="white_void",
                    arc_lock="protocol_transmission",
                    cornerstone_style="ethereal_divine",
                    mood=["action", "awe"],
                    characters=["marcus"],
                    render_tier="hero",
                    style_tags=["packet-routing metaphor", "geodesic cosmology", "transmission fall"],
                    panel_flex="painterly_impact",
                ),
            ],
        },
    ]
)

SEQUENCES.extend(
    [
        {
            "sequence_id": "ch01-seq11",
            "sequence_title": "Hands Are Useful",
            "panels": [
                panel(
                    type="REVEAL",
                    beat="Human Polly settles into view",
                    story_job="Let readers absorb the second form clearly.",
                    scene_prompt="Full-figure reveal of Polly in human form: black feather-hair, folded wings, obsidian mineral eyes, dark formal robes, posture exact and practical in the crystal archive light.",
                    continuity="The eyes are the same in both forms and carry the same intelligence.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["polly_human"],
                    style_tags=["full human-form reveal", "formal dark robes"],
                ),
                panel(
                    type="QUIET",
                    beat="Hand offered",
                    story_job="Shift from spectacle to care.",
                    scene_prompt="Polly extends a hand with brisk practicality, wings folded close, as if helping displaced engineers off ancient floors is a routine administrative task.",
                    continuity="Her care expresses itself through logistics, not softness first.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="introspective",
                    characters=["polly_human", "marcus"],
                    style_tags=["practical help", "hands are useful"],
                ),
                panel(
                    type="QUIET",
                    beat="Grounded by contact",
                    story_job="Give Marcus a physical anchor inside the impossible.",
                    scene_prompt="Close two-shot on Marcus taking Polly's hand and rising, the first real human contact grounding him more effectively than any explanation has so far.",
                    continuity="Warmth and solidity matter after white void and crystal wonder.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="introspective",
                    characters=["polly_human", "marcus"],
                    style_tags=["grounding contact", "shared frame after chaos"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq12",
            "sequence_title": "Guest Pass and Danger",
            "panels": [
                panel(
                    type="DIALOGUE",
                    beat="What are the Six Sacred Tongues",
                    story_job="Frame the core tutorial question.",
                    scene_prompt="Walking dialogue beat as Marcus asks what the Six Sacred Tongues actually are, still trying to reduce impossible metaphysics into terms he can debug.",
                    continuity="Questions are how Marcus stays upright.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="exposition",
                    characters=["marcus", "polly_human"],
                    style_tags=["walking exposition", "engineer asks for definitions"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="Domain-separated authorization channels",
                    story_job="Translate magic into Marcus's language.",
                    scene_prompt="Polly answers with cool satisfaction: domain-separated authorization channels, and Marcus's engineer face lights up in involuntary recognition while crystal walls catch impossible-spectrum reflections.",
                    continuity="She enjoys that he keeps seeing the right thing.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="exposition",
                    characters=["marcus", "polly_human"],
                    style_tags=["engineer reaction beat", "magic as infrastructure"],
                ),
                panel(
                    type="ESTABLISHING",
                    beat="This universe has infrastructure",
                    story_job="Push the corridor lane into motion.",
                    scene_prompt="Over-the-shoulder corridor shot as Polly leads Marcus deeper into crystal architecture, the place clearly run like infrastructure rather than whimsy, with doors appearing only when approached.",
                    continuity="The world is operational, not decorative.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="awe",
                    characters=["marcus", "polly_human"],
                    w=1280,
                    h=720,
                    style_tags=["corridor movement beat", "doors appear on approach"],
                ),
                panel(
                    type="EXPOSITION",
                    beat="Heartbeat verification",
                    story_job="Deliver the governing rule of existence.",
                    scene_prompt="Polly explains the Protocol's continuous heartbeat verification as they walk, and a faint visual pulse echoes through the corridor every zero-point-three seconds like the building itself is checking for coherence.",
                    continuity="Existence here is an ongoing authentication process.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="infographic",
                    mood="exposition",
                    characters=["marcus", "polly_human"],
                    style_tags=["heartbeat pulse visualization", "continuous auth explanation"],
                    panel_flex="infographic_overlay",
                ),
                panel(
                    type="EXPOSITION",
                    beat="Flicker then cease",
                    story_job="State the fail condition clearly and coldly.",
                    scene_prompt="Somber dialogue panel where Polly spells out the fail state: flicker, then cease, not die, the corridor light briefly thinning around Marcus as the idea lands.",
                    continuity="The consequence is existential deletion, not injury.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["marcus", "polly_human"],
                    style_tags=["fail state lands", "corridor light thins around subject"],
                ),
                panel(
                    type="EXPOSITION",
                    beat="Seventy-two hour guest pass",
                    story_job="Put a hard timer on the chapter's stakes.",
                    scene_prompt="Deadline beat as Polly tells Marcus he has roughly seventy-two hours on a guest pass to establish a permanent baseline, his face caught between focus and the beginnings of real fear.",
                    continuity="The clock starts now and governs everything after this chapter.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="tension",
                    characters=["marcus", "polly_human"],
                    style_tags=["deadline reveal", "guest pass stakes"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq13",
            "sequence_title": "First Look Outside",
            "panels": [
                panel(
                    type="TRANSITION",
                    beat="Gap in the corridor",
                    story_job="Set up the exterior reveal with a pause.",
                    scene_prompt="Marcus notices the corridor opening into a gap of crystal where the architecture forgets to stay enclosed, and he turns his head despite Polly continuing ahead.",
                    continuity="The exterior reveal interrupts the corridor lesson.",
                    environment="crystal_corridor",
                    arc_lock="aethermoor_world_reveal",
                    cornerstone_style="standard_dialogue",
                    mood="awe",
                    characters=["marcus", "polly_human"],
                    style_tags=["pause before exterior reveal", "corridor gap"],
                ),
                panel(
                    type="REVEAL",
                    beat="Auroral world outside",
                    story_job="Deliver the chapter's biggest world reveal.",
                    scene_prompt="Hero landscape reveal through the corridor gap: auroral violet-gold sky, floating landmasses, a pale blue river winding sideways below, and upside-down grass growing on the undersides of impossible meadows.",
                    continuity="The outside world is impossible yet coherent, not dreamlike mush.",
                    environment="aethermoor_exterior",
                    arc_lock="aethermoor_world_reveal",
                    cornerstone_style="ethereal_divine",
                    mood="awe",
                    characters=["marcus"],
                    render_tier="hero",
                    w=1280,
                    h=720,
                    style_tags=["world reveal", "sideways river", "upside-down meadows"],
                    panel_flex="painterly_impact",
                ),
                panel(
                    type="DETAIL",
                    beat="Bridge and patrol creature",
                    story_job="Prove the world is inhabited and functional.",
                    scene_prompt="Focused exterior insert showing a crystal bridge between floating masses and a many-legged patrol creature crossing it with quiet purpose, making the impossible landscape feel governed and lived-in.",
                    continuity="Aethermoor is a working civilization, not just scenery.",
                    environment="aethermoor_exterior",
                    arc_lock="aethermoor_world_reveal",
                    cornerstone_style="standard_dialogue",
                    mood="awe",
                    characters=["patrol_creature"],
                    style_tags=["functional world detail", "bridge patrol creature"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="Don't stare yet",
                    story_job="Snap Marcus back to motion without killing wonder.",
                    scene_prompt="Marcus freezes in stunned awe at the gap while Polly, still ahead in the corridor, tells him not to stare yet, her voice sharp with practical urgency rather than cruelty.",
                    continuity="The world reveal matters, but the clock matters more.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["marcus", "polly_human"],
                    style_tags=["awe interrupted by urgency", "distance between guide and newcomer"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq14",
            "sequence_title": "Follow Polly Into the Impossible",
            "panels": [
                panel(
                    type="TRANSITION",
                    beat="He keeps walking",
                    story_job="Close the chapter on forward motion rather than full understanding.",
                    scene_prompt="Marcus pulls himself back into motion and follows Polly on autopilot through the crystal corridor, posture stiff with overload but still moving because stopping is not an option.",
                    continuity="He chooses movement before comprehension.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="introspective",
                    characters=["marcus", "polly_human"],
                    style_tags=["forward motion after awe", "overloaded but functional"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="Do you have coffee",
                    story_job="End on a human question that reveals what Marcus values.",
                    scene_prompt="Walking two-shot where Marcus asks if they have coffee, not as a joke but as the most human question left available to him in a world that has replaced every other certainty.",
                    continuity="He reaches for familiarity under maximum dislocation.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="comedy",
                    characters=["marcus", "polly_human"],
                    style_tags=["human question under surreal pressure", "walking banter"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="Essence brew and a mug",
                    story_job="Let Polly soften without dropping her edge.",
                    scene_prompt="Polly visibly mangles the word `caw-fee`, then softens enough to promise essence brew and a mug, her expression caught between corvid confusion and reluctant kindness.",
                    continuity="This is the first offer of comfort she makes.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="comedy",
                    characters=["marcus", "polly_human"],
                    style_tags=["corvid word confusion", "small promise of comfort"],
                ),
                panel(
                    type="QUIET",
                    beat="Glance back and follow deeper",
                    story_job="Close with mystery carried forward, not solved.",
                    scene_prompt="Final chapter beat: Marcus glances back once toward where he arrived, filing the anomaly as a possible message from the other side, then turns and follows Polly deeper into the impossible corridor.",
                    continuity="He is already connecting the unauthorized channel to everything that happened next.",
                    environment="crystal_corridor",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood=["introspective", "awe"],
                    characters=["marcus", "polly_human"],
                    style_tags=["one last look back", "follow into the impossible"],
                ),
            ],
        },
    ]
)

SEQUENCES.extend(
    [
        {
            "sequence_id": "ch01-seq06",
            "sequence_title": "Stone and Crystal Library",
            "panels": [
                panel(
                    type="IMPACT",
                    beat="Stone impact",
                    story_job="Return the body to solid reality.",
                    scene_prompt="Ground-level impact panel as Marcus hits cold stone face-first, relief mixing with pain because physical surfaces suddenly exist again.",
                    continuity="The fall ends on something brutally real and ancient.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="dark_gritty",
                    mood="action",
                    characters=["marcus"],
                    style_tags=["stone floor impact", "pain as proof of reality"],
                ),
                panel(
                    type="DETAIL",
                    beat="Rapid self-check",
                    story_job="Show trained crisis behavior.",
                    scene_prompt="Close physical beat of Marcus flexing fingers and toes, breathing hard and running a rapid body check on the crystal stone floor before looking up at anything else.",
                    continuity="He defaults to crisis assessment before wonder.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="introspective",
                    characters=["marcus"],
                    style_tags=["post-impact triage", "hands and breath"],
                ),
                panel(
                    type="DETAIL",
                    beat="Books, ozone, and resonance",
                    story_job="Introduce the new environment through sensation first.",
                    scene_prompt="Sensory detail panel of old leather-bound books, ozone in the air, and crystal surfaces breathing with a resonant pressure that feels half scent and half vibration inside Marcus's sinuses.",
                    continuity="The room announces itself before it explains itself.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="ethereal_divine",
                    mood="awe",
                    characters=["marcus"],
                    style_tags=["sensory atmosphere", "books and ozone"],
                ),
                panel(
                    type="REVEAL",
                    beat="Wide archive reveal",
                    story_job="Show the architecture that will define the new world.",
                    scene_prompt="Hero wide reveal of the crystal-grown Archive towering above Marcus, carved shelving climbing into impossible height, warm sourceless light passing through stone and crystal like a breathing cathedral of books.",
                    continuity="This is physical architecture, not generic magical fog.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="ethereal_divine",
                    mood="awe",
                    characters=["marcus"],
                    render_tier="hero",
                    w=1280,
                    h=720,
                    style_tags=["towering archive reveal", "grounded magical architecture"],
                    panel_flex="painterly_impact",
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq07",
            "sequence_title": "The Books Hum Back",
            "panels": [
                panel(
                    type="DETAIL",
                    beat="Crystal shelves under sourceless light",
                    story_job="Slow the pace into inspection.",
                    scene_prompt="Marcus studies carved crystal shelves under warm sourceless light, dust motes turning slowly while old books rest in precise architectural rows.",
                    continuity="The room feels quiet but not inert.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="introspective",
                    characters=["marcus"],
                    style_tags=["environment inspection", "quiet old structure"],
                ),
                panel(
                    type="REVEAL",
                    beat="Every book emits a frequency",
                    story_job="Translate magic into signal.",
                    scene_prompt="Close-up on several books and crystal spines emitting subtly different light halos, each one suggesting its own frequency inside one vast harmonic chord.",
                    continuity="Marcus recognizes signal where others would call it ambience.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="infographic",
                    mood="exposition",
                    characters=["marcus"],
                    style_tags=["frequency halos", "polyphonic archive"],
                    panel_flex="infographic_overlay",
                ),
                panel(
                    type="QUIET",
                    beat="Kneeling in signal",
                    story_job="Anchor his engineering identity in the new world.",
                    scene_prompt="Vertical quiet panel of Marcus kneeling and shaking slightly on the stone floor, one hand braced down while he listens to the room and realizes the silence around him is actually structured signal.",
                    continuity="Awe and analysis arrive together.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood=["awe", "introspective"],
                    characters=["marcus"],
                    style_tags=["kneeling engineer beat", "signal hidden in silence"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq08",
            "sequence_title": "Polly in Raven Form",
            "panels": [
                panel(
                    type="QUIET",
                    beat="Voice from above and behind",
                    story_job="Break the solitude with personality.",
                    scene_prompt="Marcus freezes as a dry, impatient voice cuts in from above and behind him, the archive still warm and enormous while the sound feels surgically specific.",
                    continuity="The first speaker here is annoyed rather than grand.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["marcus", "polly_raven"],
                    style_tags=["voice interrupts stillness", "orientation breaks solitude"],
                ),
                panel(
                    type="REVEAL",
                    beat="Oversized raven on the shelf",
                    story_job="Start Polly's reveal in silhouette and scale.",
                    scene_prompt="Marcus turns to see an oversized raven perched on a crystal shelf above him, silhouette sharp against warm archive light, clearly too large and too composed to be ordinary.",
                    continuity="Polly is bigger than a normal raven and utterly self-possessed.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["polly_raven"],
                    style_tags=["shelf silhouette reveal", "corvid authority"],
                ),
                panel(
                    type="DETAIL",
                    beat="Cap, monocle, bowtie",
                    story_job="Land the absurd academic details cleanly.",
                    scene_prompt="Tight character detail on Polly's obsidian mineral eyes, miniature graduation cap, monocle, and black silk bowtie, every accessory dignified enough to make the absurdity more convincing.",
                    continuity="The regalia is not a joke prop; it is part of her identity.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["polly_raven"],
                    style_tags=["costume detail", "obsidian eyes", "academic regalia"],
                ),
                panel(
                    type="REVEAL",
                    beat="Late student stare-down",
                    story_job="Finish the character reveal with attitude.",
                    scene_prompt="Full vertical reveal of Polly staring down at Marcus from the shelf like a professor regarding a late student, glossy black-violet feathers neat and severe against crystal bookshelves.",
                    continuity="Her expression is tired annoyance backed by centuries of intelligence.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["polly_raven"],
                    render_tier="hero",
                    style_tags=["character reveal", "late student energy", "shelf dominance"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq09",
            "sequence_title": "Orientation by Raven",
            "panels": [
                panel(
                    type="REVEAL",
                    beat="Unknown language lands as comprehension",
                    story_job="Show the world bending language rules.",
                    scene_prompt="Dialogue panel where Polly speaks in a language Marcus should not know, yet every word lands in comprehension immediately, his expression caught between disbelief and involuntary understanding.",
                    continuity="The meaning bypasses normal hearing.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="exposition",
                    characters=["marcus", "polly_raven"],
                    style_tags=["impossible comprehension", "dialogue as direct meaning"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="She names him exactly",
                    story_job="Establish Polly's authority and knowledge.",
                    scene_prompt="Split dialogue panel: Polly introduces herself as Fifth Circle Keeper and recites Marcus Chen's identity and origin with calm accuracy while he sits on the stone floor staring up at her.",
                    continuity="She knows his name, age, profession, and Earth origin on contact.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood=["drama", "exposition"],
                    characters=["marcus", "polly_raven"],
                    style_tags=["identity recital", "absurd authority"],
                ),
                panel(
                    type="QUIET",
                    beat="Threat-assessment autopilot",
                    story_job="Keep Marcus behaving like Marcus under impossible conditions.",
                    scene_prompt="Marcus's eyes track Polly, the doorway, the shelves, and the floor in one silent threat-assessment sweep even while his face says he cannot believe a raven in regalia is giving him orientation.",
                    continuity="Security-engineer autopilot never shuts off.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="dark_gritty",
                    mood="tension",
                    characters=["marcus", "polly_raven"],
                    style_tags=["threat assessment under absurdity", "eyes tracking exits"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="Welcome to Aethermoor",
                    story_job="Deliver the formal arrival line.",
                    scene_prompt="Polly announces that the Protocol told them Marcus was coming and welcomes him to Aethermoor, her posture bored on the surface and watchful underneath.",
                    continuity="This is not random arrival; the system expected him.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="exposition",
                    characters=["marcus", "polly_raven"],
                    style_tags=["formal welcome", "protocol expectation"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="Psychotic break theory rejected",
                    story_job="Keep the tone sharp and character-driven.",
                    scene_prompt="Marcus deadpans that this must be a sleep-deprivation psychotic break, and Polly rejects the theory with dry corvid sarcasm rather than sympathy.",
                    continuity="Her humor is a delivery system for urgent truth.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="comedy",
                    characters=["marcus", "polly_raven"],
                    style_tags=["dry sarcasm", "two-shot disbelief versus certainty"],
                ),
            ],
        },
        {
            "sequence_id": "ch01-seq10",
            "sequence_title": "Polly Transforms",
            "panels": [
                panel(
                    type="KINETIC",
                    beat="She hops down and says he needs the Tongues",
                    story_job="Move the scene physically toward instruction.",
                    scene_prompt="Polly hops down from the shelf to the floor and tells Marcus he will need the Six Sacred Tongues if he wants to survive here, her small body all practical urgency.",
                    continuity="The survival stakes begin before the explanation is complete.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["marcus", "polly_raven"],
                    style_tags=["movement to floor", "orientation turns serious"],
                ),
                panel(
                    type="DIALOGUE",
                    beat="What kills me here",
                    story_job="Make Marcus ask the right blunt question.",
                    scene_prompt="Marcus, still half-risen from the stone floor, asks what exactly can kill him here, the line landing with engineer bluntness instead of theatrical fear.",
                    continuity="He is trying to turn fantasy stakes into operational facts.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="tension",
                    characters=["marcus", "polly_raven"],
                    style_tags=["blunt survival question", "half-standing posture"],
                ),
                panel(
                    type="DETAIL",
                    beat="Fear for him",
                    story_job="Reveal Polly's real emotional state.",
                    scene_prompt="Close detail on Polly's feathers tightening flat and eyes sharpening, a micro-expression of fear for Marcus rather than fear of him.",
                    continuity="Marcus notices because he is trained to read subtle tells.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="standard_dialogue",
                    mood="drama",
                    characters=["polly_raven"],
                    style_tags=["micro-expression reveal", "feathers flatten under stress"],
                ),
                panel(
                    type="REVEAL",
                    beat="Architectural transformation",
                    story_job="Show Polly's human form as deliberate and controlled.",
                    scene_prompt="Hero transformation panel where Polly unfolds from raven into human form with precise, architectural motion, feathers stretching into feather-hair and wings while the obsidian eyes remain exactly the same.",
                    continuity="The transformation is seamless rather than flashy.",
                    environment="crystal_library",
                    arc_lock="archive_grounded_magic",
                    cornerstone_style="ethereal_divine",
                    mood="awe",
                    characters=["polly_human"],
                    render_tier="hero",
                    style_tags=["feathers to human form", "same obsidian eyes"],
                    panel_flex="painterly_impact",
                ),
            ],
        },
    ]
)


SEQUENCE_EXPANSION_REASONS = {
    "ch01-seq01": "Open on tactile burnout details so Marcus feels human before the rupture starts.",
    "ch01-seq02": "Split the anomaly into irritation, scan, and recognition so discovery feels earned instead of announced.",
    "ch01-seq03": "Hold the trace across several images so the office tension tightens before reality breaks.",
    "ch01-seq04": "The whiteout must spread in stages to read like reality failing, not a one-frame flash.",
    "ch01-seq05": "Use multiple transmission images so the fall reads as packet-routing rather than generic freefall.",
    "ch01-seq06": "Arrival needs sensory re-orientation before exposition begins.",
    "ch01-seq07": "The library should answer Marcus in small sensory beats before Polly interrupts it.",
    "ch01-seq08": "Polly's entrance works best as a slow silhouette and attitude reveal, not a single card.",
    "ch01-seq09": "The first exchange needs panel-per-line rhythm so disbelief and authority can play off each other cleanly.",
    "ch01-seq10": "Transformation and survival stakes deserve a dedicated mini-sequence, not a shortcut panel.",
    "ch01-seq11": "The handshake and identity beat need breathing room because they ground the chapter emotionally.",
    "ch01-seq12": "The cease-not-die explanation changes the threat model and should land in steps.",
    "ch01-seq13": "Corridor motion, dialogue, and reveal inserts make the infrastructure turn feel earned.",
    "ch01-seq14": "Pair the world reveal with smaller human beats and the surveillance coda so awe does not flatten the ending.",
}


def infer_sequence_role(index: int, total: int) -> str:
    if total <= 1:
        return "solo"
    if index == 1:
        return "setup"
    if index == total:
        return "close"
    if index == total - 1:
        return "payoff"
    if total >= 4 and index == max(2, (total + 1) // 2):
        return "pivot"
    if index == 2:
        return "build"
    return "bridge"


def panel_image_path(panel_id: str) -> Path:
    return RENDERED_IMAGE_DIR / f"{panel_id}.png"


def camera_angle_for_panel(panel: dict[str, Any]) -> str:
    panel_id = str(panel.get("id") or "")
    if panel_id in CAMERA_ANGLES:
        return CAMERA_ANGLES[panel_id]
    return DEFAULT_CAMERA_BY_TYPE.get(str(panel.get("type") or "").upper(), "cinematic story panel")


def write_shotlist(packet: dict[str, Any]) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Chapter 1 v4 Shot List",
        "",
        f"- Panels: `{packet['panel_count']}`",
        f"- Source: `{packet['source_markdown']}`",
        f"- Reading strip: `{(PREVIEW_DIR / 'v4_reading_preview.jpg').as_posix()}`",
        "",
        "| Order | Shot | Panel | Sequence | Role | Beat | Camera | Render |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for panel in packet["panels"]:
        image_path = panel_image_path(panel["id"])
        render_cell = image_path.relative_to(ROOT).as_posix() if image_path.exists() else "pending"
        lines.append(
            "| {order} | `{shot}` | `{panel_id}` | {sequence} | `{role}` | {beat} | {camera} | `{render}` |".format(
                order=panel["review_order"],
                shot=panel["shot_label"],
                panel_id=panel["id"],
                sequence=panel["sequence_title"],
                role=panel["sequence_role"],
                beat=panel["beat"],
                camera=(panel.get("style_metadata") or {}).get("camera_angle", camera_angle_for_panel(panel)),
                render=render_cell,
            )
        )
    SHOTLIST_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_review_html(packet: dict[str, Any]) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    html_lines = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Chapter 1 v4 Review Sheet</title>",
        (
            "<style>"
            "body{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#111;color:#eee;}"
            "h1,p{margin:0 0 12px;}"
            ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px;}"
            ".card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:14px;}"
            "img{width:100%;height:auto;border-radius:8px;background:#000;display:block;margin:0 0 12px;}"
            ".meta{font-size:13px;line-height:1.45;color:#d7d7d7;}"
            ".shot{font-weight:700;color:#9fd3ff;}"
            ".beat{font-weight:600;color:#fff;}"
            "</style>"
        ),
        "</head><body>",
        f"<h1>{packet['title']} Review Sheet</h1>",
        "<p>Ordered review sheet for camera direction, sequence rhythm, and rendered panel drift.</p>",
        "<div class='grid'>",
    ]
    for panel in packet["panels"]:
        image_path = panel_image_path(panel["id"])
        html_lines.append("<div class='card'>")
        if image_path.exists():
            html_lines.append(f"<img src='{image_path.resolve().as_uri()}' alt='{panel['id']}'>")
        html_lines.append(f"<div class='meta'><div class='shot'>{panel['shot_label']} · {panel['id']}</div>")
        html_lines.append(f"<div class='beat'>{panel['beat']}</div>")
        html_lines.append(f"<div><strong>Sequence:</strong> {panel['sequence_title']}</div>")
        html_lines.append(f"<div><strong>Role:</strong> {panel['sequence_role']}</div>")
        html_lines.append(
            f"<div><strong>Camera:</strong> {(panel.get('style_metadata') or {}).get('camera_angle', camera_angle_for_panel(panel))}</div>"
        )
        html_lines.append(f"<div><strong>Story job:</strong> {panel['story_job']}</div>")
        html_lines.append("</div></div>")
    html_lines.append("</div></body></html>")
    REVIEW_HTML_PATH.write_text("\n".join(html_lines), encoding="utf-8")


def build_packet() -> dict[str, Any]:
    packet = deepcopy(BASE_PACKET)
    panels: list[dict[str, Any]] = []
    beat_sequences: list[dict[str, Any]] = []
    panel_index = 1
    ordered_sequences = sorted(SEQUENCES, key=lambda sequence: int(str(sequence["sequence_id"]).split("seq")[-1]))
    for sequence_index, sequence in enumerate(ordered_sequences, start=1):
        sequence_id = sequence["sequence_id"]
        expansion_reason = SEQUENCE_EXPANSION_REASONS.get(sequence_id, "Expanded for smoother visual reading cadence.")
        total_sequence_panels = len(sequence["panels"])
        sequence_panel_ids: list[str] = []
        for sequence_panel_index, raw_panel in enumerate(sequence["panels"], start=1):
            panel_payload = deepcopy(raw_panel)
            panel_id = f"ch01-v4-p{panel_index:02d}"
            panel_payload["id"] = panel_id
            panel_payload["review_order"] = panel_index
            panel_payload["shot_label"] = f"CH01-{panel_index:03d}"
            panel_payload["beat_id"] = f"{sequence_id}-beat{sequence_panel_index:02d}"
            panel_payload["sequence_id"] = sequence_id
            panel_payload["sequence_title"] = sequence["sequence_title"]
            panel_payload["sequence_index"] = sequence_index
            panel_payload["sequence_panel_index"] = sequence_panel_index
            panel_payload["sequence_role"] = infer_sequence_role(sequence_panel_index, total_sequence_panels)
            panel_payload["expansion_reason"] = expansion_reason
            panel_payload.setdefault("style_metadata", {})["camera_angle"] = camera_angle_for_panel(panel_payload)
            panels.append(panel_payload)
            sequence_panel_ids.append(panel_id)
            panel_index += 1
        beat_sequences.append(
            {
                "sequence_id": sequence_id,
                "sequence_title": sequence["sequence_title"],
                "sequence_index": sequence_index,
                "panel_count": total_sequence_panels,
                "expansion_reason": expansion_reason,
                "panel_ids": sequence_panel_ids,
            }
        )

    packet["panel_count"] = len(panels)
    packet["beat_sequences"] = beat_sequences
    packet["panels"] = panels
    return packet


def main() -> None:
    packet = build_packet()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    write_shotlist(packet)
    write_review_html(packet)
    print(f"Wrote {packet['panel_count']} panels to {OUTPUT_PATH}")
    print(f"Wrote shot list to {SHOTLIST_PATH}")
    print(f"Wrote review sheet to {REVIEW_HTML_PATH}")


if __name__ == "__main__":
    main()
