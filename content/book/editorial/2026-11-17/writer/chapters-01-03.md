# Writer proposal receipt: Chapters 1-3

- **Work:** *The Six Tongues Protocol*
- **Role:** `WRITER`
- **Scope:** Chapter 1, Interlude 1, Chapter 2, Chapter 3 only
- **Pass date:** 2026-11-17
- **Status:** proposed revision plan only
- **Manuscript edits:** none
- **Editorial bias:** preserve Issac’s dry engineering voice; prefer cuts, rhythm repairs, and one-sentence clarifications over expansion

## Provenance

The discrete reader-edition chapter files are the exact passage sources available in this worktree. The house-style-declared `content/book/source/` directory is absent, so no claim is made that these are master source files.

| Input | Exact path | SHA-256 |
|---|---|---|
| Chapter 1 | `C:\dev\_wt_six_tongues_editorial_20261117\content\book\reader-edition\ch01.md` | `E94355604666D47353F99C94B813DD2585AF573DCF706BCD52D44ADB8892FE2E` |
| Interlude 1 | `C:\dev\_wt_six_tongues_editorial_20261117\content\book\reader-edition\interlude-01-pollys-vigil.md` | `E840B0F70AB25EB9CC9B62AFAF7D52E70B572286FECC3148660A89981156C3D1` |
| Chapter 2 | `C:\dev\_wt_six_tongues_editorial_20261117\content\book\reader-edition\ch02.md` | `78668C5B109BA925A83B1E3158035E1881D0AD26A94C24A7FA737A86254E55F0` |
| Chapter 3 | `C:\dev\_wt_six_tongues_editorial_20261117\content\book\reader-edition\ch03.md` | `240256F5A7B0F3C54B1E13B7A1371EF76B210EEA6E8784A74C1CB7DD6D2CDA28` |
| Compiled reader manuscript, reference container | `C:\dev\_wt_six_tongues_editorial_20261117\content\book\reader-edition\the-six-tongues-protocol-full.md` | `2DEAC4193F5B4916CBD3B7D77E96FC3BE631AB85D9785B1AC800DB9DE0335728` |
| Fresh-reader receipt | `C:\dev\_wt_six_tongues_editorial_20261117\content\book\editorial\2026-11-17\fresh-reader\chapters-01-03.md` | `F64C55210B1B8CA7BBFCAAA8CD6CEF44041D3D016A7FAD2130F146C9C30C5A48` |

Line references below are local to the discrete file named in each proposal. Snippets are intentionally short and are **not applied text**.

## Editorial diagnosis

The opening already has a complete engine:

1. a valid-but-impossible security signal;
2. a tired man whose honest intent is to understand;
3. a sarcastic keeper whose care appears as maintenance and proximity;
4. six legible domains surrounding a missing seventh place; and
5. a distress signal rising from that absence.

The revision goal is therefore not to add lore or spectacle. It is to reach each turn a little sooner, avoid explaining the same framework twice, and remove small surface errors that make the reader notice the draft rather than the world.

## Proposed edits

### Chapter 1 — “Protocol Handshake”

#### W01 — Cut the second apartment inventory

- **Location:** `ch01.md:L20`
- **Priority:** high
- **Before:** “His apartment was twelve miles south, an efficiency unit ... one expired yogurt and a bottle of Sriracha. He hadn't been home since Thursday.”
- **After:** “His apartment was twelve miles south. His manager had stopped asking why he hadn't gone back.”
- **Keep around it:** the blinking cursor, the sixteen-hour voluntary shift, and the final manager sentence.
- **What it buys:** The window, Bryce, bass guitar, mattress, yogurt, Sriracha, and Thursday absence have already established Marcus’s chosen but neglected life at `L10-L18`. This cut gets to “Something was wrong with the logs” sooner without losing grief, isolation, or the running expired-yogurt joke.
- **Canon impact:** none; it removes duplicate evidence only.

#### W02 — Restore past-tense control in the coffee callback

- **Location:** `ch01.md:L42`
- **Priority:** mechanical
- **Before:** “The taste of late nights and bad decisions, but how could he not? It is the taste of his actual life.”
- **After:** “The taste of late nights and bad decisions. How could he not? It was the taste of his actual life.”
- **What it buys:** Keeps the dry, self-indicting beat while removing the one unmarked present-tense slip in an otherwise past-tense scene.
- **Canon impact:** none.

#### W03 — Give the closing security hook shorter packet-like rhythm

