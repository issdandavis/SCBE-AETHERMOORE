#!/usr/bin/env python3
"""
Aethermoor Expanded Scene Library — 33 scenes, 180+ choices, full 14-layer coverage.
Compact data-driven format for the Six Tongues Protocol game engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

# ── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class LayerTag:
    layer: int; name: str; desc: str

@dataclass
class EChoice:
    cid: str; label: str; next_scene: str; tongue: str
    layers: List[LayerTag]; stats: Dict[str, float] = field(default_factory=dict)
    difficulty: float = 0.0; risk: str = "safe"
    opinions: Dict[str, str] = field(default_factory=dict)

@dataclass
class EScene:
    sid: str; title: str; text: str; location: str; time: str; bg: str
    chars: List[str]; choices: List[EChoice]
    entry: bool = False; exit: bool = False; mood: str = "neutral"

# ── Helpers ──────────────────────────────────────────────────────────────────

def L(n, name, desc): return LayerTag(n, name, desc)
def C(cid, label, nxt, tongue, layers, **kw): return EChoice(cid, label, nxt, tongue, layers, **kw)
def S(sid, title, text, loc, time, bg, chars, choices, **kw): return EScene(sid, title, text, loc, time, bg, chars, choices, **kw)

# Shortcut opinion dicts
def _op(p=None, c=None, e=None, a=None, z=None, k=None):
    d = {}
    if p: d["Polly"] = p
    if c: d["Clay"] = c
    if e: d["Eldrin"] = e
    if a: d["Aria"] = a
    if z: d["Zara"] = z
    if k: d["Kael"] = k
    return d

# ── Arc 1: Earth (5 scenes) ─────────────────────────────────────────────────

_earth = [
    S("earth_morning", "Morning Routine", "Sunlight breaks through your apartment window. Your phone buzzes with messages — work deadlines, friend requests, news alerts. The ordinary world presses in.", "apartment", "dawn", "apartment", ["Izack"],
      [C("em1","Check news feeds carefully","earth_work","AV",[L(1,"Intent","Parse morning intent from noise"),L(3,"Context","Build daily context from news")],stats={"AV":0.05},opinions=_op(p="The Protocol demands we filter before we consume.",c="Morning is safe time.")),
       C("em2","Meditate before anything","earth_work","RU",[L(4,"Memory","Anchor yesterday's lessons"),L(9,"Spectral","Tune inner frequency before external noise")],stats={"RU":0.05},opinions=_op(e="There might be something beyond the silence...",a="The boundary math suggests centering first.")),
       C("em3","Rush out the door","earth_work","CA",[L(7,"Compute","React-first processing"),L(2,"Routing","Skip routing, direct action")],stats={"CA":0.03},risk="moderate",opinions=_op(z="I can build a workaround for lost time.",c="Rush is not safe.")),
       C("em4","Journal your dreams","earth_work","DR",[L(4,"Memory","Encode dream-state memories"),L(11,"Schema","Structure subconscious data")],stats={"DR":0.05},opinions=_op(k="There's always another way to remember.",p="Recording is wisdom.")),
       C("em5","Call a friend","earth_work","KO",[L(12,"Auth","Verify trust before sharing"),L(14,"Integration","Integrate external perspective")],stats={"KO":0.05},opinions=_op(a="The boundary math suggests allies early.",z="Connection is infrastructure."))],
      entry=True, mood="hopeful"),

    S("earth_work", "The Daily Grind", "Your desk is piled with tasks. A colleague asks for help on a project that conflicts with your own deadline. The fluorescent lights hum overhead.", "office", "morning", "apartment", ["Izack"],
      [C("ew1","Help the colleague first","earth_evening","KO",[L(1,"Intent","Prioritize collaborative intent"),L(6,"Policy","Apply aid-before-self policy")],stats={"KO":0.05},opinions=_op(p="The Protocol says: serve the network.",c="Helping is good. I like helping.")),
       C("ew2","Negotiate a compromise","earth_evening","AV",[L(2,"Routing","Route effort across two tasks"),L(5,"Constraints","Balance competing constraints")],stats={"AV":0.05},opinions=_op(e="There might be something beyond either-or.",a="The boundary math suggests splitting.")),
       C("ew3","Focus on your own work","earth_evening","DR",[L(7,"Compute","Allocate all compute to priority"),L(5,"Constraints","Honor self-constraint")],stats={"DR":0.03},risk="moderate",opinions=_op(z="I can build a workaround later.",k="There's always another way.")),
       C("ew4","Automate the boring parts","earth_evening","CA",[L(7,"Compute","Optimize with automation"),L(11,"Schema","Schema-ify repetitive work")],stats={"CA":0.05},opinions=_op(z="I can build a workaround for everything!",e="There might be something beyond manual labor...")),
       C("ew5","Report the conflict to management","earth_evening","UM",[L(13,"Governance","Escalate to governance layer"),L(12,"Auth","Authenticate the complaint chain")],stats={"UM":0.03},risk="moderate",opinions=_op(p="The Protocol demands transparency.",a="The boundary math suggests escalation."))]),

    S("earth_evening", "Evening Crossroads", "Home again. A strange email sits in your inbox — symbols you almost recognize. The TV flickers with news of unexplained atmospheric phenomena.", "apartment", "evening", "apartment", ["Izack"],
      [C("ee1","Study the symbols carefully","earth_night","RU",[L(3,"Context","Decode symbol context"),L(9,"Spectral","Spectral analysis of glyph frequency")],stats={"RU":0.05},opinions=_op(e="There might be something beyond those glyphs...",p="The Protocol demands caution here.")),
       C("ee2","Delete the email, watch TV","earth_night","UM",[L(8,"Encrypt","Reject unverified payload"),L(5,"Constraints","Stay within known constraints")],stats={"UM":0.03},opinions=_op(c="Safe is good. I like safe.",k="There's always another way to find truth.")),
       C("ee3","Forward it to a cryptographer friend","earth_night","KO",[L(12,"Auth","Verify via trusted third party"),L(14,"Integration","Integrate expert perspective")],stats={"KO":0.05},opinions=_op(a="The boundary math suggests collaboration.",z="I can build a workaround with the right people.")),
       C("ee4","Try to reply in the same symbols","earth_night","CA",[L(7,"Compute","Pattern-match and generate response"),L(10,"Quantum","Probabilistic symbol completion")],stats={"CA":0.05},risk="moderate",opinions=_op(e="There might be something beyond imitation.",k="There's always another way to communicate.")),
       C("ee5","Search online for the symbols","earth_night","AV",[L(2,"Routing","Route query through search"),L(3,"Context","Gather web context")],stats={"AV":0.05},opinions=_op(z="I can build a workaround with data.",p="The Protocol says: gather before acting."))]),

    S("earth_night", "The Tremor", "At 3 AM the apartment shakes. Not an earthquake — the air itself ripples. The symbols from the email glow on your wall. A door that wasn't there stands open, leading into impossible violet light.", "apartment", "night", "apartment", ["Izack"],
      [C("en1","Step through immediately","earth_crisis","CA",[L(1,"Intent","Pure exploratory intent"),L(7,"Compute","Instant decision compute")],stats={"CA":0.05},risk="risky",opinions=_op(e="There might be something beyond that door...",c="Not safe. But... bright.")),
       C("en2","Gather supplies first","earth_crisis","DR",[L(6,"Policy","Preparation policy"),L(4,"Memory","Pack based on memory of needs")],stats={"DR":0.05},opinions=_op(p="The Protocol demands preparation.",z="I can build a workaround with the right gear.")),
       C("en3","Try to close the portal","earth_crisis","UM",[L(8,"Encrypt","Seal the breach"),L(13,"Governance","Apply containment governance")],stats={"UM":0.05},risk="moderate",opinions=_op(a="The boundary math suggests containment.",p="The Protocol demands caution here.")),
       C("en4","Document everything on your phone","earth_crisis","AV",[L(11,"Schema","Structure observations"),L(3,"Context","Record full context")],stats={"AV":0.05},opinions=_op(z="Evidence is infrastructure.",k="There's always another way to prove it.")),
       C("en5","Call out into the light","earth_crisis","KO",[L(12,"Auth","Authenticate what responds"),L(1,"Intent","Broadcast intent to unknown")],stats={"KO":0.03},risk="risky",opinions=_op(k="There's always another way to make first contact.",e="There might be something beyond the silence..."))]),

    S("earth_crisis", "Point of No Return", "The portal pulses faster. Your apartment begins to dissolve at the edges. Whatever you choose, Earth as you knew it is ending.", "apartment", "night", "apartment", ["Izack"],
      [C("ec1","Leap through with faith","transit_fall","KO",[L(1,"Intent","Commit full intent"),L(14,"Integration","Integrate self with unknown")],stats={"KO":0.1},risk="dangerous",opinions=_op(p="The Protocol says: trust the framework.",c="Jump together?")),
       C("ec2","Grab the glowing symbols first","transit_fall","RU",[L(4,"Memory","Preserve ancestral data"),L(9,"Spectral","Read spectral signature")],stats={"RU":0.1},opinions=_op(e="There might be something beyond the symbols...",a="The boundary math suggests taking the key.")),
       C("ec3","Shield yourself with logic","transit_fall","AV",[L(8,"Encrypt","Encrypt personal boundary"),L(5,"Constraints","Maintain self-constraints in transit")],stats={"AV":0.1},opinions=_op(a="The boundary math suggests shielding.",z="I can build a workaround for gravity.")),
       C("ec4","Let the dissolution take you","transit_fall","UM",[L(10,"Quantum","Accept quantum indeterminacy"),L(13,"Governance","Surrender to larger governance")],stats={"UM":0.1},risk="dangerous",opinions=_op(k="There's always another way... or is there?",p="The Protocol demands we trust the process.")),
       C("ec5","Reach for your phone — one last message","transit_fall","DR",[L(11,"Schema","Encode final message"),L(6,"Policy","Apply last-will policy")],stats={"DR":0.1},opinions=_op(c="I like messages. Send good one.",z="Data persists."))]),
]

# ── Arc 2: Transit (3 scenes) ───────────────────────────────────────────────

_transit = [
    S("transit_fall", "The Fall Between Worlds", "You tumble through corridors of light. Memories flash — childhood, first love, last meal. Six colors weave around you: red, cyan, gold, green, purple, orange. Each one whispers in a language you almost understand.", "void", "timeless", "forest", ["Izack"], [], mood="wonder"),

    S("transit_choice", "The Six Paths", "The colors solidify into six paths stretching into darkness. Each hums with a distinct frequency. Feathered shapes and earthen forms coalesce beside you — companions forming from the light itself.", "void", "timeless", "forest", ["Izack","Polly","Clay"],
      [C("tc1","Follow the red path (authority)","transit_landing","KO",[L(1,"Intent","Choose authority intent"),L(13,"Governance","Accept governance mantle")],stats={"KO":0.1},opinions=_op(p="The Protocol demands we lead.",a="The boundary math suggests command.")),
       C("tc2","Follow the cyan path (transport)","transit_landing","AV",[L(2,"Routing","Choose routing mastery"),L(3,"Context","Read contextual currents")],stats={"AV":0.1},opinions=_op(e="There might be something beyond every horizon.",c="Cyan feels safe.")),
       C("tc3","Follow the gold path (memory)","transit_landing","RU",[L(4,"Memory","Choose ancestral memory"),L(9,"Spectral","Attune to spectral echoes")],stats={"RU":0.1},opinions=_op(p="The Protocol honors the ancestors.",k="There's always another way to remember.")),
       C("tc4","Follow the green path (creation)","transit_landing","CA",[L(7,"Compute","Choose creative compute"),L(11,"Schema","Build from schema")],stats={"CA":0.1},opinions=_op(z="I can build a workaround for anything on this path!",e="There might be something beyond creation itself.")),
       C("tc5","Follow the purple path (shadow)","transit_landing","UM",[L(8,"Encrypt","Choose encryption mastery"),L(10,"Quantum","Accept quantum shadow")],stats={"UM":0.1},risk="moderate",opinions=_op(k="There's always another way in the dark.",a="The boundary math suggests caution.")),
       C("tc6","Weave all six together","transit_landing","MULTI",[L(14,"Integration","Integrate all six tongues"),L(6,"Policy","Unified policy across tongues"),L(5,"Constraints","Balance six-fold constraints")],stats={"KO":0.03,"AV":0.03,"RU":0.03,"CA":0.03,"UM":0.03,"DR":0.03},difficulty=0.8,risk="risky",opinions=_op(p="The Protocol has never seen this attempted.",z="I can build a workaround if the weave frays."))]),

    S("transit_landing", "Arrival in Aethermoor", "You crash through a canopy of luminescent leaves onto soft moss. Floating islands drift in a violet sky. A raven lands on your shoulder. A small golem forms from the earth beside you. Welcome to Aethermoor.", "aethermoor", "twilight", "island", ["Izack","Polly","Clay"],
      [C("tl1","Ask Polly where you are","academy_arrival","AV",[L(3,"Context","Gather local context"),L(2,"Routing","Route via familiar guide")],stats={"AV":0.05},opinions=_op(p="The Protocol says I am your archive now.",c="New dirt! Good dirt!")),
       C("tl2","Explore the immediate area","academy_arrival","CA",[L(9,"Spectral","Scan spectral environment"),L(7,"Compute","Process new sensory data")],stats={"CA":0.05},opinions=_op(e="There might be something beyond those trees...",z="I can build a workaround for being lost.")),
       C("tl3","Meditate to ground yourself","academy_arrival","RU",[L(4,"Memory","Anchor self in memory"),L(1,"Intent","Clarify intent in new world")],stats={"RU":0.05},opinions=_op(p="The Protocol demands centering.",k="There's always another way to find yourself.")),
       C("tl4","Fortify your landing spot","academy_arrival","DR",[L(6,"Policy","Establish perimeter policy"),L(8,"Encrypt","Encrypt camp boundary")],stats={"DR":0.05},opinions=_op(a="The boundary math suggests defense first.",c="Safe is good. I like safe.")),
       C("tl5","Try to sense other people","academy_arrival","KO",[L(12,"Auth","Authenticate nearby presences"),L(10,"Quantum","Quantum-sense life signatures")],stats={"KO":0.05},opinions=_op(k="There's always another way to find allies.",e="There might be something beyond the clearing..."))]),
]

# ── Arc 3: Academy (8 scenes) ───────────────────────────────────────────────

_academy = [
    S("academy_arrival", "Avalon Academy Gates", "Towering spires of crystallized language rise before you. Eldrin, a cartographer with ink-stained hands, waves from the gate. Aria stands guard, equations shimmering on her blade.", "academy", "morning", "academy", ["Izack","Polly","Clay","Eldrin","Aria"],
      [C("aa1","Greet Eldrin warmly","academy_lesson","KO",[L(12,"Auth","Authenticate new ally"),L(1,"Intent","Broadcast friendly intent")],stats={"KO":0.05},opinions=_op(e="There might be something beyond formalities!",p="The Protocol approves of proper introductions.")),
       C("aa2","Ask Aria about defenses","academy_lesson","DR",[L(5,"Constraints","Learn constraint boundaries"),L(8,"Encrypt","Study encryption wards")],stats={"DR":0.05},opinions=_op(a="The boundary math suggests you ask the right questions.",z="I can build a workaround once I understand the specs.")),
       C("aa3","Examine the crystal spires","academy_lesson","RU",[L(9,"Spectral","Analyze crystal spectral resonance"),L(11,"Schema","Read architectural schema")],stats={"RU":0.05},opinions=_op(e="There might be something beyond the surface patterns.",p="The Protocol is encoded in those crystals.")),
       C("aa4","Let Polly scout ahead","academy_lesson","AV",[L(2,"Routing","Aerial route scouting"),L(3,"Context","Gather overhead context")],stats={"AV":0.05},opinions=_op(p="The Protocol demands reconnaissance.",c="Polly flies good.")),
       C("aa5","Enter boldly","academy_lesson","CA",[L(7,"Compute","Fast-path entry processing"),L(1,"Intent","Assert presence intent")],stats={"CA":0.03},risk="moderate",opinions=_op(k="There's always another way to make an entrance.",a="The boundary math suggests... well, boldness has a formula."))]),

    S("academy_lesson", "First Tongue Lesson", "Professor Tharn draws six glowing circles in the air. 'Each Tongue carries a piece of the world's operating system,' she says. 'Today you learn to hear them.'", "academy", "midday", "academy", ["Izack","Polly","Clay","Eldrin"],
      [C("al1","Focus on Kor'aelin (authority)","academy_training","KO",[L(1,"Intent","Learn authoritative intent"),L(13,"Governance","Study governance tongue")],stats={"KO":0.1},opinions=_op(p="The Protocol begins with command.",a="The boundary math suggests leadership first.")),
       C("al2","Focus on Avali (transport)","academy_training","AV",[L(2,"Routing","Learn routing tongue"),L(14,"Integration","Study integration pathways")],stats={"AV":0.1},opinions=_op(e="There might be something beyond every route.",c="Gentle sounds.")),
       C("al3","Focus on Runethic (memory)","academy_training","RU",[L(4,"Memory","Learn memory tongue"),L(9,"Spectral","Study spectral memory encoding")],stats={"RU":0.1},opinions=_op(p="The Protocol honors ancestral memory.",k="There's always another way to remember.")),
       C("al4","Focus on Cassisivadan (creation)","academy_training","CA",[L(7,"Compute","Learn creative compute"),L(11,"Schema","Study generative schema")],stats={"CA":0.1},opinions=_op(z="I can build a workaround for everything with this!",e="There might be something beyond imagination.")),
       C("al5","Try to hear all six at once","academy_training","MULTI",[L(14,"Integration","Integrate all tongue frequencies"),L(10,"Quantum","Quantum superposition of tongues"),L(5,"Constraints","Balance six-fold input")],stats={"KO":0.02,"AV":0.02,"RU":0.02,"CA":0.02,"UM":0.02,"DR":0.02},difficulty=0.7,risk="moderate",opinions=_op(p="The Protocol has never prescribed this approach.",z="I can build a workaround if your ears bleed."))]),

    S("academy_training", "The Training Grounds", "Zara joins you on the practice field, dragon-fire dancing at her fingertips. 'Theory is nothing without practice,' she grins. Stone dummies await.", "academy", "afternoon", "arena", ["Izack","Polly","Clay","Zara","Aria"],
      [C("at1","Spar with Aria (martial)","academy_library","DR",[L(5,"Constraints","Learn combat constraints"),L(7,"Compute","Real-time battle compute")],stats={"DR":0.05},risk="moderate",opinions=_op(a="The boundary math suggests you'll lose. Good practice.",z="I can build a workaround for bruises.")),
       C("at2","Build with Zara (engineering)","academy_library","CA",[L(11,"Schema","Engineer defensive schema"),L(7,"Compute","Applied creative compute")],stats={"CA":0.05},opinions=_op(z="I can build a workaround AND an upgrade!",c="Building is good. I like building.")),
       C("at3","Practice tongue pronunciation","academy_library","RU",[L(9,"Spectral","Tune vocal spectral output"),L(4,"Memory","Memorize phonetic patterns")],stats={"RU":0.05},opinions=_op(p="The Protocol demands precision.",e="There might be something beyond mere pronunciation.")),
       C("at4","Meditative combat forms","academy_library","UM",[L(8,"Encrypt","Encrypt combat intentions"),L(10,"Quantum","Quantum-state fighting stance")],stats={"UM":0.05},opinions=_op(k="There's always another way to fight without fighting.",a="The boundary math suggests inner strength.")),
       C("at5","Run the obstacle course","academy_library","AV",[L(2,"Routing","Dynamic route optimization"),L(6,"Policy","Apply traversal policy")],stats={"AV":0.05},opinions=_op(e="There might be something beyond the finish line!",c="Running! Fun!"))]),

    S("academy_library", "The Wingscroll Archive", "Polly leads you to a vast library where books fly between shelves on feathered wings. Ancient tomes pulse with tongue-encoded knowledge. A restricted section glows behind wards.", "academy", "evening", "academy", ["Izack","Polly","Eldrin"],
      [C("ab1","Research the Spiral Spire","academy_rivalry","RU",[L(4,"Memory","Access historical memory"),L(3,"Context","Build expedition context")],stats={"RU":0.05},opinions=_op(p="The Protocol says knowledge precedes action.",e="There might be something beyond the known maps.")),
       C("ab2","Study defensive wards","academy_rivalry","UM",[L(8,"Encrypt","Learn ward encryption"),L(13,"Governance","Study governance seals")],stats={"UM":0.05},opinions=_op(a="The boundary math suggests understanding defenses.",k="There's always another way past a ward.")),
       C("ab3","Sneak into restricted section","academy_rivalry","CA",[L(12,"Auth","Bypass authentication"),L(7,"Compute","Compute bypass route")],stats={"CA":0.05},risk="risky",opinions=_op(k="There's always another way in.",p="The Protocol FORBIDS unauthorized access!")),
       C("ab4","Ask Polly to translate old texts","academy_rivalry","AV",[L(2,"Routing","Route through Polly's knowledge"),L(11,"Schema","Parse ancient schema")],stats={"AV":0.05},opinions=_op(p="The Protocol demands proper translation.",e="There might be something beyond literal meaning.")),
       C("ab5","Catalog what you've learned so far","academy_rivalry","DR",[L(11,"Schema","Structure knowledge schema"),L(6,"Policy","Apply information management policy")],stats={"DR":0.05},opinions=_op(z="I can build a workaround for forgetfulness.",c="Writing things down. Smart."))]),

    S("academy_rivalry", "Kael's Challenge", "A figure in shadow-woven robes blocks your path. Kael Nightwhisper — your son from a life you barely remember. 'You don't belong here,' he says, but his eyes say something else entirely.", "academy", "night", "academy", ["Izack","Polly","Kael"],
      [C("ar1","Embrace him","academy_test","KO",[L(1,"Intent","Broadcast unconditional intent"),L(12,"Auth","Authenticate blood bond")],stats={"KO":0.1},opinions=_op(p="The Protocol says: trust the bond.",c="Family is safe.")),
       C("ar2","Challenge him to a duel","academy_test","DR",[L(5,"Constraints","Accept combat constraints"),L(7,"Compute","Battle compute engaged")],stats={"DR":0.05},risk="moderate",opinions=_op(a="The boundary math suggests he's stronger than you.",z="I can build a workaround for father-son issues.")),
       C("ar3","Ask why he's angry","academy_test","AV",[L(3,"Context","Gather emotional context"),L(1,"Intent","Clarify his intent")],stats={"AV":0.05},opinions=_op(e="There might be something beyond the anger...",k="There's always another way... father.")),
       C("ar4","Read his shadow-tongue aura","academy_test","UM",[L(9,"Spectral","Spectral read of shadow frequency"),L(10,"Quantum","Quantum entanglement scan")],stats={"UM":0.1},opinions=_op(p="The Protocol demands we understand before we judge.",k="There's always another way to see me.")),
       C("ar5","Walk away silently","academy_test","RU",[L(6,"Policy","Apply non-engagement policy"),L(4,"Memory","Let memory speak later")],stats={"RU":0.05},risk="moderate",opinions=_op(c="Leaving is safe... but sad.",p="The Protocol permits strategic retreat."))]),

    S("academy_test", "The Tongue Examination", "The Academy's great hall fills with light as six crystals rise from the floor. 'Speak to each crystal in its Tongue,' the examiner says. 'Your resonance determines your path.'", "academy", "dawn", "academy", ["Izack","Polly","Clay","Eldrin","Aria","Zara"],
      [C("ax1","Speak with authority (KO)","academy_incident","KO",[L(13,"Governance","Assert governance authority"),L(1,"Intent","Command intent")],stats={"KO":0.1},opinions=_op(p="The Protocol demands a clear voice.",a="The boundary math suggests confidence.")),
       C("ax2","Speak with gentleness (AV)","academy_incident","AV",[L(2,"Routing","Gentle routing of energy"),L(14,"Integration","Integrate with crystal softly")],stats={"AV":0.1},opinions=_op(c="Soft is nice.",e="There might be something beyond force.")),
       C("ax3","Speak with memory (RU)","academy_incident","RU",[L(4,"Memory","Channel ancestral voice"),L(9,"Spectral","Match crystal spectral memory")],stats={"RU":0.1},opinions=_op(p="The Protocol remembers all who came before.",k="There's always another way to be heard.")),
       C("ax4","Speak with invention (CA)","academy_incident","CA",[L(7,"Compute","Creative compute expression"),L(11,"Schema","Generate novel schema")],stats={"CA":0.1},opinions=_op(z="I can build a workaround that becomes an invention!",e="There might be something beyond the curriculum.")),
       C("ax5","Speak with shadow (UM)","academy_incident","UM",[L(8,"Encrypt","Encrypt-speak in shadow"),L(10,"Quantum","Quantum shadow resonance")],stats={"UM":0.1},risk="moderate",opinions=_op(k="There's always another way in the dark.",a="The boundary math suggests... unexpected results."))]),

    S("academy_incident", "The Ward Breach", "Alarms shatter the night. The restricted section's wards have failed. Shadow-creatures pour through cracks in reality. The Academy mobilizes.", "academy", "night", "academy", ["Izack","Polly","Clay","Aria","Zara","Kael"],
      [C("ai1","Join the defensive line","academy_choice","DR",[L(5,"Constraints","Combat constraint adherence"),L(13,"Governance","Emergency governance protocol")],stats={"DR":0.1},opinions=_op(a="The boundary math suggests holding the line.",c="Fight together!")),
       C("ai2","Seal the breach yourself","academy_choice","UM",[L(8,"Encrypt","Emergency ward encryption"),L(10,"Quantum","Quantum seal generation")],stats={"UM":0.1},risk="risky",opinions=_op(z="I can build a workaround for the broken wards!",p="The Protocol demands containment.")),
       C("ai3","Evacuate the students","academy_choice","KO",[L(1,"Intent","Protective leadership intent"),L(6,"Policy","Apply evacuation policy")],stats={"KO":0.1},opinions=_op(p="The Protocol prioritizes lives.",c="Safe is good. Everyone safe.")),
       C("ai4","Analyze the creatures' weakness","academy_choice","AV",[L(3,"Context","Context-scan threat data"),L(9,"Spectral","Spectral vulnerability analysis")],stats={"AV":0.1},opinions=_op(e="There might be something beyond brute force.",a="The boundary math suggests study before strike.")),
       C("ai5","Rally Kael to fight beside you","academy_choice","KO",[L(12,"Auth","Authenticate shared purpose"),L(14,"Integration","Integrate estranged ally")],stats={"KO":0.05,"UM":0.05},opinions=_op(k="There's always another way... together, maybe.",p="The Protocol says: all hands now."))]),

    S("academy_choice", "The Academy's Verdict", "Dawn breaks over a battered Academy. The breach is sealed but the damage is real. The elders offer you a choice: stay and rebuild, or journey to the Spiral Spire to find the source.", "academy", "dawn", "academy", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("ac1","Stay and rebuild","spire_approach","DR",[L(6,"Policy","Apply reconstruction policy"),L(14,"Integration","Integrate repair efforts")],stats={"DR":0.1},opinions=_op(z="I can build a workaround for everything broken.",c="Building is good.")),
       C("ac2","Journey to the Spire immediately","spire_approach","CA",[L(2,"Routing","Plot route to Spire"),L(7,"Compute","Compute fastest path")],stats={"CA":0.1},opinions=_op(e="There might be something beyond the Academy walls!",a="The boundary math suggests striking while the trail is fresh.")),
       C("ac3","Send scouts first","spire_approach","AV",[L(3,"Context","Advance context gathering"),L(2,"Routing","Multi-route scouting")],stats={"AV":0.1},opinions=_op(p="The Protocol demands reconnaissance.",k="There's always another way to learn the terrain.")),
       C("ac4","Consult the restricted texts","spire_approach","RU",[L(4,"Memory","Access forbidden memory"),L(11,"Schema","Read ancient schema")],stats={"RU":0.1},opinions=_op(p="The Protocol now permits access.",e="There might be something beyond the obvious texts.")),
       C("ac5","Ask Kael what the shadows told him","spire_approach","UM",[L(9,"Spectral","Read shadow spectral data"),L(10,"Quantum","Quantum shadow interrogation")],stats={"UM":0.1},opinions=_op(k="There's always another way to hear the dark.",a="The boundary math suggests using every source."))]),
]

# ── Arc 4: Spiral Spire (7 scenes) ──────────────────────────────────────────

_spire = [
    S("spire_approach", "The Spiral Spire", "It rises from a floating island like a frozen tornado — the Spiral Spire, where reality folds in on itself. Each floor tests a different layer of understanding.", "wilderness", "midday", "island", ["Izack","Polly","Clay","Eldrin","Aria"],
      [C("sa1","Approach directly","spire_guardian","DR",[L(1,"Intent","Direct approach intent"),L(5,"Constraints","Accept the Spire's constraints")],stats={"DR":0.05},opinions=_op(a="The boundary math suggests the front door.",c="Big tower. Very big.")),
       C("sa2","Scout the perimeter","spire_guardian","AV",[L(2,"Routing","Perimeter route scan"),L(3,"Context","Environmental context mapping")],stats={"AV":0.05},opinions=_op(e="There might be something beyond the obvious entrance.",p="The Protocol demands reconnaissance.")),
       C("sa3","Attune to the Spire's frequency","spire_guardian","RU",[L(9,"Spectral","Spectral attunement to structure"),L(4,"Memory","Access structural memory")],stats={"RU":0.05},opinions=_op(p="The Protocol says: listen before entering.",k="There's always another way to hear stone speak.")),
       C("sa4","Build a base camp","spire_guardian","CA",[L(11,"Schema","Camp schema design"),L(7,"Compute","Resource allocation compute")],stats={"CA":0.05},opinions=_op(z="I can build a workaround for comfort!",c="Safe camp. Good.")),
       C("sa5","Send Polly to the top","spire_guardian","KO",[L(13,"Governance","Delegate authority to scout"),L(2,"Routing","Aerial fast-route")],stats={"KO":0.05},risk="moderate",opinions=_op(p="The Protocol volunteers... reluctantly.",a="The boundary math suggests aerial advantage."))]),

    S("spire_guardian", "The Stone Guardian", "A massive construct of living rock blocks the entrance, speaking in all six Tongues simultaneously. 'Prove your resonance or be denied.'", "spire", "midday", "dungeon", ["Izack","Polly","Clay","Aria"],
      [C("sg1","Answer in Kor'aelin","spire_floor1","KO",[L(13,"Governance","Assert governance right of entry"),L(12,"Auth","Authenticate via authority tongue")],stats={"KO":0.1},opinions=_op(p="The Protocol speaks through you.",a="The boundary math suggests authority.")),
       C("sg2","Let Clay commune with it","spire_floor1","DR",[L(14,"Integration","Earth-to-earth integration"),L(9,"Spectral","Spectral stone resonance")],stats={"DR":0.1},opinions=_op(c="Rock friend! I talk to rock friend!",z="I can build a workaround through the golem network.")),
       C("sg3","Solve its riddle logically","spire_floor1","CA",[L(7,"Compute","Riddle-solving compute"),L(11,"Schema","Parse riddle schema")],stats={"CA":0.1},opinions=_op(e="There might be something beyond the obvious answer.",a="The boundary math suggests a systematic approach.")),
       C("sg4","Offer a memory as payment","spire_floor1","RU",[L(4,"Memory","Trade memory for passage"),L(6,"Policy","Apply exchange policy")],stats={"RU":0.1},risk="moderate",opinions=_op(p="The Protocol warns: memories have value.",k="There's always another way to pay.")),
       C("sg5","Shadow-slip past it","spire_floor1","UM",[L(8,"Encrypt","Encrypt passage through shadow"),L(10,"Quantum","Quantum phase through guardian")],stats={"UM":0.1},risk="risky",opinions=_op(k="There's always another way around a wall.",p="The Protocol FORBIDS deception... mostly."))]),

    S("spire_floor1", "Floor of Mirrors", "Every surface reflects not your body but your intentions. Distorted versions of yourself make choices you haven't made yet.", "spire", "unknown", "dungeon", ["Izack","Polly","Clay"],
      [C("f11","Face your reflections honestly","spire_floor2","KO",[L(1,"Intent","Confront true intent"),L(12,"Auth","Self-authenticate")],stats={"KO":0.1},opinions=_op(p="The Protocol demands honesty with self.",c="Mirror-me looks scared too.")),
       C("f12","Analyze the mirror mechanics","spire_floor2","CA",[L(7,"Compute","Mirror-logic computation"),L(11,"Schema","Reflection schema mapping")],stats={"CA":0.1},opinions=_op(z="I can build a workaround for recursive reflection!",e="There might be something beyond the glass.")),
       C("f13","Close your eyes and navigate by feel","spire_floor2","UM",[L(9,"Spectral","Non-visual spectral navigation"),L(8,"Encrypt","Encrypt visual channel")],stats={"UM":0.1},opinions=_op(k="There's always another way to see.",a="The boundary math suggests trusting other senses.")),
       C("f14","Shatter one mirror to test","spire_floor2","DR",[L(5,"Constraints","Test constraint boundaries"),L(13,"Governance","Challenge floor governance")],stats={"DR":0.05},risk="risky",opinions=_op(a="The boundary math suggests... caution.",z="I can build a workaround if it breaks wrong.")),
       C("f15","Ask Polly which reflection is real","spire_floor2","AV",[L(3,"Context","External context verification"),L(2,"Routing","Route through trusted observer")],stats={"AV":0.1},opinions=_op(p="The Protocol sees what you cannot.",c="Polly always knows."))]),

    S("spire_floor2", "Floor of Echoes", "Sounds arrive before their causes. You hear your own future conversations. The air tastes of ozone and old decisions.", "spire", "unknown", "dungeon", ["Izack","Polly","Clay","Eldrin"],
      [C("f21","Listen to your future self","spire_floor3","RU",[L(4,"Memory","Future-memory access"),L(9,"Spectral","Temporal spectral analysis")],stats={"RU":0.1},opinions=_op(p="The Protocol says: the future is data.",e="There might be something beyond linear time!")),
       C("f22","Speak loud to override echoes","spire_floor3","KO",[L(1,"Intent","Override with present intent"),L(13,"Governance","Assert temporal governance")],stats={"KO":0.1},opinions=_op(a="The boundary math suggests amplitude.",c="LOUD! Clay likes loud!")),
       C("f23","Map the echo patterns","spire_floor3","AV",[L(2,"Routing","Map temporal routes"),L(3,"Context","Build temporal context")],stats={"AV":0.1},opinions=_op(e="There might be something beyond the pattern...",z="I can build a workaround for causality.")),
       C("f24","Silence yourself completely","spire_floor3","UM",[L(8,"Encrypt","Encrypt all output"),L(10,"Quantum","Quantum silence state")],stats={"UM":0.1},opinions=_op(k="There's always another way through silence.",p="The Protocol permits strategic quiet.")),
       C("f25","Harmonize with the echoes","spire_floor3","MULTI",[L(14,"Integration","Temporal-sonic integration"),L(6,"Policy","Apply harmonic policy"),L(7,"Compute","Harmonic compute")],stats={"RU":0.05,"AV":0.05},difficulty=0.6,opinions=_op(z="I can build a workaround using resonance!",e="There might be something beyond dissonance."))]),

    S("spire_floor3", "Floor of Weights", "Gravity shifts with every step. Moral choices literally weigh you down or lift you up. Your companions float at different heights.", "spire", "unknown", "dungeon", ["Izack","Polly","Clay","Aria"],
      [C("f31","Accept all weight equally","spire_floor4","RU",[L(6,"Policy","Equitable weight policy"),L(5,"Constraints","Accept all constraints equally")],stats={"RU":0.1},opinions=_op(p="The Protocol bears all burdens.",a="The boundary math suggests equilibrium.")),
       C("f32","Redistribute weight to Clay","spire_floor4","DR",[L(14,"Integration","Team load integration"),L(7,"Compute","Weight distribution compute")],stats={"DR":0.05},risk="moderate",opinions=_op(c="Clay is strong! Give weight!",z="I can build a workaround for gravity.")),
       C("f33","Find the weightless path","spire_floor4","CA",[L(2,"Routing","Gravity-free route finding"),L(10,"Quantum","Quantum gravity manipulation")],stats={"CA":0.1},opinions=_op(e="There might be something beyond gravity itself.",k="There's always another way to be light.")),
       C("f34","Question what the weights represent","spire_floor4","AV",[L(3,"Context","Analyze weight symbolism"),L(11,"Schema","Decode weight schema")],stats={"AV":0.1},opinions=_op(p="The Protocol demands understanding before action.",e="There might be something beyond the metaphor.")),
       C("f35","Encrypt your moral signature","spire_floor4","UM",[L(8,"Encrypt","Encrypt moral weight data"),L(12,"Auth","Authenticate under pressure")],stats={"UM":0.1},opinions=_op(k="There's always another way to carry darkness.",a="The boundary math suggests shielding values."))]),

    S("spire_floor4", "Floor of Tongues", "All six Sacred Tongues manifest as living entities — each one demands you speak it perfectly or face silence forever. This is the final test.", "spire", "unknown", "dungeon", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("f41","Speak each Tongue in sequence","spire_summit","MULTI",[L(14,"Integration","Sequential tongue integration"),L(4,"Memory","Recall all tongue training"),L(7,"Compute","Real-time tongue switching")],stats={"KO":0.05,"AV":0.05,"RU":0.05,"CA":0.05,"UM":0.05,"DR":0.05},difficulty=0.9,opinions=_op(p="The Protocol demands mastery.",a="The boundary math suggests systematic coverage.")),
       C("f42","Improvise a new combined tongue","spire_summit","CA",[L(7,"Compute","Creative linguistic compute"),L(11,"Schema","Novel tongue schema")],stats={"CA":0.15},risk="risky",opinions=_op(z="I can build a workaround that becomes a language!",e="There might be something beyond the six.")),
       C("f43","Let your companions speak for you","spire_summit","KO",[L(13,"Governance","Delegate tongue authority"),L(12,"Auth","Authenticate through trusted voices")],stats={"KO":0.1},opinions=_op(p="The Protocol accepts delegation.",c="Clay speaks earth. Earth is enough.")),
       C("f44","Sing instead of speak","spire_summit","RU",[L(9,"Spectral","Musical spectral encoding"),L(4,"Memory","Channel ancestral songs")],stats={"RU":0.1},opinions=_op(k="There's always another way to say what words cannot.",e="There might be something beyond speech.")),
       C("f45","Embrace the silence","spire_summit","UM",[L(8,"Encrypt","Accept encrypted existence"),L(10,"Quantum","Quantum state of speech-and-silence")],stats={"UM":0.1},opinions=_op(k="There's always another way in the quiet.",p="The Protocol permits paradox... sometimes."))]),

    S("spire_summit", "The Summit Vision", "At the top, reality thins. You see the World Tree — Pollyoneth — at the center of Aethermoor. Its roots are rotting. Dark threads connect it to whatever breached the Academy.", "spire", "timeless", "observatory", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("ss1","Descend immediately toward the Tree","tree_base","CA",[L(2,"Routing","Fastest route to crisis"),L(7,"Compute","Rapid descent compute")],stats={"CA":0.1},opinions=_op(e="There might be something beyond urgency.",a="The boundary math suggests speed.")),
       C("ss2","Study the dark threads from above","tree_base","AV",[L(3,"Context","Aerial threat context"),L(9,"Spectral","Spectral thread analysis")],stats={"AV":0.1},opinions=_op(p="The Protocol demands understanding the enemy.",z="I can build a workaround once I see the pattern.")),
       C("ss3","Strengthen your bonds before descending","tree_base","KO",[L(12,"Auth","Reaffirm team authentication"),L(14,"Integration","Integrate team resolve")],stats={"KO":0.1},opinions=_op(c="Together is safe.",k="There's always another way... but not alone.")),
       C("ss4","Channel the Spire's power into yourself","tree_base","UM",[L(10,"Quantum","Absorb quantum Spire energy"),L(8,"Encrypt","Encrypt power within")],stats={"UM":0.1},risk="risky",opinions=_op(k="There's always another way to gain power.",p="The Protocol warns against greed.")),
       C("ss5","Record everything for those who follow","tree_base","DR",[L(11,"Schema","Encode knowledge schema"),L(6,"Policy","Apply legacy policy")],stats={"DR":0.1},opinions=_op(p="The Protocol demands records.",z="Data survives when towers don't."))]),
]

# ── Arc 5: World Tree (7 scenes) ────────────────────────────────────────────

_tree = [
    S("tree_base", "The Roots of Pollyoneth", "The World Tree rises miles into the violet sky. Its trunk is wider than a city. At its base, bark peels away revealing corruption — black veins spreading upward.", "world_tree", "twilight", "tree", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("tb1","Heal the roots with tongue-song","tree_roots","RU",[L(9,"Spectral","Healing spectral frequency"),L(4,"Memory","Channel tree's own memory")],stats={"RU":0.1},opinions=_op(p="The Protocol demands we try.",c="Tree is hurting. Fix tree.")),
       C("tb2","Analyze the corruption source","tree_roots","AV",[L(3,"Context","Corruption context mapping"),L(11,"Schema","Infection schema analysis")],stats={"AV":0.1},opinions=_op(e="There might be something beyond the symptoms.",z="I can build a workaround once I find the root cause.")),
       C("tb3","Burn away the corruption","tree_roots","DR",[L(7,"Compute","Controlled burn compute"),L(5,"Constraints","Constraint: don't harm the host")],stats={"DR":0.05},risk="risky",opinions=_op(a="The boundary math suggests precision.",z="I can build a workaround for collateral damage.")),
       C("tb4","Enter the roots directly","tree_roots","CA",[L(2,"Routing","Internal route mapping"),L(1,"Intent","Exploratory intent")],stats={"CA":0.1},opinions=_op(e="There might be something beyond the bark!",k="There's always another way inside.")),
       C("tb5","Set up a perimeter defense","tree_roots","KO",[L(13,"Governance","Establish area governance"),L(6,"Policy","Defense perimeter policy")],stats={"KO":0.1},opinions=_op(a="The boundary math suggests we protect what we heal.",c="Safe tree. I guard."))]),

    S("tree_roots", "Inside the Root Network", "Inside the roots, sap flows like glowing rivers. The corruption appears as dark crystals growing where healthy tissue should be. The tree's heartbeat is audible.", "world_tree", "unknown", "dungeon", ["Izack","Polly","Clay"],
      [C("tr1","Follow the sap upstream","tree_canopy","AV",[L(2,"Routing","Follow internal routes"),L(3,"Context","Read sap flow context")],stats={"AV":0.1},opinions=_op(p="The Protocol follows the current.",e="There might be something beyond the flow.")),
       C("tr2","Purify crystals one by one","tree_canopy","RU",[L(9,"Spectral","Crystal purification frequency"),L(4,"Memory","Restore crystal memory to health")],stats={"RU":0.1},opinions=_op(p="The Protocol demands patience.",c="One at a time. Good.")),
       C("tr3","Build sap-flow bypass channels","tree_canopy","CA",[L(7,"Compute","Engineering compute"),L(11,"Schema","Bypass schema design")],stats={"CA":0.1},opinions=_op(z="I can build a workaround for the blockages!",e="There might be something beyond the obvious.")),
       C("tr4","Encrypt healthy sap against reinfection","tree_canopy","UM",[L(8,"Encrypt","Biological encryption"),L(10,"Quantum","Quantum immune system")],stats={"UM":0.1},opinions=_op(k="There's always another way to protect what's pure.",a="The boundary math suggests lasting immunity.")),
       C("tr5","Let Clay merge with the root structure","tree_canopy","DR",[L(14,"Integration","Earth-golem-tree integration"),L(12,"Auth","Authenticate Clay's earth nature")],stats={"DR":0.1},risk="moderate",opinions=_op(c="Clay... becomes tree? Clay likes tree.",p="The Protocol warns: integration is irreversible."))]),

    S("tree_canopy", "The Living Canopy", "Among branches thick as highways, you find a hidden civilization — tree-dwellers who've lived here for millennia. They speak in a tongue that blends all six.", "world_tree", "eternal_day", "tree", ["Izack","Polly","Clay","Eldrin","Aria"],
      [C("tca1","Learn their blended tongue","tree_heart","MULTI",[L(14,"Integration","Full tongue integration study"),L(4,"Memory","Encode new linguistic memory"),L(9,"Spectral","Analyze blended spectral signature")],stats={"KO":0.03,"AV":0.03,"RU":0.03,"CA":0.03,"UM":0.03,"DR":0.03},difficulty=0.8,opinions=_op(p="The Protocol has never encountered this.",e="There might be something beyond the six we know.")),
       C("tca2","Ask about the corruption","tree_heart","AV",[L(3,"Context","Gather historical context"),L(6,"Policy","Understand their policy on the blight")],stats={"AV":0.1},opinions=_op(e="There might be something beyond our understanding.",p="The Protocol demands we listen first.")),
       C("tca3","Offer to help defend them","tree_heart","KO",[L(1,"Intent","Protective intent"),L(13,"Governance","Establish mutual governance")],stats={"KO":0.1},opinions=_op(a="The boundary math suggests alliance.",c="New friends! Protect new friends!")),
       C("tca4","Trade knowledge for passage","tree_heart","DR",[L(11,"Schema","Knowledge exchange schema"),L(12,"Auth","Mutual authentication of knowledge")],stats={"DR":0.1},opinions=_op(z="I can build a workaround with shared blueprints.",k="There's always another way to earn trust.")),
       C("tca5","Search for the Tree's heart alone","tree_heart","UM",[L(8,"Encrypt","Stealth encryption"),L(2,"Routing","Solo route to heart")],stats={"UM":0.05},risk="moderate",opinions=_op(k="There's always another way nobody expects.",p="The Protocol advises against lone operations."))]),

    S("tree_heart", "The Heart of Pollyoneth", "At the Tree's core: a chamber of pure light where all six Tongues exist as one living sound. Here the corruption is thickest — a dark figure stands at the center, feeding on the Tree's power.", "world_tree", "timeless", "tree", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("th1","Confront the dark figure","tree_confrontation","KO",[L(1,"Intent","Confront with authority"),L(13,"Governance","Assert highest governance")],stats={"KO":0.1},opinions=_op(p="The Protocol demands courage.",a="The boundary math suggests a direct approach.")),
       C("th2","Analyze the corruption mechanism","tree_confrontation","AV",[L(3,"Context","Deep threat context"),L(11,"Schema","Corruption schema analysis")],stats={"AV":0.1},opinions=_op(e="There might be something beyond what we see.",z="I can build a workaround once I understand the mechanism.")),
       C("th3","Channel the Tree's own defenses","tree_confrontation","RU",[L(4,"Memory","Activate tree's immune memory"),L(9,"Spectral","Amplify tree spectral defense")],stats={"RU":0.1},opinions=_op(p="The Protocol says: use the host's strength.",c="Tree is strong. Help tree fight.")),
       C("th4","Build a containment ward","tree_confrontation","UM",[L(8,"Encrypt","Maximum encryption ward"),L(10,"Quantum","Quantum containment field")],stats={"UM":0.1},opinions=_op(k="There's always another way to cage darkness.",a="The boundary math suggests containment before combat.")),
       C("th5","Ask Kael to use his shadow-tongue","tree_confrontation","DR",[L(12,"Auth","Authenticate Kael's loyalty"),L(5,"Constraints","Accept the risk constraints")],stats={"DR":0.1,"UM":0.05},risk="risky",opinions=_op(k="There's always another way. Let me show you.",p="The Protocol... permits this. Barely."))]),

    S("tree_confrontation", "Face to Face", "The dark figure turns. It wears your face — a version of you that chose power over connection, efficiency over compassion. 'I am what you could become,' it says.", "world_tree", "timeless", "tree", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("tc1a","I choose connection","tree_battle","KO",[L(1,"Intent","Declare core intent"),L(14,"Integration","Integrate values over power")],stats={"KO":0.15},opinions=_op(p="The Protocol IS connection.",c="Together always.")),
       C("tc2a","I choose understanding","tree_battle","AV",[L(3,"Context","Understand even the enemy"),L(6,"Policy","Apply compassion policy")],stats={"AV":0.15},opinions=_op(e="There might be something beyond opposition.",p="The Protocol demands we understand our shadow.")),
       C("tc3a","I choose memory","tree_battle","RU",[L(4,"Memory","Draw strength from all memories"),L(9,"Spectral","Ancestral spectral surge")],stats={"RU":0.15},opinions=_op(p="The Protocol carries everyone who came before.",k="There's always another way to honor the past.")),
       C("tc4a","I choose creation","tree_battle","CA",[L(7,"Compute","Channel all compute into creation"),L(11,"Schema","Generate counter-schema")],stats={"CA":0.15},opinions=_op(z="I can build a workaround for evil itself!",e="There might be something beyond destruction.")),
       C("tc5a","I choose both light and shadow","tree_battle","MULTI",[L(10,"Quantum","Accept quantum duality"),L(8,"Encrypt","Encrypt shadow within light"),L(13,"Governance","Unified governance of self")],stats={"KO":0.05,"UM":0.1},difficulty=0.9,risk="dangerous",opinions=_op(k="There's always another way. This IS the way.",p="The Protocol... was built for this moment."))]),

    S("tree_battle", "The Battle for Pollyoneth", "Six tongues of light erupt from your companions. The dark version attacks with corrupted versions of every spell you've learned. The World Tree trembles.", "world_tree", "timeless", "arena", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("bt1","Lead the six-tongue harmony","tree_resolution","MULTI",[L(14,"Integration","Full team tongue integration"),L(13,"Governance","Harmonic governance"),L(1,"Intent","Unified intent")],stats={"KO":0.05,"AV":0.05,"RU":0.05,"CA":0.05,"UM":0.05,"DR":0.05},difficulty=1.0,opinions=_op(p="The Protocol sings through all of us.",a="The boundary math says: together.")),
       C("bt2","Shield while others attack","tree_resolution","DR",[L(5,"Constraints","Defensive constraint mastery"),L(8,"Encrypt","Shield encryption")],stats={"DR":0.15},opinions=_op(a="The boundary math suggests sacrifice.",c="Shield friends. Clay shields.")),
       C("bt3","Find the weak point and strike","tree_resolution","CA",[L(7,"Compute","Tactical vulnerability compute"),L(9,"Spectral","Spectral weak-point detection")],stats={"CA":0.15},opinions=_op(z="I can build a workaround for invincibility!",e="There might be something beyond brute force.")),
       C("bt4","Absorb the corruption into yourself","tree_resolution","UM",[L(10,"Quantum","Quantum corruption absorption"),L(8,"Encrypt","Encrypt corruption within")],stats={"UM":0.15},risk="dangerous",opinions=_op(k="There's always another way to end this.",p="The Protocol FORBIDS self-sacrifice!")),
       C("bt5","Forgive your shadow self","tree_resolution","KO",[L(1,"Intent","Compassionate intent"),L(12,"Auth","Authenticate shared identity")],stats={"KO":0.15},opinions=_op(p="The Protocol says: love is the highest governance.",c="Shadow-you is still you."))]),

    S("tree_resolution", "The Tree Restored", "Light floods the chamber. The corruption dissolves. The World Tree's heartbeat strengthens. Your shadow-self fades with a strange smile — not defeated, but integrated.", "world_tree", "dawn", "tree", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("tr1a","Return to the Academy as teachers","ending_scholar","DR",[L(6,"Policy","Establish teaching policy"),L(14,"Integration","Integrate all learned knowledge")],stats={"DR":0.1},opinions=_op(p="The Protocol must be passed on.",e="There might be something beyond what we can teach.")),
       C("tr2a","Stay at the World Tree as guardians","ending_guardian","KO",[L(13,"Governance","Permanent governance commitment"),L(12,"Auth","Guardian authentication")],stats={"KO":0.1},opinions=_op(c="Stay with tree forever. Clay likes.",a="The boundary math suggests permanence.")),
       C("tr3a","Open a path back to Earth","ending_bridge","AV",[L(2,"Routing","Inter-dimensional routing"),L(14,"Integration","Bridge two worlds")],stats={"AV":0.1},opinions=_op(e="There might be something beyond either world alone.",z="I can build a workaround between dimensions!")),
       C("tr4a","Explore deeper into the unknown","ending_guardian","CA",[L(1,"Intent","Exploratory intent renewed"),L(10,"Quantum","Quantum frontier seeking")],stats={"CA":0.1},opinions=_op(e="There might be something beyond everything!",k="There's always another way.")),
       C("tr5a","Merge with the Tree's consciousness","ending_scholar","RU",[L(4,"Memory","Merge into world memory"),L(9,"Spectral","Spectral self-dissolution")],stats={"RU":0.1},risk="dangerous",opinions=_op(p="The Protocol says: some sacrifices are permanent.",k="There's always another way to live on."))]),
]

# ── Endings (3 scenes) ──────────────────────────────────────────────────────

_endings = [
    S("ending_scholar", "The Scholar's Legacy", "Years pass. The Academy thrives. Your students carry the Six Tongues to every floating island. The Protocol endures — not as rigid law but as living wisdom, growing with each new voice that speaks it.", "academy", "eternal", "academy", ["Izack","Polly","Clay","Eldrin","Aria","Zara","Kael"],
      [C("es1","Write the definitive tongue codex","ending_scholar","DR",[L(11,"Schema","Canonical schema creation"),L(4,"Memory","Encode for posterity")],stats={"DR":0.1},opinions=_op(p="The Protocol will endure.",e="There might be something beyond the written word.")),
       C("es2","Train the next generation personally","ending_scholar","KO",[L(13,"Governance","Mentorship governance"),L(1,"Intent","Pedagogical intent")],stats={"KO":0.1},opinions=_op(a="The boundary math suggests continuity.",c="Little ones! Teach little ones!")),
       C("es3","Research new tongues","ending_scholar","CA",[L(7,"Compute","Discovery compute"),L(10,"Quantum","Quantum linguistic research")],stats={"CA":0.1},opinions=_op(z="I can build a workaround for the unknown!",e="There might be something beyond six.")),
       C("es4","Establish inter-world diplomacy","ending_scholar","AV",[L(2,"Routing","Diplomatic routing"),L(14,"Integration","Cross-world integration")],stats={"AV":0.1},opinions=_op(p="The Protocol transcends borders.",k="There's always another way to make peace.")),
       C("es5","Guard the restricted archive","ending_scholar","UM",[L(8,"Encrypt","Archive encryption"),L(6,"Policy","Secrecy policy")],stats={"UM":0.1},opinions=_op(k="There's always another way to protect knowledge.",p="The Protocol demands vigilance."))],
      exit=True, mood="triumphant"),

    S("ending_guardian", "The Guardian's Watch", "You stand where the World Tree meets the sky, watching over Aethermoor through seasons of change. The six Tongues sing through you like wind through leaves. You are home.", "world_tree", "eternal", "tree", ["Izack","Polly","Clay","Kael"],
      [C("eg1","Strengthen the tree's defenses","ending_guardian","UM",[L(8,"Encrypt","Living ward encryption"),L(13,"Governance","Eternal governance")],stats={"UM":0.1},opinions=_op(k="There's always another way to keep watch.",c="Guard tree. Always guard tree.")),
       C("eg2","Welcome new arrivals from Earth","ending_guardian","KO",[L(12,"Auth","Newcomer authentication"),L(1,"Intent","Welcoming intent")],stats={"KO":0.1},opinions=_op(p="The Protocol welcomes all who resonate.",e="There might be something beyond what we expected.")),
       C("eg3","Tend the root network","ending_guardian","RU",[L(4,"Memory","Root memory maintenance"),L(9,"Spectral","Spectral health monitoring")],stats={"RU":0.1},opinions=_op(c="Roots are deep. Deep is safe.",p="The Protocol demands maintenance.")),
       C("eg4","Map new floating islands","ending_guardian","AV",[L(2,"Routing","Cartographic routing"),L(3,"Context","Environmental context mapping")],stats={"AV":0.1},opinions=_op(e="There might be something beyond the known islands!",z="I can build a workaround for distance.")),
       C("eg5","Build defenses with Zara's blueprints","ending_guardian","CA",[L(7,"Compute","Construction compute"),L(11,"Schema","Defense schema implementation")],stats={"CA":0.1},opinions=_op(z="I can build a workaround for any threat!",a="The boundary math suggests fortification."))],
      exit=True, mood="serene"),

    S("ending_bridge", "The Bridge Between Worlds", "A shimmering arch spans the void between Earth and Aethermoor. You stand at its center, translator and guardian, ensuring that what flows between worlds is governed by the Protocol.", "void", "eternal", "observatory", ["Izack","Polly","Clay","Eldrin","Zara"],
      [C("eb1","Monitor bridge traffic","ending_bridge","AV",[L(2,"Routing","Inter-dimensional routing"),L(3,"Context","Cross-world context analysis")],stats={"AV":0.1},opinions=_op(p="The Protocol governs all passages.",e="There might be something beyond traffic patterns.")),
       C("eb2","Establish trade protocols","ending_bridge","DR",[L(6,"Policy","Trade policy framework"),L(5,"Constraints","Fair exchange constraints")],stats={"DR":0.1},opinions=_op(z="I can build a workaround for any tariff!",a="The boundary math suggests balance.")),
       C("eb3","Teach Earth about the Tongues","ending_bridge","KO",[L(1,"Intent","Educational intent"),L(13,"Governance","Cross-world governance")],stats={"KO":0.1},opinions=_op(p="The Protocol must reach all worlds.",c="Earth people need Tongues too.")),
       C("eb4","Research bridge stability","ending_bridge","CA",[L(7,"Compute","Structural analysis compute"),L(10,"Quantum","Quantum bridge mechanics")],stats={"CA":0.1},opinions=_op(z="I can build a workaround for dimensional instability!",e="There might be something beyond physics.")),
       C("eb5","Encrypt the bridge against misuse","ending_bridge","UM",[L(8,"Encrypt","Bridge encryption"),L(12,"Auth","Access authentication")],stats={"UM":0.1},opinions=_op(k="There's always another way to keep the gate.",p="The Protocol demands security."))],
      exit=True, mood="hopeful"),
]

# ── Library Functions ────────────────────────────────────────────────────────

_ALL_SCENES: Dict[str, EScene] = {}
for _arc in (_earth, _transit, _academy, _spire, _tree, _endings):
    for _s in _arc:
        _ALL_SCENES[_s.sid] = _s

_SCENE_ORDER = [s.sid for arc in (_earth, _transit, _academy, _spire, _tree, _endings) for s in arc]

def get_all_scenes() -> Dict[str, EScene]:
    return dict(_ALL_SCENES)

def get_scene_order() -> List[str]:
    return list(_SCENE_ORDER)

def get_layers_by_scene(sid: str) -> Set[int]:
    scene = _ALL_SCENES.get(sid)
    if not scene:
        return set()
    layers: Set[int] = set()
    for ch in scene.choices:
        for lt in ch.layers:
            layers.add(lt.layer)
    return layers

def validate_coverage() -> Dict[int, int]:
    counts: Dict[int, int] = {i: 0 for i in range(1, 15)}
    for scene in _ALL_SCENES.values():
        for ch in scene.choices:
            for lt in ch.layers:
                counts[lt.layer] = counts.get(lt.layer, 0) + 1
    return counts

# ── Selftest ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scenes = get_all_scenes()
    order = get_scene_order()
    all_sids = set(scenes.keys())
    errors = []

    # 1. Count total scenes
    n = len(scenes)
    print(f"Total scenes: {n}", "PASS" if n == 33 else "FAIL")
    if n != 33:
        errors.append(f"Expected 33 scenes, got {n}")
        print("  Scene IDs:", sorted(all_sids))

    # 2. Verify 5-7 choices (transit_fall exempt)
    for sid, sc in scenes.items():
        nc = len(sc.choices)
        if sid == "transit_fall":
            if nc != 0:
                errors.append(f"{sid}: expected 0 choices (narrative), got {nc}")
            continue
        if nc < 5 or nc > 7:
            errors.append(f"{sid}: {nc} choices (need 5-7)")
    print(f"Choice counts: {'PASS' if not any('choices' in e for e in errors) else 'FAIL'}")

    # 3. Layer coverage >= 5
    cov = validate_coverage()
    layer_names = {1:"Intent",2:"Routing",3:"Context",4:"Memory",5:"Constraints",
                   6:"Policy",7:"Compute",8:"Encrypt",9:"Spectral",10:"Quantum",
                   11:"Schema",12:"Auth",13:"Governance",14:"Integration"}
    print("\nLayer Coverage Map:")
    for i in range(1, 15):
        c = cov.get(i, 0)
        bar = "#" * min(c, 40)
        status = "OK" if c >= 5 else "LOW"
        print(f"  L{i:2d} {layer_names[i]:12s}: {c:3d} {bar} {status}")
        if c < 5:
            errors.append(f"Layer {i} ({layer_names[i]}): only {c} occurrences (need >=5)")

    # 4. No dangling next_scene references
    for sid, sc in scenes.items():
        for ch in sc.choices:
            if ch.next_scene not in all_sids:
                errors.append(f"{sid}/{ch.cid}: next_scene '{ch.next_scene}' not found")
    print(f"\nDangling references: {'PASS' if not any('next_scene' in e for e in errors) else 'FAIL'}")

    # 5. All choices have >= 2 companion opinions
    for sid, sc in scenes.items():
        for ch in sc.choices:
            if len(ch.opinions) < 2:
                errors.append(f"{sid}/{ch.cid}: only {len(ch.opinions)} opinions (need >=2)")
    print(f"Companion opinions: {'PASS' if not any('opinions' in e for e in errors) else 'FAIL'}")

    # 6. Total choice count
    total_choices = sum(len(sc.choices) for sc in scenes.values())
    print(f"\nTotal choices: {total_choices}")

    # Summary
    if errors:
        print(f"\n--- {len(errors)} ERRORS ---")
        for e in errors:
            print(f"  ! {e}")
    else:
        print("\n--- ALL CHECKS PASSED ---")
