# Bookforge Studio system map

Status: implemented and locally validated, 2026-10-28

## Capability being added

Bookforge Studio becomes a local-first publishing workbench that can ingest a
Markdown or plain-text manuscript and optional cover image, derive editable
book metadata and cover/blurb drafts, preview page ornament choices, run KDP
mechanical and image checks, and export the profile/manuscript/blurb files used
by the existing Python Bookforge build engine.

KDP upload and final approval remain human-confirmed steps. Amazon's Bookshelf,
Cover Studio, cover-template generator, and Print Previewer are external systems;
there is no repo-owned KDP publishing API in this lane.

## Nodes and authority

| Node | Exact path or URL | Role / authority | Status | Inputs | Outputs / consumers |
|---|---|---|---|---|---|
| Existing browser studio | `docs/bookforge-writing-studio.html` | Public static/PWA surface | Executable, narrow | Form input | Browser preview and prompts |
| Bookforge engine | `packages/bookforge/src/scbe_bookforge/` | Canonical local build engine | Executable; focused tests | `bookforge.json`, Markdown, optional blurb | Interior PDF, cover-wrap PDF, EPUB, DOCX |
| Existing KDP checklist | `docs/downloads/kdp-bookforge-checklist.md` | Human handoff checklist | Current but manually maintained | KDP guidance | Author review |
| Watershed manuscript | `C:\dev\clay_sources\novels\watershed-cultivation\WATERSHED_MANUSCRIPT.md` | Author-owned source fixture; SHA-256 recorded by discovery | Existing, 514,082 bytes | Story chapters | Studio import; existing KDP builders |
| Watershed metadata | `C:\dev\clay_sources\novels\watershed-cultivation\KDP_DESCRIPTION.md` | Author-owned title/blurb/metadata authority | Existing | Story synthesis | Back cover and listing draft |
| Watershed cover brief | `C:\dev\clay_sources\novels\watershed-cultivation\research\cover-art-market-and-generation-brief.md` | Current art-direction authority | Existing design | Story motifs and market read | Cover concept / art prompt |
| SCBE gallery chromatics | `src/crypto/gallery_chromatics.py` | Security/gallery color encoding, not print science | Executable but domain-mismatched | Encoded bytes/colors | Reused only as optional palette vocabulary |
| SCBE sieve calculator | `python/scbe/sieve_calc.py` | Deterministic number/category calculation, not image processing | Executable but domain-mismatched | Integers/categories | Rejected for pixel enhancement |
| Browser image preflight | `docs/static/bookforge-studio-core.js` | Deterministic local analysis | IMPLEMENTED | Local image pixels and intended print size | DPI, clipping, luminance and saturation diagnostics |
| Browser studio controller | `docs/static/bookforge-studio.js` | Local workflow/state layer | IMPLEMENTED | Local files and author choices | Preview, editable drafts, downloads |
| Official KDP rules | `https://kdp.amazon.com/en_US/help/` | Final mechanical authority | External/current as of 2026-10-28 | Binding, trim, ink, paper, pages | Rules and manual Previewer |
| KDP cover template | `https://kdp.amazon.com/cover-templates` | Exact final cover dimensions, especially hardcover | External/manual | Final page count and print choices | PNG/PDF template |
| KDP Print Previewer | KDP Bookshelf | Final automated preview gate | External/manual | Uploaded files | Errors/warnings before publishing |

Discovery receipt: `artifacts/bookforge-system-inventory-20261028.json`.

## Edges

```text
author files (local)
  -> browser File API [measured locally; no upload]
  -> manuscript/image analyzers [deterministic]
  -> editable metadata + blurb + cover brief [heuristic draft]
  -> bookforge.json + manuscript.md + blurb.json [download]
  -> Python Bookforge engine [existing executable path]
  -> PDF / EPUB / DOCX + preflight report [local artifacts]
  -> KDP Bookshelf + official template + Print Previewer [manual]
  -> proof copy / publication [Amazon review; external]
```