- **Location:** `ch01.md:L212`
- **Priority:** medium
- **Before:** “And because the unauthorized channel he'd been tracing ... had shown him something--a pattern in the traffic, not random, not malicious, but *structured*...”
- **After:** “Back in the world that now felt like a dream, the unauthorized channel had carried a pattern: not random, not malicious, but *structured*. Like language. Like protocol. Like someone on the other side of reality trying to get a message through. He filed it away. Even here. Even now.”
- **What it buys:** Reasserts the book’s central mystery at the exit in Marcus’s diagnostic cadence. The shorter units echo a trace resolving into a signal and keep the final coffee-and-biscuit line as the warmer last note.
- **Canon impact:** preserves the channel, its non-malicious structure, and the implied message source.

### Interlude 1 — “Polly’s Vigil”

#### W04 — Do not imply an unseen question scene

- **Location:** `interlude-01-pollys-vigil.md:L80-L90`
- **Priority:** high, pending chronology decision
- **Before:** “Marcus had been in Aethermoor for less than six hours, and he'd already asked the question...”
- **After:** “Marcus had been in Aethermoor for less than six hours, and his arrival had already exposed the question...”
- **What it buys:** Marcus has not asked the three preceding questions on-page in Chapters 1-3. “Exposed” preserves Polly’s inference—that an outside engineer makes the system’s missing vocabulary visible—without inventing an unseen conversation.
- **Canon impact:** Marcus remains the catalyst; only the asserted mechanism changes.
- **Continuity hold:** If a deliberately omitted six-hour scene contains the question, reject this edit and make that chronology legible instead.

#### Intentionally preserved after review

- **Kael’s ghost-patches (`L46-L48`):** retain. It is compact, technically vivid, and supplies an early named trace even if the reader cannot place him yet.
- **The three questions (`L80-L90`):** retain. They define the missing governance domain more emotionally than another architecture explanation would.
- **The sleep-caw and six-inch distance (`L102-L120`):** retain verbatim unless the author requests a voice pass. This is the interlude’s payoff and the emotional checksum for the block.

### Chapter 2 — “The Language Barrier”

#### W05 — Clarify why a nine-dimensional vector names only four dimensions

- **Location:** `ch02.md:L108-L112`
- **Priority:** medium
- **Before:** “His state vector--nine dimensions of data ... His context window ... temporal phase ... entropy level ... quantum coherence ... Nine numbers...”
- **After:** “His state vector--nine semantic dimensions the Protocol tracked continuously. He caught only four: context window, temporal phase, entropy, coherence. All nine updated in real time, defining not just whether he existed but *how well* he existed.”
- **What it buys:** Preserves the canonically significant number nine while telling the reader that the partial list is Marcus’s limited glimpse, not an accidentally incomplete enumeration.
- **Canon impact:** The exact technical definitions can remain in the surrounding prose or annotated edition. A continuity keeper should confirm their official names before any cut is accepted.

#### W06 — Compress only the repeated definitions in Polly’s second six-tongue pass

- **Location:** `ch02.md:L146-L175`
- **Priority:** high
- **Before, representative:** “KO. Kor'aelin. The Control Tongue. High-level declarations. *I want this to happen* ... Not how. Not why. Just *what*.”
- **After:** “KO. Kor'aelin. Control: the outcome you request, not the implementation.”
- **Before, representative:** “AV. Avali. The Transport Tongue. This is the *how to get there*. Initialization, routing, channel establishment...”
- **After:** “AV. Avali. Transport: initialization, routing, the secure path between intent and arrival.”
- **What to preserve in the same scene:** Marcus’s translation jokes; the RU-gated invisible door; CA as the engineer’s tongue; UM’s escalating concealment risk; Polly’s reaction to the Architect; DR’s tamper-evident proof; and the final network-stack recognition.
- **What it buys:** The first pass at `L74-L87` already lets the reader feel and learn all six. The second pass should now demonstrate Marcus and Polly building a shared vocabulary, not re-teach every definition. A roughly twenty-percent cut keeps the banter and all new operational facts while reaching “This is a network stack” sooner.
- **Canon impact:** no domain, name, color, function, or dependency may be dropped. This is compression, not remapping.

#### W07 — Make the Chapter 2-to-3 handoff agree with the imminent lesson

- **Location:** `ch02.md:L190-L198`
- **Priority:** high
- **Before:** “One at a time. Starting tomorrow. Tonight, you rest.” ... “And I owe you a drink.”
- **After:** “One at a time. But first, I owe you a drink.”
- **What it buys:** Chapter 3 opens in the refectory and announces formal training in seven minutes. Removing the promise that training starts tomorrow makes the cut continuous and allows the sleeping ward later in Chapter 3 to provide the promised rest after the lesson.
- **Canon impact:** preserves one-at-a-time instruction, essence brew, and later sleep; changes only timing language.
- **Continuity hold:** The interlude’s placement still requires a separate chronology decision; see Risks C01-C02.

#### W08 — Remove desire for an object Marcus did not perceive

