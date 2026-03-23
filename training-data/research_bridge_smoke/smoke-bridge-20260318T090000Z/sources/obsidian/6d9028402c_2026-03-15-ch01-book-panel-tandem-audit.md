# Chapter 1 Tandem Audit

Date: 2026-03-15

Scope:
- Manuscript source: `content/book/reader-edition/ch01.md`
- Live packet: `artifacts/webtoon/panel_prompts/ch01_prompts_v4.json`
- Earlier storyboard note: `artifacts/webtoon/ch01_adaptation_script_v3.md`
- Governance report: `artifacts/webtoon/generated_router_hf_full_book/_verification/ch01/ch01_prompts_v4_quality_report.json`

Goal:
- Read the book and the live panel packet in tandem.
- Identify where the adaptation is synchronized with the manuscript.
- Identify where the packet or older storyboard notes drift from the book.

## Verdict

The live `v4` packet is mostly faithful to the emotional and causal order of Chapter 1.

It succeeds at:
- preserving Marcus as a human being before spectacle
- turning the anomaly into a sequence instead of a single summary image
- staging the whiteout and transmission as multiple beats
- grounding the library in sensory detail before exposition
- letting Polly arrive as attitude, not only as plot information
- ending on coffee, impossible geography, and motion deeper into Aethermoor

The biggest drifts are:
- the guest-pass / cease stakes land too late in the `v4` sequence
- the manuscript's security-guard loneliness beat is mostly missing as a visual beat
- the older `v3` adaptation note conflicts with the manuscript on the Earth workspace
- `v4` still has metadata debt that weakens cinematic direction even though it is approved

## Strong Sync Points

### 1. Marcus before rupture

The packet gets the opening logic right:
- stale coffee
- cursor rhythm
- exhaustion and isolation
- wrongness in the logs

This matches the manuscript's real opening job: make Marcus legible as a tired engineer before the world breaks.

Sequences that sync well:
- `ch01-seq01`
- `ch01-seq02`
- `ch01-seq03`

### 2. The anomaly is treated as forensic discovery, not generic magic

The manuscript does not present the log issue as an alarm. It is subtle, valid, elegant, and disturbing because it is not obviously malicious.

The packet preserves that logic well:
- `ch01-v4-p05` wrongness too subtle for alarms
- `ch01-v4-p07` line 4,847
- `ch01-v4-p08` undocumented routing channel
- `ch01-v4-p09` elegant and not malicious
- `ch01-v4-p12` forensic trace launched

That is one of the strongest synchronizations in the chapter.

### 3. The whiteout and the fall are correctly expanded

The manuscript's whiteout is not one image. It is escalation:
- monitor white
- room white
- world erased
- tone compression
- unanswerable intent question
- routed fall

The packet gets this right structurally:
- `ch01-seq04`
- `ch01-seq05`

This is one of the places where the panel logic clearly improves on a one-panel adaptation.

### 4. Arrival in the archive is sensory before explanatory

The manuscript emphasizes:
- stone impact
- self-check
- old books
- ozone
- unnamed resonance
- humming shelves

The packet preserves that order well:
- `ch01-seq06`
- `ch01-seq07`

This is faithful to the book's survival mindset and helps the world feel physical instead of generic fantasy glow.

### 5. Polly's entrance is correctly treated as a layered reveal

The manuscript introduces Polly as:
- voice first
- oversized raven
- mineral eyes
- absurd academic regalia
- precise intelligence

The packet handles this as a proper reveal lane instead of a single character card:
- `ch01-seq08`
- `ch01-seq09`

That is good adaptation logic.

### 6. The ending beats are correctly human

The manuscript does not end on pure spectacle. It ends on:
- impossible geography
- coffee
- Polly's softened answer
- Marcus following anyway

The packet preserves that human exit:
- `ch01-seq13`
- `ch01-seq14`

This is the right instinct.

## Clear Drift Points

### 1. The old `v3` storyboard note is wrong about the Earth workspace

`ch01_adaptation_script_v3.md` says the current panels are wrong because the desk should match the cover:
- home desk
- one curved monitor
- warm desk lamp
- city skyline
- not a corporate office

The manuscript says otherwise:
- Marcus is at work
- his manager stopped asking why
- there is a security guard below
- the overhead fluorescents are off
- the light comes from his three monitors

So the live `v4` packet is actually closer to the book than the old `v3` correction note on this specific issue.

Action:
- treat the manuscript as source of truth
- demote the cover-correction note from canon authority

### 2. The guest-pass / cease stakes are out of order in `v4`

In the manuscript, the order is:
1. Polly says he must learn the Tongues to survive.
2. Marcus asks what kills him here.
3. Polly explains heartbeat verification, flicker, and cease.
4. He stands.
5. Polly transforms.
6. Handshake.
7. Then the Tongues / infrastructure explanation lands.

In the packet, the order is:
- `ch01-seq10`: transform lane
- `ch01-seq11`: handshake lane
- `ch01-seq12`: heartbeat verification, cease, guest pass

That is a real structural drift. It changes when the reader understands the threat.

Action:
- move the guest-pass / cease explanation earlier
- transformation and handshake should follow the threat clarification, not precede it

### 3. The security guard beat is not clearly carried into `v4`

The manuscript explicitly uses the guard below to reinforce:
- office building reality
- loneliness
- one other human in the structure

The packet captures isolation in general, but it does not clearly preserve the security-guard beat as a distinct visual moment.

This matters because that beat deepens the rupture when reality goes white.

Action:
- add or restore a dedicated high-angle guard-below beat in the office sequence

### 4. Some cinematic direction is still missing from the packet itself

The governance report is correct:
- `16` panels are still missing `style_metadata.camera_angle`
- `ch01-v4-p51` has no character binding
- reference-chapter trigger/style-adapter fields are empty

This is not a story-order problem, but it does weaken precise shot control.

Action:
- fill missing camera angles
- assign the patrol-creature/object beat on `ch01-v4-p51` explicitly
- fill `generation_profile.trigger_phrases`
- fill `generation_profile.style_adapter`

## Synchronized vs Drifted Sources

Ranked by trustworthiness for Chapter 1:

1. `content/book/reader-edition/ch01.md`
2. `artifacts/webtoon/panel_prompts/ch01_prompts_v4.json`
3. `artifacts/webtoon/generated_router_hf_full_book/_verification/ch01/ch01_prompts_v4_quality_report.json`
4. `artifacts/webtoon/ch01_adaptation_script_v3.md`

The `v3` note is still useful for pacing ambition and some added beats, but it should not override the manuscript on environmental facts.

## Practical Conclusion

The live `v4` packet already reads like Chapter 1 more than like a generic fantasy conversion.

Where it syncs:
- emotional order
- forensic anomaly logic
- staged rupture
- sensory archive arrival
- Polly reveal
- human ending

Where it does not:
- workspace interpretation in the older adaptation note
- threat-order timing around guest pass / cease
- explicit security-guard loneliness beat
- camera-angle and reference metadata completeness

## Recommended Next Fixes

1. Reorder `ch01-seq10` to `ch01-seq12` so the guest-pass explanation lands before transformation/handshake.
2. Add a dedicated security-guard office beat if it is not already represented visually elsewhere in the final strip.
3. Fill the `16` missing `camera_angle` fields.
4. Bind `ch01-v4-p51` to an explicit non-human subject token.
5. Populate the reference-chapter trigger/style-adapter fields so Chapter 1 can function as the cleaner pilot anchor for later rerenders.
