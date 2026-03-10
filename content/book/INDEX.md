# The Six Tongues Protocol — Project Index

**Author**: Issac Davis
**Status**: Book 1 complete (124K words, 27 chapters + 10 interludes + epilogue)
**Last updated**: 2026-03-10

## Directory Structure

```
book/
├── reader-edition/          # CANONICAL manuscript (publication-ready)
│   ├── ch01.md - ch27.md   # 27 chapters
│   ├── ch-rootlight.md      # Epilogue
│   ├── interlude-01 - 10    # 10 multi-POV interludes
│   ├── the-six-tongues-protocol-full.md  # Compiled (124K words)
│   └── canon/               # Canon maps + continuity tracking
│       ├── ch23-27_canon_map.json
│       ├── ch23-27_continuity_flags.md
│       ├── interludes_canon_map.json
│       └── interludes_continuity_flags.md
│
├── annotated-edition/       # Annotated version (ch01-06 + appendix)
├── source/                  # Historical drafts and variant chapters
├── spiral-of-pollyoneth/   # Companion story (Polly's 300-year arc)
│
├── HOUSE_STYLE.md           # Voice, POV, typography rules
├── ISEKAI_7_SENSE_CONTENT_VAULT.md  # Sensory palette + thematic vault
├── KDP_FORMAT.md            # Kindle Direct Publishing spec
├── worldbuilding-geography.md  # Regions, settlements, travel systems
├── build_kdp.py             # KDP Word doc builder
└── INDEX.md                 # This file
```

## Reading Order (with interludes)

| # | File | Title | POV | Words |
|---|------|-------|-----|-------|
| 1 | ch01 | Protocol Handshake | Marcus | 3,504 |
| — | interlude-01 | Polly's Vigil | Polly | 1,804 |
| 2 | ch02 | The Language Barrier | Marcus | 4,141 |
| 3 | ch03 | Hyperbolic Consequences | Marcus | 2,530 |
| 4 | ch04 | The Swarm Beneath | Marcus | 2,957 |
| 5 | ch05 | Intent and Integrity | Marcus | 2,138 |
| — | interlude-06 | Jorren Records | Jorren | 1,601 |
| 6 | ch06 | The Harmonic Wall | Marcus | 2,483 |
| 7 | ch07 | Fleet Dynamics | Marcus | 3,145 |
| — | interlude-04 | Bram's Report | Bram | 1,637 |
| 8 | ch08 | Rogue Signatures | Marcus | 2,556 |
| — | interlude-09 | Tovak Hides | Tovak | 1,233 |
| 9 | ch09 | The Architect's Children | Marcus | 4,056 |
| — | interlude-02 | The Garden Before | Kael (14) | 2,376 |
| 10 | ch10 | The Dead Author's Code | Marcus | 2,428 |
| — | interlude-03 | Senna Before Dawn | Senna | 2,206 |
| 11 | ch11 | The Void Seed | Marcus | 3,729 |
| 12 | ch12 | The Rite of Binding | Marcus | 4,403 |
| 13 | ch13 | The First Incursion | Marcus | 3,733 |
| — | interlude-07 | Nadia Runs | Nadia | 1,752 |
| 14 | ch14 | Threshold Country | Marcus | 6,240 |
| 15 | ch15 | The Fractal Proof | Marcus | 5,428 |
| 16 | ch16 | The Long Watch | Marcus | 5,361 |
| 17 | ch17 | The Outer Ring | Marcus | 2,935 |
| 18 | ch18 | The Industrial Hum | Marcus | 3,779 |
| 19 | ch19 | The Memory Tithe | Marcus | 3,221 |
| 20 | ch20 | The Seventh Absence | Marcus | 5,007 |
| — | interlude-10 | Aria's Garden | Aria | 1,633 |
| 21 | ch21 | The Earth Thread | Marcus | 4,800 |
| 22 | ch22 | The Intention Dimension | Marcus | 3,345 |
| 23 | ch23 | The Underroot | Marcus | 4,066 |
| 24 | ch24 | The Time Tax | Marcus | 3,551 |
| — | interlude-08 | The Pipe | Izack | 2,290 |
| 25 | ch25 | Ordered Witness | Marcus | 4,346 |
| — | interlude-05 | Alexander Holds | Alexander | 2,061 |
| 26 | ch26 | The Keys | Marcus | 3,371 |
| 27 | ch27 | The Architect | Marcus | 4,323 |
| E | ch-rootlight | Rootlight | Marcus | 4,032 |

**Total: ~123,600 words**

## POV Coverage

- **Marcus Chen**: 27 chapters + epilogue (main POV)
- **Polly**: Interlude 01 (Polly's Vigil)
- **Kael Thorne (age 14)**: Interlude 02 (The Garden Before)
- **Senna Thorne**: Interlude 03 (Senna Before Dawn)
- **Bram Cortez**: Interlude 04 (Bram's Report)
- **Alexander Thorne**: Interlude 05 (Alexander Holds)
- **Jorren Hale**: Interlude 06 (Jorren Records)
- **Nadia Kest**: Interlude 07 (Nadia Runs)
- **Izack Thorne**: Interlude 08 (The Pipe)
- **Tovak Rel**: Interlude 09 (Tovak Hides)
- **Aria Ravencrest Thorne**: Interlude 10 (Aria's Garden)

## Sacred Tongue Coverage (Interludes)

| Tongue | Interlude | Character |
|--------|-----------|-----------|
| KO (Intent) | Alexander Holds | Alexander |
| AV (Transport) | Nadia Runs | Nadia |
| RU (Policy) | referenced in multiple | — |
| CA (Compute) | Bram's Report | Bram |
| UM (Security) | Tovak Hides | Tovak |
| DR (Schema) | Jorren Records | Jorren |

## Build Commands

```bash
# Rebuild compiled manuscript
cd content/book/reader-edition
cat ch01.md interlude-01-pollys-vigil.md ch02.md ... > the-six-tongues-protocol-full.md

# Build KDP Word document
python content/book/build_kdp.py
```