- **Location:** `ch02.md:L228-L230`
- **Priority:** low
- **Before:** “Marcus didn't look back at the seventh pedestal, though part of him wanted to.”
- **After:** “Marcus didn't look back.”
- **What it buys:** The reader can see the pedestal through the narrative reveal, but Marcus has missed it. The shorter line preserves strict anchoring and lands like a closed door.
- **Canon impact:** the seventh pedestal, its age, position, darkness, and unparseable script remain unchanged.

### Chapter 3 — “Hyperbolic Consequences”

#### W09 — Trim the second consecutive landscape reveal

- **Location:** `ch03.md:L56-L70`
- **Priority:** medium
- **Before:** “Somewhere in the middle distance, a creature the size of a delivery van drifted ... A herd of something woolly grazed on a boulder...”
- **After:** “A stained-glass-winged creature drifted between two floating meadows.”
- **What to preserve:** the layered dawn, climbing leyline rivers, conversing gardens, mildly annoyed tree, and “That’s not architecture. That’s parenthood.”
- **What it buys:** Chapter 2 has just supplied the large world panorama. This cut keeps the new morning color and the crucial parenthood insight while reaching the hyperbolic training room before wonder becomes repetition.
- **Canon impact:** removes incidental scenic inventory only.

#### W10 — Repair the missing training-room furniture

- **Location:** `ch03.md:L188-L194`
- **Priority:** mechanical
- **Before:** “she was on the table edge nearest him now”
- **After:** “she was at the plinth’s edge nearest him now”
- **What it buys:** The room established an obsidian plinth and an accidental chair, but no table. The change keeps Polly close without making the set flicker around her.
- **Canon impact:** none. Her six-inch proximity and feather distress remain.

#### W11 — Put the sensory rule before the technical label

- **Location:** `ch03.md:L220-L232`
- **Priority:** medium
- **Before:** “Tiny intent drift ... multiplied through harmonic cost. ... In bounded systems, drift is annoying. In hyperbolic systems, drift compounds.”
- **After:** “Tiny intent drift,” Polly said. “The room turns distance into cost. Harmonic cost. In bounded systems, drift is annoying. In hyperbolic systems, each correction compounds the next.”
- **What it buys:** The room has already flexed and distance has become felt before “harmonic cost” is named. The additional plain clause makes the title concept graspable without turning the scene into a formula lecture.
- **Canon impact:** preserves harmonic cost, hyperbolic compounding, and Polly’s warning that vagueness is expensive.

#### W12 — Repair nested dialogue quotation marks

- **Location:** `ch03.md:L248-L250`, `L276`
- **Priority:** mechanical
- **Before:** `"If you say "sleep hygiene" I'm leaving."`
- **After:** `"If you say 'sleep hygiene,' I'm leaving."`
- **Before:** `"I was going to say "sleep or cease.""`
- **After:** `"I was going to say 'sleep or cease.'"`
- **Before:** `"Nothing says "sweet dreams" like "anti-ontological disconnect hardware.""`
- **After:** `"Nothing says 'sweet dreams' like 'anti-ontological disconnect hardware.'"`
- **What it buys:** Restores readable dialogue without touching the jokes.
- **Canon impact:** none.

#### W13 — Bound “stay” so the later choice can remain a choice

- **Location:** `ch03.md:L296-L306`
- **Priority:** author decision
- **Before:** “I intend to understand,” he said. “And stay.”
- **After:** “I intend to understand,” he said. “And stay until I do.”
- **What it buys:** Marcus can honestly commit to the immediate danger and relationship without appearing to decide his permanent home before the later slow-earned choice described by the house style. Polly can still hear hope in it.
- **Canon impact:** potentially significant. If the unbounded “stay” is intended as unconscious foreshadowing that the Protocol recognizes before Marcus does, preserve the original. Only Issac should choose between those readings.

## What must remain canon in any accepted patch

1. **Marcus’s Earth anchor:** Bryce, Thursday, the warm window breeze, the small chosen apartment, dead coffee, and work as avoidance. Cuts may remove repetition, not the emotional cause.
2. **The initiating mystery:** tokens are valid, unauthorized, structured, non-malicious, and almost beautiful; the channel appears to carry a message from the other side.
3. **Intent before wording:** the Protocol asks what Marcus intends, listens beneath language, and recognizes his honest desire to understand.
4. **Polly’s embodiment and voice:** academic-regalia raven is her comfortable true form; humanoid form is a practical unfolding; obsidian eyes persist; sarcasm covers warmth; feathers carry body-language truth.
5. **Existence stakes:** the 0.3-second verification heartbeat, temporary guest pass, seventy-two-hour baseline deadline, flicker/cease distinction, and layer-specific outcomes.
6. **Six-tongue counterpoint:** KO, AV, RU, CA, UM, and DR retain their names, colors, sensory signatures, functions, separations, and ability to relate without becoming uniform.
7. **The missing domain:** the old, dark seventh pedestal; Kael’s ghost-patches; the Seventh Holding; the architecture’s missing vocabulary for endings; and the many-voiced distress signal remain mystery, not prematurely explained villainy.
8. **Domestic proof of care:** mug, essence brew, chalk, tea, blanket, sleep-caw, and chosen proximity remain as load-bearing emotional infrastructure.
9. **Training consequences:** the accidental chair, successful KO plus failed RU, reduced-resolution destabilization, hyperbolic compounding, and the principle that vague logs can kill.
10. **Home-building trajectory:** Marcus’s eventual decision to stay must remain earned; Izack is load-bearing rather than reduced to tragedy; Polly’s hope appears through precision and proximity.