The Watershed files feed the same import edge as any other book. They are not
copied into the public web app and are not seed data in local storage.

## Invariants and schemas

- Manuscript contents remain in browser memory/local storage only when the
  author explicitly saves; the default implementation does not send them over
  the network.
- Imported manuscript types in the first slice are UTF-8 `.md` and `.txt`.
- Cover/image analysis never overwrites an original. Adjustments are previewed
  and exported to a new PNG.
- Print images are checked against an intended physical size and 300 DPI.
- Paperback dimensions use KDP's published bleed and spine formulas.
- Hardcover output is marked template-required: KDP case laminate uses 0.51 in
  wrap and 0.4 in hinges, and exact file size comes from KDP's template.
- KDP does not support spot colors. “Gold” is a simulated process-color visual,
  not metallic foil, gilded edges, or a manufacturing promise.
- A print wrap is one PDF; an ebook cover is a front-only RGB image.
- Spine text is disabled below 80 pages.
- Generated blurbs and cover prompts are drafts and stay editable.

## Controls and success criteria

Baseline: the current studio only calculates simple paperback dimensions and
builds prompt text. No-intervention control: existing Python Bookforge tests and
artifacts must remain unchanged when new profile fields are absent.

Success requires:

1. Deterministic unit checks for spine math, manuscript statistics, blurb draft
   shape, image metrics, hardcover warnings, and profile export.
2. Existing `packages/bookforge/tests/test_smoke.py` remains green.
3. Browser smoke: app loads without console errors, imports a fixture, updates
   the dashboard, switches ornament/format states, analyzes a cover image, and
   downloads a project packet.
4. Desktop and mobile screenshots show no clipping or unreadable controls.
5. A Watershed profile can build local artifacts without modifying the source
   manuscript.

The equal-width/model controls from training systems do not apply: this is a
deterministic publishing tool, not a learned model. The relevant ablation is a
raw-image/no-adjustment export compared with an adjusted preview; both preserve
the original input.

## Budget, saves, rollback, and stops

- Compute: browser CPU only for text/image inspection; no training or GPU.
- Disk: source changes plus small test fixtures; generated QA files remain
  outside committed source unless they are release assets.
- Network: official KDP research and links only. No manuscript or image upload.
- Immutable discovery save: `artifacts/bookforge-system-inventory-20261028.json`.
- Rollback: revert the new static files and the scoped HTML/service-worker edits;
  existing Python Bookforge behavior remains the fallback.
- Stop the build if an existing target file has unrelated dirty changes, the
  app would need to transmit manuscript text, hardcover sizing is being guessed
  instead of template-backed, or browser QA shows data loss or a broken export.

## Post-build update

## Story fire graph build gate — 2026-10-28

Capability: add a local, interactive story map where chapters form the time
axis, recurring characters occupy lanes, and extracted character moments are
colored and sized by narrative heat. This interprets “fire graph” as a force-
graph-like story visualization with an explicit intensity dimension.

Reused nodes are `analyzeManuscript`, the imported manuscript held by the
studio controller, existing dialog controls, local downloads, and the
Watershed manuscript as the real holdout. New nodes are a deterministic
`analyzeStoryGraph(text)` result and a dependency-free responsive SVG renderer.

Schema crossing the edge:

```text
manuscript text
  -> chapters[{id,index,title,wordCount,heat,characters,excerpt}]
  -> characters[{id,name,appearances,chapterIds,momentCount}]
  -> moments[{id,chapterId,character,text,heat,type}]
  -> SVG nodes/edges + selected-node detail + JSON export
```

Invariants: analysis is local and deterministic; source text is never uploaded;
heat is a heuristic editorial signal, not sentiment truth; extracted names and
moments remain inspectable; graph size is bounded for browser responsiveness;
and KDP profile/PDF output is unchanged. The downstream risk is stale graph
state after import/restore, false proper-name detections, and unreadable density
on mobile or a 43-chapter novel.

