## Webtoon Reference Chapter Workflow

The book does not need a full weak panel pass first.

The production rule is:

1. Build one good chapter.
2. Use that chapter as the visual, pacing, and continuity anchor.
3. Expand outward only after the anchor chapter works in the reader.

### Why

- Full-book bulk generation creates incoherent panels faster than it creates value.
- The useful artifact is a chapter that proves:
  - Marcus is visually stable
  - Polly is stable in raven and human form
  - page-to-page motion reads cleanly on phone
  - environment language is consistent
  - dialogue beats and spectacle beats land in the right order

### Current Anchor

- Reference chapter: `ch01`
- Reader-preferred reference art lane: `hq`
- Draft lane: `generated`

### Required Properties Of A Reference Chapter

- Strong beat order from source text
- Reusable character bible
- Reusable environment bible
- Clear panel intent per beat
- Readable phone scroll flow
- Canon lane clearly separated from AI draft lane

### Operational Rule

When generating future panels:

- do not treat `generated` as canon
- use `ch01` reference chapter for:
  - character consistency
  - shot rhythm
  - lighting language
  - panel density targets

### Next Build Direction

- regenerate `ch01` only until the flow is right
- compare against the `hq` lane inside the emulator reader
- only then move to `ch02+`

For the concrete generation loop, read [WEBTOON_IMAGE_CONSISTENCY_SYSTEM.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/specs/WEBTOON_IMAGE_CONSISTENCY_SYSTEM.md).
