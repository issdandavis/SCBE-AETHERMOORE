# Show HN launch kit — AI Materials Bench

Post on a weekday morning US-Eastern (Tue–Thu ~8–10am ET tends to do best). No URL in the
title. Post the "first comment" immediately yourself. Reply to every comment fast, and never
ask for upvotes.

---

## Title
```
Show HN: Materials Bench – type a coil/tube build, get physics + BOM, in-browser
```

## URL
```
<your live demo URL — e.g. https://aethermoore.com/ai-materials-bench>
```

## Text (the post body)

I built a small tool that turns a plain build description — a fiber/coil/tube concept — into
a first-pass engineering concept report. You type something like "quartz tube, copper
micro-winding, ferrite flux guide," set a few numbers, and it returns:

- conductor-aware physics: coil resistance, solenoid field, power, skin depth, optical NA
  (the numbers actually change if you say silver vs copper vs aluminum — it's not a label)
- a costed bill of materials with a price range
- a safety envelope: operating voltage, and the max continuous current that keeps the coil
  inside a 5 W bench-thermal budget
- a measurement test plan with target values
- a downloadable .md report with a provenance receipt

The part I care about: it runs **100% in your browser**. No signup, no account, no backend.
The physics is ~200 lines of plain JS you can read in devtools — every number comes from an
explicit formula, not an LLM black box. It works offline and on a static host.

Honest about what it is: these are first-pass estimates. The field math is an ideal-solenoid
model, so real coils read lower; the BOM is rough hobbyist pricing, not quotes; nothing here
replaces real engineering or a current-limited bench test. It's meant to get you from "vague
idea" to "buildable first sketch with a parts list," fast.

I'm a solo builder and I'd genuinely like to be told where the physics is wrong — that's the
feedback I want most.

## First comment (post this yourself, right after submitting)

Context on the "why": I've been building a pile of "AI tool" front ends and got tired of
demos that return vague hand-waving you can't check or act on. So the rule for this one was:
every output has to be a real number from a real formula, inspectable and exportable — and
the demo can't require a signup or a server, because a demo that 404s or gates you is worse
than no demo.

It's deliberately client-side and boring under the hood — there's no model call in the demo
path at all. Open devtools and you can read the whole engine. Please tear the physics apart,
especially the solenoid-field estimate and the skin-depth calc; I want to know what I got
wrong before anyone builds off it.

---

## Notes before you post
- **Fill the URL** with wherever you deploy it (the page is static + client-side, so GitHub
  Pages or any host works — it won't 404 or gate the demo).
- **The honesty is the strategy.** The "ideal-solenoid, real coils read lower / BOM is rough
  / not a substitute for engineering" lines aren't hedging — on HN they're trust. Keep them.
- **Be there for the first 2 hours.** Answer every technical comment plainly; if someone
  finds a physics bug, thank them and say you'll fix it (then fix it — that thread becomes
  your best advertisement).
- Cross-post the same thing to r/AskElectronics or r/diyelectronics afterward; that's closer
  to this tool's actual audience than HN's core.