Controls: the no-intervention control is the existing six browser-core tests
and ten Python Bookforge tests. New unit fixtures must prove stable chapter
segmentation, recurring-character ranking, moment-to-chapter binding, heat
ordering, and bounded output. The Watershed holdout must render all chapter
units without console errors, allow a character filter and node selection, and
fit both desktop and mobile through contained horizontal scrolling. Expected
budget is browser CPU only, under one second for a roughly 90,000-word novel,
with no dependency, network, or model cost. Rollback is limited to the graph
analyzer, dialog markup/styles/controller hooks, service-worker version, tests,
and this map. Stop if the graph transmits content, blocks manuscript import,
changes publication artifacts, or cannot remain usable under the bounded cap.

Discovery receipt:
`artifacts/bookforge-fire-graph-inventory-20261028.json`. The preferred
`scripts/system_inventory.py` helper was absent, so the receipt is a manual,
path-bounded fallback rather than helper output.

### Implemented paths

- Browser: `docs/bookforge-writing-studio.html`, `docs/static/bookforge-studio.css`,
  `docs/static/bookforge-studio-core.js`, `docs/static/bookforge-studio.js`, and
  `docs/bookforge-sw.js`.
- Python engine: `packages/bookforge/src/scbe_bookforge/profile.py`, `cover.py`,
  `interior_reportlab.py`, `manuscript.py`, and `ebook.py`.
- Guidance/tests: `packages/bookforge/README.md`,
  `docs/downloads/kdp-bookforge-checklist.md`,
  `tests/bookforge-studio-core.test.cjs`, and
  `packages/bookforge/tests/test_smoke.py`.
- Watershed: `bookforge.json`, `COVER_AI_DISCLOSURE.md`, cover master/print
  derivative, and `build/bookforge/` artifacts under
  `C:\dev\clay_sources\novels\watershed-cultivation`.

### Verification receipts

- `node --check` passed for both studio JavaScript files.
- `node --test tests/bookforge-studio-core.test.cjs`: 6/6 passed.
- `python -m pytest packages/bookforge/tests/test_smoke.py -q`: 10/10 passed.
- Browser QA with the real Watershed manuscript and cover: 88,717 words,
  43 chapter units, 320 effective cover DPI, no console errors, no desktop
  horizontal overflow, and a clean 390 x 844 mobile layout.
- Watershed print geometry: 387 interior pages at 5 x 8 in; cover wrap one page
  at 11.22 x 8.25 in, sized from an even cover count of 388 pages and a
  0.970 in cream-paper spine.
- PDF font audit: all interior and cover font resources are embedded Georgia
  regular/bold/italic subsets.
- Visual fidelity ledger: the implementation preserves the concept's five-step
  rail, central two-page canvas, right specifications/cover inspector, mineral
  blue-jade palette, serif-book/sans-UI hierarchy, bottom preflight logic, and
  responsive mobile workflow. The concept's seeded sample was intentionally
  replaced by an empty local-import state for privacy.

### Final artifact hashes (SHA-256)

- Manuscript: `7AB1D1AD4CAE85EE59CAE3E5F342028155D4C366E430ABE8FE73A5FEC95C2C16`
- Cover master: `F776A4ECC404A56AE7F5CA435AA30546B2F6A164AAB2A7257DB0E190460514CF`
- 1600 x 2560 print derivative: `AB1BC1EA4584BD56E19300A844E626B3226ACDD913E4AE4B35C011E75B758CB1`
- Interior PDF: `2D1FE4F15C00AD5CC5EE0E8F9B2905B79C94BFCB44148BF5BEDC588ABB79910E`
- Cover PDF: `316106DF5CF1DC9655615736ED6517216B7530034FB6C984F3A2533877E470CE`
- EPUB: `DCEE9DEE1F50240DEE1508DFA6B9D6E8D0A4241FA55FFD02AFAD9527DB23EBA7`
- DOCX: `4C378F69A59AC99FF7144752095C1F00303B820C8B226E92B2B300460CD12419`

