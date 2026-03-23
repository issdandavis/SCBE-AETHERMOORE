"""
Chapter 1: Protocol Handshake — Full 30-Panel Cinematic Generation (v3)
Source: artifacts/webtoon/ch01_adaptation_script_v2.md + manhwa-cinematic-forge skill
Style: Solo Leveling pacing + Fog Hill painterly atmosphere
Characters locked from reference sheets.
"""
import argparse
import os
import sys
import time
import json
from pathlib import Path

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
DEFAULT_OUT_DIR = Path("C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/ch01/v3")
DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_BY_TIER = {
    "fast": "imagen-4.0-fast-generate-001",
    "standard": "imagen-4.0-generate-001",
    "ultra": "imagen-4.0-ultra-generate-001",
}
DEFAULT_TIER = "standard"

# ─── STYLE DNA (constant across all panels) ───
STYLE = (
    "manhwa webtoon illustration, full-width vertical scroll panel, "
    "clean confident linework with soft painterly atmospheric shading, "
    "cinematic camera angle, game-quality character design. "
    "Dynamic composition with Solo Leveling panel flow "
    "and Fog Hill of Five Elements painterly atmosphere. "
)

# ─── CHARACTER ANCHORS (constant per character) ───
MARCUS = (
    "Marcus Chen: 32-year-old Asian American man with Chinese heritage, "
    "short dark messy hair, tired dark brown eyes with dark circles underneath, "
    "light stubble on angular jawline, lean desk-worker build not muscular. "
    "Dark navy hoodie unzipped over wrinkled white button-down shirt, dark jeans. "
    "NO glasses ever. "
)

POLLY_RAVEN = (
    "Polly the raven: a fantasy raven TWICE normal raven size knee-height to human, "
    "glossy black-to-violet feathers that drink light, "
    "polished OBSIDIAN mineral eyes smooth reflective and unnaturally bright, "
    "wearing miniature graduation cap at jaunty angle, monocle over one eye, "
    "black silk bowtie neatly knotted at throat. "
)

POLLY_HUMAN = (
    "Polly humanoid form: appears 20 years old but eyes suggest centuries, "
    "glossy black FEATHERS instead of hair cascading past shoulders "
    "with visible barbs and iridescent sheen not normal hair, "
    "black wings folded neatly against back, "
    "polished OBSIDIAN mineral eyes identical to raven form, "
    "dark formal scholarly robes, fingers slightly too long with dark iridescent nails. "
)

# ─── COLOR PALETTES ───
COOL_OFFICE = "Color palette: cool blues, dark greens, terminal green accent only. No warm tones whatsoever. "
WHITE_VOID = "Color palette: draining to pure white, minimal linework, ink on void. "
FALL_LAYERS = "Color palette: shifting geometric colors dissolving from rainbow into warm amber crystal. "
WARM_ARCHIVE = "Color palette: warm amber, crystal refraction light, soft directionless glow. No cool blues. "
WARM_CORRIDOR = "Color palette: warm amber crystal light mixed with cool blue crystal refractions. "
AETHERMOOR_EXT = "Color palette: violet-gold auroral sky, pale blue luminescence, warm amber crystal. "