## One cinematic website candy concept

### The Warm Handshake

The page opens in midnight-blue near-darkness with a single cursor and one plain question: **What do you intend?** The visitor chooses or writes a short intent. Six restrained facets then answer in counterpoint:

- outcome;
- route;
- permission;
- work;
- protection;
- proof.

If the intent and stated constraint disagree, an ordinary amber-lit chair appears—not as a failure screen, but as a gentle prompt: *Your need may be asking for something different from your words.* The visitor receives a free, copyable six-line “intent receipt” they can use to plan a project or evaluate a system. A warm mug glow and slow verification pulse close the interaction.

The paid next step appears only afterward: continue into the novel, inspect a technical project, or request deeper implementation help. The candy is the useful receipt itself, not an advertisement disguised as a tool.

Accessibility and canon boundaries:

- readable and useful with animation disabled;
- no knowledge of Marcus, Polly, or the tongue names required;
- no generated likeness of Issac or any real person;
- no claim that the interaction performs security validation, certification, or psychological assessment;
- colors and motion may evoke the chapters, but the website wording remains ordinary-language first.

## Continuity risks for the independent keeper

### C01 — Interlude chronology

`interlude-01-pollys-vigil.md:L6-L16` says Marcus falls asleep on the archive floor and begins Protocol integration. Chapter 1 ends with him following Polly away; Chapter 2 resumes their corridor orientation; Chapter 3 later presents the sleeping ward and Protocol dreams as a new event. Determine whether the interlude is:

1. non-linear and needs an explicit placement signal;
2. chronologically between two unseen movements and needs a bridge; or
3. intended to sit later in the sequence.

Do not solve this by silently relocating or rewriting the interlude. Author approval is required.

### C02 — “Tomorrow,” morning, and seven minutes

Chapter 2 promises training “starting tomorrow” and rest “tonight” (`ch02.md:L190-L196`), while Chapter 3 opens with the promised first drink, morning arrives, and training begins in seven minutes (`ch03.md:L4-L58`). W07 is the smallest local fix, but the keeper must reconcile it with C01 before acceptance.

### C03 — Unseen question

The interlude states Marcus has already asked what happens to what the system drops (`interlude-01-pollys-vigil.md:L80-L90`), but that question is not shown in these files. W04 changes “asked” to “exposed”; reject W04 if a canonical omitted scene is meant to supply the conversation.

### C04 — POV contract

The house style specifies third-person limited anchored to Marcus, but Interlude 1 is limited to Polly and Chapter 2 briefly reveals a seventh pedestal Marcus misses. These may be deliberate interlude/narrative exceptions. The keeper should document the exception rather than normalize it accidentally.

### C05 — Exact technical registry

Before accepting W05, verify the canonical names and count of the nine semantic dimensions. Before accepting W06 or W11, verify that no compressed phrase changes the formal roles of the tongues, harmonic cost, or hyperbolic compounding.

### C06 — Form and furniture

Polly begins Chapter 3 as a raven, shifts humanoid for instruction (`ch03.md:L78`), and is later described at a table edge with feather distress (`L192`). W10 fixes the absent table, but the keeper should confirm whether she remains humanoid throughout the lesson or changes form off-page.

### C07 — The scope of “stay”

W13 protects the later voluntary-home arc, but the original may deliberately let the Protocol reveal Marcus’s desire before he consciously accepts it. This is an authorial foreshadowing decision, not a copy edit.

## Author-approval boundary

- This file is a proposal receipt, not a manuscript patch.
- No reader-edition, compiled manuscript, house-style, canon, or website file was modified.
- “After” snippets are candidate language only and must not be promoted automatically.
- Issac Davis is the final authority for wording, canon, chronology, the scope of Marcus’s intent, website presentation, pricing, and publication.
- A separate continuity keeper must review any candidate patch against the exact hashes above before author review.
- Acceptance should be granular by proposal ID (`W01`-`W13`); rejecting one proposal must not silently accept or reject the others.
