const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "docs", "static", "bookforge-studio-core.js"), "utf8");
const context = { globalThis: {} };
vm.runInNewContext(source, context, { filename: "bookforge-studio-core.js" });
const core = context.globalThis.BookforgeStudioCore;

test("paperback spine and wrap use KDP white-paper math", () => {
  const spec = core.calculatePrintSpec({ binding: "paperback", trim: "5x8", pageCount: 100, ink: "bw", paper: "white" });
  assert.equal(spec.spineIn, 0.2252);
  assert.equal(spec.coverWidthIn, 10.4752);
  assert.equal(spec.coverHeightIn, 8.25);
  assert.equal(spec.spineTextAllowed, true);
});

test("spine text stays off below 80 pages", () => {
  assert.equal(core.calculatePrintSpec({ trim: "5x8", pageCount: 79, ink: "bw", paper: "cream" }).spineTextAllowed, false);
  assert.equal(core.calculatePrintSpec({ trim: "5x8", pageCount: 80, ink: "bw", paper: "cream" }).spineTextAllowed, true);
});

test("hardcover requires the exact KDP template and rejects standard color", () => {
  const spec = core.calculatePrintSpec({ binding: "hardcover", trim: "5.5x8.5", pageCount: 120, ink: "color_standard", paper: "white" });
  assert.equal(spec.templateRequired, true);
  assert.equal(spec.coverWidthIn, null);
  assert.match(spec.errors.join(" "), /standard color/i);
  assert.match(spec.warnings.join(" "), /0\.51 in wrap/i);
});

test("manuscript analysis and local blurb draft derive from content", () => {
  const manuscript = `# The River Gate\n\n## Chapter 1. Stone\n\nMira found the old gate below the river wall. The water carried a warning no map had recorded.\n\n## Chapter 2. Crossing\n\nShe returned with her brother before the flood reached the village.`;
  const analysis = core.analyzeManuscript(manuscript);
  const blurb = core.draftBlurb({ text: manuscript, title: analysis.title });
  assert.equal(analysis.title, "The River Gate");
  assert.equal(analysis.chapterCount, 2);
  assert.match(blurb.hook, /Mira found the old gate/);
  assert.ok(blurb.paragraphs.length >= 1);
});

test("story fire graph binds recurring characters and hot moments to chapters", () => {
  const manuscript = `# Ember Road

## Chapter 1. The Letter

Mira Vale read the quiet letter beside Sol Renn. Mira Vale folded it and chose to leave.

## Chapter 2. The Bridge

Sol Renn found Mira Vale at the bridge. Mira Vale promised Sol Renn they would cross together.

## Chapter 3. The Burning Gate

Mira Vale drew her sword. Sol Renn shouted as the gate exploded! Mira Vale struck the attacker and refused to run.`;
  const graph = core.analyzeStoryGraph(manuscript, { maxCharacters: 6, maxMomentsPerChapter: 3 });
  assert.equal(Array.from(graph.chapters, (chapter) => chapter.index).join(","), "1,2,3");
  assert.ok(graph.characters.some((character) => character.name === "Mira Vale"));
  assert.ok(graph.characters.some((character) => character.name === "Sol Renn"));
  assert.ok(graph.moments.some((moment) => moment.chapterId === "ch-3" && moment.character === "Mira Vale"));
  assert.ok(graph.chapters[2].heat > graph.chapters[0].heat);
  assert.equal(graph.stats.hottestChapterId, "ch-3");
  assert.ok(graph.moments.length <= 9);
});

test("image metrics flag clipped black and white pixels", () => {
  const metrics = core.analyzePixels(new Uint8ClampedArray([0, 0, 0, 255, 255, 255, 255, 255, 100, 100, 100, 255]));
  assert.equal(Math.round(metrics.shadowClipPct), 33);
  assert.equal(Math.round(metrics.highlightClipPct), 33);
});

test("profile export records ornament and simulated-gold limits", () => {
  const profile = core.buildProfile({
    title: "Test",
    author: "Author",
    ornament: "rose",
    simulatedGold: true,
    pageCount: 100,
    trim: "5x8",
  });
  assert.equal(profile.ornament.style, "rose");
  assert.equal(profile.interior_engine, "reportlab");
  assert.match(profile.cover.note, /not foil/i);
});
