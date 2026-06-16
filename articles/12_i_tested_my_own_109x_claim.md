# I said my code was 109× faster than Python. I tested it. Here's the real number.

A while back I built a Rust version of an AST encoder I'd been running in Python, and at
some point the number "109×" got attached to it. Faster than Python. Hundred-ex. The kind of
number you put in a README and feel good about.

This week I went to actually prove it — not because anyone asked, but because I'm trying to
build things people can trust, and a number you can't reproduce isn't a feature, it's a
liability waiting for the first person who checks. So I wrote a real benchmark: warmup runs,
20+ measured runs, mean/median/standard deviation, coefficient of variation, the works. Then
I ran it on my own (noisy) laptop *and* on a clean Kaggle box, so it wasn't just one lucky
machine.

Here's what came back.

| What I measured | Result |
|---|---|
| Full encode, end-to-end (laptop) | **~3.4× faster** |
| Full encode, end-to-end (Kaggle, different machine) | **4.53×** |
| Engine only, subprocess startup removed | **~4.6×** |
| Parse-only, fastest parser (ruff) vs Python `ast.parse` | **6.3×** |
| Parse-only, the parser my build actually uses vs Python | **2.0×** |
| **109×** | **reproduces nowhere** |

So. Not 109×. About 4–5× for the real thing, 6× best-case for the slice I could cherry-pick.

Why the gap? A couple of honest reasons:

1. **Python's parser isn't Python.** `ast.parse` is implemented in C under the hood. So I
   was never racing "Python" — I was racing C. And `ruff`, the fastest Python parser that
   exists, only gets ~6× over that C parser on my files. There isn't a hidden 100× sitting in
   "parse some Python" — the baseline is already fast. I wasn't underperforming; I was bumping
   into physics.
2. **The 109× was a different measurement.** It came from a specific parser fork on a
   parse-heavy workload, almost certainly with the process-startup cost excluded — basically
   the most favorable slice possible. The build I actually ship doesn't run that way.

I could've buried this. Nobody would've known. Instead I'm writing it down, because here's
the thing I actually believe: **a reproduced 4.5× beats an unreproducible 109× every single
time.** The 109× is a number that makes you look like a liar the moment someone runs it
themselves. The 4.5× is a number I can hand you with the exact command, the environment, the
spread, and a second machine that agrees — and you can check me. One of those builds trust.
The other one spends it.

The AI/dev world is drowning in 100× claims right now. I'd rather be the guy whose smaller
number is *true* than the guy whose big number evaporates under a stopwatch.

The receipts are committed — the harness, the score cards, the Kaggle run, all of it. If you
want to tear it apart, please do; that's the point. Finding out my hype was 20× too big isn't
a bad day. It's just the part of building where you stop telling stories and start keeping
records.

More of these coming. I'm building a coding system out in the open, and I'm going to publish
the real numbers — the good ones and the ones that humble me. If that's your kind of thing,
stick around.

— Issac