# ─── ALL 30 PANELS ───
PANELS = {
    # ══════════════════════════════════════════
    # SCENE 1: THE OFFICE (Shots 1-8)
    # ══════════════════════════════════════════
    "p01": {
        "title": "The Desk — Establishing",
        "aspect": "3:4",
        "prompt": STYLE + COOL_OFFICE + MARCUS +
        "Scene: High angle looking down at Marcus hunched at his desk in a dark empty corporate office. "
        "Three monitors with green-on-black terminal code. Green monitor glow is the ONLY light source. "
        "Dead fluorescent lights visible overhead turned OFF. Coffee mug with brown residue ring at his elbow. "
        "Behind him on a shelf: three framed photos catching screen-glow, a dead succulent plant, stacked papers. "
        "Through a glass partition below: a tiny security guard walks alone in the distance. "
        "The office is empty, institutional, submarine-like. Marcus is the only warm thing in the frame. "
        "Camera: high angle, he is small and isolated. "
        "Mood: 3:14 AM, exhaustion, loneliness, a life held together by competence. "
        "High quality digital art.",
    },
    "p02": {
        "title": "Three Hours Cold — Coffee Detail",
        "aspect": "1:1",
        "prompt": STYLE + COOL_OFFICE +
        "MACRO CLOSE-UP, tight crop on a single object, NO characters visible. "
        "Scene: Extreme close-up of a white ceramic coffee mug on a dark office desk. "
        "The mug has a visible brown residue RING marking the tidal line where coffee evaporated hours ago. "
        "The coffee inside is dead black and cold. Green terminal code is reflected in the liquid surface. "
        "Keyboard edge visible at bottom of frame. A few coffee drip stains on the desk. "
        "Camera: macro, slightly above, intimate. "
        "Mood: stale, mineral, the taste of late nights and bad decisions made tactile. "
        "High quality digital art.",
    },
    "p03": {
        "title": "The Shelf — Bryce Memorial",
        "aspect": "16:9",
        "prompt": STYLE + COOL_OFFICE +
        "CLOSE-UP of a desk shelf in a dark office, lit only by green monitor glow. NO full characters visible. "
        "Three framed photos on the shelf catching the green light: "
        "First photo: a woman in graduation robes holding a diploma, warm smile. "
        "Second photo: casual group of young tech workers at a startup, smiling at camera. "
        "Third photo, placed SLIGHTLY APART from the others in a wooden frame: "
        "a young man with dark brown hair, short beard, blue eyes, wearing a blue plaid shirt, "
        "chin resting on his fist, warm easy grin like he is about to say something funny. Outdoor setting. "
        "Next to the photos: a dead succulent plant in a small pot, and stacked compliance reports. "
        "Camera: eye-level macro, intimate shelf detail. "
        "Mood: the only personal objects in an institutional room. These matter. "
        "High quality digital art.",
    },
    "p04": {
        "title": "Breathing — Terminal Glow",
        "aspect": "16:9",
        "prompt": STYLE + COOL_OFFICE +
        "ATMOSPHERIC BREATHING PANEL, NO characters, pure mood. "
        "Scene: A dark office wall lit by faint green terminal glow. "
        "A blinking cursor shape reflected on the wall. Faint hum of servers suggested by the stillness. "
        "Mostly darkness with one point of green light. Minimalist composition. "
        "Camera: static, atmospheric. "
        "Mood: silence as presence, the held breath between cursor blinks. "
        "High quality digital art.",
    },
    "p05": {
        "title": "Line 4847 — Terminal Close-up",
        "aspect": "1:1",
        "prompt": STYLE + COOL_OFFICE +
        "Scene: Close-up of a computer monitor showing green-on-black terminal code. "
        "Dense lines of authentication logs scroll on screen. "
        "One line near the middle is HIGHLIGHTED in brighter green, standing out from the rest. "
        "The highlighted sequence looks elegant, almost beautiful, threading through the code cleanly. "
        "Marcus's eye is faintly reflected in the monitor glass, sharp and focused. "
        "Camera: tight on the monitor, slight angle. "
        "Mood: discovery, a pattern that should not exist but is too clean to be malicious. "
        "High quality digital art.",
    },
    "p06": {
        "title": "Found You — Close-up",
        "aspect": "1:1",
        "prompt": STYLE + COOL_OFFICE + MARCUS +
        "Scene: Close-up of Marcus's face illuminated by green terminal glow from the left. "
        "His eyes are narrowed, focused, mouth set in a thin line. Fatigue replaced by professional obsession. "
        "Green light paints his face. Dark shadows on the right side. "
        "His stubble, tired eyes, and angular jawline visible in detail. "
        "Camera: tight close-up, slightly below eye level, making him look capable and locked-in. "
        "Mood: the moment a security engineer finds the anomaly. Not fear. Recognition. "
        "High quality digital art.",
    },
    "p07": {
        "title": "The Sip — Macro Detail",
        "aspect": "16:9",
        "prompt": STYLE + COOL_OFFICE +
        "MACRO DETAIL PANEL. "
        "Scene: Close-up of a hand hovering over a coffee mug in a dark office. "
        "The hand hesitates, then grips the mug. The man knows the coffee is cold and dead. "
        "He is going to drink it anyway. The gesture is habit, not choice. "
        "Green terminal glow illuminates the hand and mug from one side. "
        "Camera: tight macro on hand and mug only. "
        "Mood: the taste of his actual life, compressed into one gesture. "
        "High quality digital art.",
    },
    "p08": {
        "title": "The Guard Below — Isolation",
        "aspect": "16:9",
        "prompt": STYLE + COOL_OFFICE +
        "Scene: Looking DOWN through a glass floor partition at a lower level of an office building. "
        "Far below, a single security guard walks alone through an empty lit corridor, tiny in the frame. "
        "His shoes would squeak on the tile. He is the only other human in the building. "
        "The upper frame is dark office with green monitor glow. The lower frame is sterile fluorescent. "
        "Camera: high angle looking down through glass, extreme distance to the guard. "
        "Mood: metronomic loneliness, two humans in a building, floors apart. "
        "High quality digital art.",
    },

    # ══════════════════════════════════════════
    # SCENE 2: THE WHITEOUT (Shots 9-11)
    # ══════════════════════════════════════════
    "p09": {
        "title": "Screen Goes White — Impact",
        "aspect": "16:9",
        "prompt": STYLE + WHITE_VOID + MARCUS +
        "WIDE LANDSCAPE composition, COMPRESSED HEIGHT for impact speed. "
        "Scene: Marcus half-rising from his office chair, palms up, bracing against nothing, recoiling. "
        "The entire office is being consumed by impossible white light radiating from the monitors outward. "
        "Desk edges dissolving into white. Walls bleaching. Coffee mug is the LAST object casting a shadow. "
        "The white BURNS with oversaturated bloom effect. NOT an explosion. Reality being overwritten. "
        "Camera: frontal, slightly low angle, white consuming toward the viewer. "
        "Mood: not a crash. A re-authentication. The world asking a question. "
        "High quality digital art.",
    },
    "p10": {
        "title": "What Do You Intend — Narrow Strip",
        "aspect": "16:9",
        "prompt": STYLE + WHITE_VOID +
        "MINIMALIST PANEL, extreme close-up on near-total white void. "
        "Scene: Only a pair of wide-open dark brown eyes visible against pure white emptiness. "
        "Just the eyes, bridge of nose, and eyebrows. Everything else is white. "
        "Very faint ghostly text barely visible between the eyes: What do you intend. "
        "The white space feels oppressive and judging, not peaceful. Waiting for an answer. "
        "Camera: extreme close-up, just eyes floating in void. "
        "Mood: a system larger than the world has asked for a credential he cannot present. "
        "High quality digital art.",
    },
    "p11": {
        "title": "Breathing — White to Black",
        "aspect": "16:9",
        "prompt": STYLE +
        "BREATHING TRANSITION PANEL, NO characters, pure gradient. "
        "Color palette: gradual transition from pure white on the left to pure black on the right. "
        "A smooth gradient with no objects, no characters, no text. "
        "The transition represents the space between reality ending and a new world beginning. "
        "Camera: static, abstract. "
        "Mood: the held breath between worlds. "
        "High quality digital art.",
    },

    # ══════════════════════════════════════════
    # SCENE 3: THE FALL (Shot 12)
    # ══════════════════════════════════════════
    "p12": {
        "title": "The Packet — Transmission Fall",
        "aspect": "9:16",
        "prompt": STYLE + FALL_LAYERS + MARCUS +
        "TALL VERTICAL composition, portrait orientation, reader scrolls through the fall. "
        "Scene: Marcus falling headfirst through visible LAYERS of abstract space like geological strata. "
        "TOP of image: dissolving binary code and hexadecimal data streams. "
        "UPPER MIDDLE: geodesic wireframe spheres and Poincare disk geometry. "
        "LOWER MIDDLE: musical notation twisted into colored spirals, frequencies as visible color. "
        "NEAR BOTTOM: six colored glyphs flash past like highway signs "
        "(red-gold, blue-silver, deep purple, white-gold, shadow-black, earth-brown). "
        "BOTTOM: crystal formations resolving into recognizable architecture. "
        "Marcus is disoriented, arms spread, a data packet being routed through a system. "
        "Concentric rings radiate from his body suggesting a sustained tone. "
        "Camera: top-down, viewer looks down at him falling away through layers. "
        "Mood: dislocation with terrible order, the scroll IS the fall. "
        "High quality digital art.",
    },

    # ══════════════════════════════════════════
    # SCENE 4: ARRIVAL (Shots 13-16)
    # ══════════════════════════════════════════
    "p13": {
        "title": "Breathing — Sliver of Amber",
        "aspect": "16:9",
        "prompt": STYLE +
        "BREATHING PANEL, NO characters, transition from darkness to new world. "
        "Color palette: mostly black with a thin sliver of warm amber crystal light at the right edge. "
        "Pure black field with just a crack of warm golden light breaking through. "
        "Camera: static, abstract. "
        "Mood: arrival. Something solid exists again. The first hint of Aethermoor. "
        "High quality digital art.",
    },
    "p14": {
        "title": "Cheek on Stone — Ground Level",
        "aspect": "3:4",
        "prompt": STYLE + WARM_ARCHIVE + MARCUS +
        "Scene: Marcus lies face-down on ancient smooth stone floor, his cheek pressed flat against cold stone. "
        "Eyes half-open with bodily relief at something solid after dissolving abstraction. "
        "One hand in foreground, fingers splayed on stone, visibly trembling. "
        "Behind him crystal walls rise with shelves carved into translucent crystal, "
        "filled with leather-bound books that each have a faint warm glow around their spines. "
        "Ceiling curves upward impossibly high, grown from crystal not built. "
        "Sourceless soft light refracts through crystal. Dust motes float. "
        "Camera: ground-level, stone floor filling foreground, Marcus face-down. "
        "Mood: bodily relief, the specific cold-and-hard of stone that has not seen sunlight in a long time. "
        "High quality digital art.",
    },
    "p15": {
        "title": "The Archive Breathes — Looking Up",
        "aspect": "9:16",
        "prompt": STYLE + WARM_ARCHIVE +
        "TALL VERTICAL establishing shot, NO characters, pure environment. "
        "Scene: Low angle looking UP at a vast crystal library archive. "
        "Crystal shelves stretch upward toward a ceiling that might be thirty feet or infinite. "
        "Crystal formations are organic, grown not carved, natural geometry. "
        "Hundreds of leather-bound books fill the shelves, each with a faint individual warm glow "
        "as if humming at different frequencies. Tiny light halos around each book spine. "
        "Light is sourceless, soft, refracted through translucent crystal, warm amber tones. "
        "Dust motes catch the light. The room itself produces a chord. "
        "No torches, no candles, no gothic arches. Pure crystal architecture. "
        "Camera: extreme low angle looking straight up, showing infinite vertical scale. "
        "Mood: reverence and unease, the books are signaling not decorating. "
        "High quality digital art.",
    },
    "p16": {
        "title": "Breathing — Book Hum",
        "aspect": "16:9",
        "prompt": STYLE + WARM_ARCHIVE +
        "BREATHING DETAIL PANEL, NO characters. "
        "Scene: Extreme close-up of three leather-bound book spines on a crystal shelf. "
        "Each book has a faint warm glow around it, slightly different color temperature. "
        "The crystal shelf refracts the glow into tiny prismatic fragments. "
        "Dust motes float in the warm light between the books. "
        "Camera: macro close-up on book spines. "
        "Mood: the hum made visible, each book on a slightly different frequency. "
        "High quality digital art.",
    },

    # ══════════════════════════════════════════
    # SCENE 5: POLLY THE RAVEN (Shots 17-21)
    # ══════════════════════════════════════════
    "p17": {
        "title": "The Raven — Character Reveal",
        "aspect": "3:4",
        "prompt": STYLE + WARM_ARCHIVE + POLLY_RAVEN +
        "Scene: Polly the raven perched on a crystal shelf about four feet above the viewer, "
        "looking down with sharp annoyed intelligence. "
        "Graduation cap at a jaunty angle. Monocle catches crystal light. Bowtie neatly knotted. "
        "Her feathers shift between black and deep violet. "
        "Crystal archive shelves with glowing books stretch behind her infinitely. "
        "She looks at the viewer like a professor whose student showed up twenty minutes late. "
        "Camera: LOW ANGLE looking UP at her on the shelf. She has all the authority. "
        "Mood: absurd dignity, sharp intelligence, the most memorable character introduction possible. "
        "High quality digital art.",
    },
    "p18": {
        "title": "Polly Close-up — Corvid Stare",
        "aspect": "1:1",
        "prompt": STYLE + WARM_ARCHIVE + POLLY_RAVEN +
        "Scene: Extreme close-up of Polly the raven's face. "
        "Her obsidian mineral eyes fill the frame, smooth reflective and too bright. "
        "Head tilted at a sharp corvid angle. Monocle glints. "
        "Graduation cap tassel hangs. Feathers black shifting to violet at edges. "
        "Expression: centuries of exhausted patience behind a veneer of annoyance. "
        "Camera: tight close-up, eye level with the raven. "
        "Mood: you are being assessed and found wanting. "
        "High quality digital art.",
    },
    "p19": {
        "title": "Threat Assessment — Two Character",
        "aspect": "3:4",
        "prompt": STYLE + WARM_ARCHIVE + MARCUS + POLLY_RAVEN +
        "Scene: Marcus on his knees on smooth ancient stone floor, looking up at Polly. "
        "Polly perches on a crystal shelf above him, looking down. "
        "The height difference between them emphasizes her authority. "
        "Marcus's expression: processing impossible information like an engineer reading bad data. "
        "Crystal archive behind them with shelves of glowing books stretching upward. "
        "Camera: ground level, showing both characters with the vast archive behind them. "
        "Mood: first meeting between a disoriented engineer and an absurdly dignified raven. "
        "High quality digital art.",
    },
    "p20": {
        "title": "Polly's Fear — Micro Expression",
        "aspect": "1:1",
        "prompt": STYLE + WARM_ARCHIVE + POLLY_RAVEN +
        "Scene: Close-up of Polly the raven, her feathers subtly pressed FLAT against her body. "
        "A micro-expression of fear. Not fear of the person she is talking to. Fear FOR them. "
        "Her obsidian eyes carry concern she is trying to hide behind professional delivery. "
        "The graduation cap and monocle are still perfectly in place but her feathers betray her. "
        "Camera: medium close-up, eye level. "
        "Mood: the crack in her composure, caring enough to be afraid. Small detail, huge meaning. "
        "High quality digital art.",
    },
    "p21": {
        "title": "The Stakes — 72 Hours",
        "aspect": "3:4",
        "prompt": STYLE + WARM_ARCHIVE + MARCUS + POLLY_RAVEN +
        "Scene: Marcus has stood up because lying down felt like the wrong posture for this conversation. "
        "He stands in his hoodie and button-down, upright, engineer posture, receiving bad data. "
        "Polly the raven stands at his knee level, looking up at him now. "
        "The power dynamic has shifted slightly, he chose to stand. "
        "Crystal archive behind them, warm amber light. "
        "Camera: eye level, showing both characters at their full heights. "
        "Mood: existential stakes delivered plainly. Not game-like. Infrastructurally indifferent. "
        "High quality digital art.",
    },

    # ══════════════════════════════════════════
    # SCENE 6: HANDS ARE USEFUL (Shots 22-24)
    # ══════════════════════════════════════════
    "p22": {
        "title": "The Transformation — Two Beat",
        "aspect": "9:16",
        "prompt": STYLE + WARM_ARCHIVE +
        "TWO-BEAT VERTICAL panel, split into top half and bottom half sharing same background. "
        "TOP HALF: A large raven with glossy black-violet feathers mid-transformation. "
        "Feathers flowing UPWARD like ink dispersing in water. Shape stretching and reorganizing. "
        "No sparkles, no flash, no magical-girl effects. Casual like a window being resized. "
        "BOTTOM HALF: A young woman stands where the raven was. "
        "Black FEATHERS as hair cascading past shoulders with iridescent sheen. "
        "Black wings folded against back. Dark scholarly robes. "
        "Polished obsidian mineral eyes IDENTICAL to the raven above, unchanged. "
        "She extends one hand. Expression: mildly annoyed, practical. "
        "Crystal archive background continuous between both halves. "
        "Mood: casual precision, utility not spectacle, a window resize not a power-up. "
        "High quality digital art.",
    },
    "p23": {
        "title": "The Handshake — Macro Detail",
        "aspect": "16:9",
        "prompt": STYLE + WARM_ARCHIVE +
        "MACRO CLOSE-UP of two hands clasping. "
        "Scene: A man's hand gripping a woman's hand. Her grip is stronger than expected. "
        "Her fingers are slightly too long, nails dark and faintly iridescent. "
        "His hand is a keyboard hand, long fingers, slightly pale. "
        "Warm amber crystal light illuminates the handshake from behind. "
        "Camera: tight macro on the hands only. "
        "Mood: first physical connection, trust as grip, warm solid real. "
        "High quality digital art.",
    },
    "p24": {
        "title": "Breathing — Two Shadows Walking",
        "aspect": "16:9",
        "prompt": STYLE + WARM_CORRIDOR +
        "BREATHING PANEL, atmospheric transition. "
        "Scene: Two shadows cast on a translucent crystal floor. One shadow has wings. "
        "The shadows walk side by side through warm amber light. No characters visible, just shadows. "
        "Crystal floor refracts the light into subtle prismatic patterns around the shadows. "
        "Camera: looking down at the floor, abstract. "
        "Mood: transition from stranger to guide, the journey beginning. "
        "High quality digital art.",
    },

    # ══════════════════════════════════════════
    # SCENE 7: THE WORLD (Shots 25-30)
    # ══════════════════════════════════════════
    "p25": {
        "title": "We Have Infrastructure — Corridor",
        "aspect": "3:4",
        "prompt": STYLE + WARM_CORRIDOR + MARCUS + POLLY_HUMAN +
        "Scene: Crystal corridor stretching into the distance. "
        "Polly walks ahead in dark formal robes, wings folded neatly, footsteps silent on stone. "
        "Her wings are slightly spread, catching crystal light in prismatic fragments. "
        "Marcus follows behind her, leaning forward as he walks, studying the environment. "
        "The floor looks transparent but holds weight. A doorway glows ahead, appearing as they approach. "
        "Camera: medium shot from behind both characters, corridor stretching ahead. "
        "Mood: infrastructure not scenery, a serious universe with systems. "
        "High quality digital art.",
    },
    "p26": {
        "title": "The Impossible — Aethermoor Reveal",
        "aspect": "9:16",
        "prompt": STYLE + AETHERMOOR_EXT +
        "TALL VERTICAL SPLASH PANEL, the chapter's visual climax, a painting worthy of a wall. "
        "Scene: View through a gap in a crystal corridor wall looking out at an impossible landscape. "
        "A sky lined with soft auroral light in violet and gold, pulsing gently. "
        "Below: a river of pale blue LUMINESCENCE winds between structures that are part building part mountain. "
        "Several landmasses FLOAT in the air without visible mechanism, gravity simply paused mid-sentence. "
        "On the UNDERSIDES of floating landmasses, meadows grow with grass pointing DOWNWARD. "
        "A bridge of crystal arcs between two floating masses, something with too many legs crosses it purposefully. "
        "The world feels impossible but COHERENT, designed, inhabited, structural. "
        "Crystal corridor walls frame the view on both sides like a window. "
        "Camera: wide, looking out, the reader stops scrolling and stares. "
        "Mood: world-shock not postcard beauty. Impossible and inhabited at once. "
        "High quality digital art.",
    },
    "p27": {
        "title": "Marcus Stops Walking — Awe",
        "aspect": "1:1",
        "prompt": STYLE + AETHERMOOR_EXT + MARCUS +
        "Scene: Close-up of Marcus's face in profile, looking out at something breathtaking off-screen. "
        "Violet-gold auroral light illuminates his face from the side. Wind moves his hair slightly. "
        "His mouth is slightly open. Eyes wide. Expression of pure awe mixed with disbelief. "
        "He has stopped walking mid-stride. "
        "Camera: close-up profile, auroral light painting his face. "
        "Mood: the moment the impossible becomes real, felt in the sternum. "
        "High quality digital art.",
    },
    "p28": {
        "title": "Caw-fee — Dialogue Comedy",
        "aspect": "3:4",
        "prompt": STYLE + WARM_CORRIDOR + MARCUS + POLLY_HUMAN +
        "Scene: Polly has stopped mid-stride in a crystal corridor and turned around, "
        "her head tilted at a sharp bird-like angle, genuine confusion on her face. "
        "Marcus faces her, rubbing the back of his neck with one hand, "
        "a small half-smile on his face for the first time in the chapter. "
        "Crystal corridor behind them, warm amber light. "
        "The energy between them has shifted from guide and subject toward something more equal. "
        "She is confused by something he said. He is amused for the first time. "
        "Camera: medium two-shot, eye level, both characters facing each other. "
        "Mood: the relief valve, humor as human tether, coffee as Earth. "
        "High quality digital art.",
    },
    "p29": {
        "title": "Following Polly — Medium Walking",
        "aspect": "3:4",
        "prompt": STYLE + WARM_CORRIDOR + MARCUS + POLLY_HUMAN +
        "Scene: Polly walking ahead through a crystal corridor, Marcus following. "
        "Polly is slightly ahead and to the left, dark robes flowing, wings folded. "
        "Marcus is a step behind on the right, hands in hoodie pockets, still processing. "
        "The corridor ahead glows with warm amber light, crystal walls catching prismatic refractions. "
        "They are walking deeper into a world he does not understand yet. "
        "Camera: medium shot from behind, the path stretches ahead. "
        "Mood: moving forward because there is nothing else to do. "
        "High quality digital art.",
    },
    "p30": {
        "title": "A Biscuit For The Bird — Closing",
        "aspect": "3:4",
        "prompt": STYLE + WARM_CORRIDOR + MARCUS +
        "Scene: Marcus glancing back over his shoulder in a crystal corridor. "
        "Warm amber light glows ahead of him where Polly has already walked on. "
        "Behind him is the darkness of where he arrived. "
        "His expression is complex: loss, determination, a trace of wry humor. "
        "He is leaving the spot where he landed, following someone he just met into the impossible. "
        "He wishes he had coffee and a biscuit for the bird. "
        "Camera: over-shoulder, looking back the way he came, light ahead. "
        "Mood: the chapter closes on fragile human continuity, not spectacle. The ache of transition. "
        "High quality digital art.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Chapter 1 v3 panels with Imagen.")
    parser.add_argument("panels", nargs="*", help="Optional panel ids such as p01 p12 p26")
    parser.add_argument(
        "--tier",
        choices=sorted(MODEL_BY_TIER.keys()),
        default=DEFAULT_TIER,
        help="Imagen quality tier to use",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the model id directly. If omitted, tier decides the model.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Optional output directory. Defaults to artifacts/webtoon/ch01/v3 or a tier-specific subdir when using non-standard tiers.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate panels even if the target file already exists.",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=2.0,
        help="Delay between generation calls.",
    )
    return parser.parse_args()


def resolve_out_dir(args: argparse.Namespace) -> Path:
    if args.out_dir:
        return Path(args.out_dir)
    if args.tier == DEFAULT_TIER and not args.model:
        return DEFAULT_OUT_DIR
    suffix = args.tier if not args.model else args.model.replace("/", "__").replace(":", "_")
    return DEFAULT_OUT_DIR / suffix


def generate(panel_id, data, *, out_dir: Path, model: str, force: bool):
    path = out_dir / f"ch01-v3-{panel_id}.png"
    if path.exists() and not force:
        print(f"  SKIP {panel_id} (exists)")
        return "SKIP"
    print(f"  GEN  {panel_id}: {data['title']} [{data['aspect']}]")
    try:
        result = client.models.generate_images(
            model=model,
            prompt=data["prompt"],
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio=data["aspect"],
            ),
        )
        if result.generated_images:
            with open(path, "wb") as f:
                f.write(result.generated_images[0].image.image_bytes)
            from PIL import Image
            img = Image.open(path)
            print(f"  OK   {img.size[0]}x{img.size[1]}")
            return "OK"
        else:
            print(f"  FAIL no image returned")
            return "FAIL"
    except Exception as e:
        print(f"  ERR  {e}")
        return f"ERR: {e}"