### Known limits and resume point

- KDP Bookshelf upload and Print Previewer approval remain manual. These local
  checks are not external acceptance, and a physical proof is still required
  before declaring print color proven.
- Hardcover wrap export remains deliberately blocked until an exact KDP
  case-laminate template is supplied. Simulated gold is process color, not foil.
- Browser image adjustments are pixel-level tonal previews, not ICC soft
  proofing; upscaling cannot recover detail absent from the source image.
- Hybrid/graphic-novel mode is a layout and planning scaffold. No fight-scene
  panels were inserted into the manuscript in this pass.
- Next resume point: choose 6-10 fight scenes, storyboard page turns and panel
  beats, create consistent character sheets, then generate and place print-size
  panels before rerunning interior pagination, wrap sizing, Previewer, and proof.

### Story fire graph post-build evidence — 2026-10-28

Implemented in `docs/static/bookforge-studio-core.js`,
`docs/static/bookforge-studio.js`, `docs/static/bookforge-studio.css`, and
`docs/bookforge-writing-studio.html`; documented in `packages/bookforge/README.md`;
cached as `bookforge-studio-v4`; and covered by
`tests/bookforge-studio-core.test.cjs`.

The deterministic analyzer segments chapters, ranks recurring proper names,
extracts up to four character moments per chapter, classifies five transparent
signal families, and maps raw signal counts to a 5-100 heat scale. The rendered
SVG supports all-cast or single-character lanes, heat filtering, keyboard/click
inspection, automatic centering on the hottest chapter, JSON export, standalone
SVG export, and contained horizontal scrolling.

Verification:

- `node --check` passed for core and controller.
- `node --test tests/bookforge-studio-core.test.cjs`: 7/7 passed, including
  chapter order, recurring-character binding, moment binding, heat ordering,
  hottest-chapter selection, and output caps.
- `python -m pytest packages/bookforge/tests/test_smoke.py -q`: 10/10 passed
  as the no-intervention Bookforge control.
- Watershed holdout: 43 chapters, 10 recurring character lanes, 166 moments,
  heat range 10-76, ordered chapter IDs, and 318 ms analysis time in Node.
- Browser plugin confirmed the page identity and rendered entry state. A bounded
  Playwright fallback was required for local file attachment and console capture.
- Desktop and 390 x 844 mobile passes had no console warnings/errors, no document
  overflow, 43 visible chapter nodes, contained graph scrolling, working Yun
  Zhou filtering (37 visible moments at heat 20), node-detail selection, a
  valid all-cast SVG containing 43 chapter and 166 moment nodes, and a separate
  filtered SVG containing 43 chapter and 37 Yun Zhou moment nodes.

Watershed outputs:

- `build/bookforge/WATERSHED-story-fire-graph.json`, SHA-256
  `670D60B00A5E77560C7B8D06EE0EBE4EFDCC266F95D17AB15E52CE7A499902C2`.
- `build/bookforge/WATERSHED-story-fire-graph.svg`, SHA-256
  `ECE57186E39683D815E3926EF74F90BA8644AF750253AC334A63FA0F366E0789`.
- `build/bookforge/WATERSHED-story-fire-graph-Yun-Zhou.svg`, SHA-256
  `CB8B783BF5F40762F4F7172AB4FC8FEA5ECFF94F7CE0FCFBF87F90F0842D063C`.

Known limitation: proper-name extraction is heuristic. The current Watershed
top ten were manually inspected and are plausible cast names, but an author
should review exported JSON before treating every lane or moment as canon.
The next graph-specific improvement is an editable cast roster and moment
override layer, followed by explicit fight-scene panel markers for hybrid pages.