def main():
    args = parse_args()
    model = args.model or MODEL_BY_TIER[args.tier]
    out_dir = resolve_out_dir(args)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = args.panels if args.panels else sorted(PANELS.keys())
    print(f"Chapter 1 v3 Full Generation — {len(targets)} panels")
    print(f"Tier: {args.tier}")
    print(f"Model: {model}")
    print(f"Output: {out_dir}\n")

    results = {}
    for pid in targets:
        if pid not in PANELS:
            print(f"  UNKNOWN: {pid}")
            continue
        results[pid] = generate(pid, PANELS[pid], out_dir=out_dir, model=model, force=args.force)
        time.sleep(args.sleep_sec)

    print("\n=== RESULTS ===")
    ok = sum(1 for v in results.values() if v == "OK")
    skip = sum(1 for v in results.values() if v == "SKIP")
    fail = sum(1 for v in results.values() if v not in ("OK", "SKIP"))
    for pid, status in sorted(results.items()):
        print(f"  {pid}: {status}")
    print(f"\nTotal: {ok} OK, {skip} SKIP, {fail} FAIL")

    log = {"model": model, "tier": args.tier, "style_version": "v3", "panels": {
        pid: {"title": PANELS[pid]["title"], "aspect": PANELS[pid]["aspect"], "result": results.get(pid)}
        for pid in targets if pid in PANELS
    }}
    log_path = out_dir / "generation_log.json"
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
