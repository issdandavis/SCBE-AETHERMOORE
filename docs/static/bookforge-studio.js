(function () {
  "use strict";

  const core = window.BookforgeStudioCore;
  if (!core) throw new Error("Bookforge Studio core did not load");

  const byId = (id) => document.getElementById(id);
  const state = {
    manuscriptText: "",
    manuscriptName: "manuscript.md",
    analysis: core.analyzeManuscript(""),
    edition: "novel",
    ornament: "water_channel",
    coverFileName: "",
    coverObjectUrl: "",
    coverImageElement: null,
    imageDpi: 0,
    imageMetrics: null,
    blurb: { hook: "", paragraphs: [], provenance: "" },
    storyGraph: core.analyzeStoryGraph(""),
    zoom: 1,
  };

  const elements = {
    title: byId("bookTitle"),
    author: byId("author"),
    subtitle: byId("subtitle"),
    genre: byId("genre"),
    manuscriptFile: byId("manuscriptFile"),
    manuscriptName: byId("manuscriptName"),
    coverFile: byId("coverFile"),
    coverName: byId("coverName"),
    binding: byId("binding"),
    trim: byId("trim"),
    pages: byId("pages"),
    ink: byId("ink"),
    paper: byId("paper"),
    coverFinish: byId("coverFinish"),
    printSpec: byId("printSpec"),
    emptyManuscript: byId("emptyManuscript"),
    pageStage: byId("pageStage"),
    spread: byId("spreadPreview"),
    previewMode: byId("previewMode"),
    canvas: byId("imageCanvas"),
    blackPoint: byId("blackPoint"),
    contrast: byId("contrast"),
    saturation: byId("saturation"),
    preflightChecks: byId("preflightChecks"),
    fireGraphSvg: byId("fireGraphSvg"),
    fireCharacterFilter: byId("fireCharacterFilter"),
    fireHeatFilter: byId("fireHeatFilter"),
    toast: byId("toast"),
  };

  let toastTimer = 0;
  let imageFrame = 0;

  function toast(message) {
    window.clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.add("show");
    toastTimer = window.setTimeout(() => elements.toast.classList.remove("show"), 2600);
  }

  function slugify(value) {
    return String(value || "book")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "book";
  }

  function downloadBlob(name, blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function downloadText(name, text, type) {
    downloadBlob(name, new Blob([text], { type: type || "text/plain;charset=utf-8" }));
  }

  function currentOptions() {
    return {
      binding: elements.binding.value,
      trim: elements.trim.value,
      pageCount: Number(elements.pages.value) || 0,
      ink: elements.ink.value,
      paper: elements.paper.value,
      dpi: state.imageDpi,
      wordCount: state.analysis.wordCount,
    };
  }

  function currentProfile() {
    return core.buildProfile({
      title: elements.title.value.trim(),
      subtitle: elements.subtitle.value.trim(),
      author: elements.author.value.trim(),
      source: "manuscript.md",
      binding: elements.binding.value === "ebook" ? "paperback" : elements.binding.value,
      trim: elements.trim.value,
      pageCount: Number(elements.pages.value) || null,
      ink: elements.ink.value,
      paper: elements.paper.value,
      coverFinish: elements.coverFinish.value,
      ornament: state.ornament,
      coverArtName: state.coverFileName ? `cover/${state.coverFileName.replace(/\.[^.]+$/, "-print.png")}` : "",
      simulatedGold: byId("simulatedGold").checked,
      hook: state.blurb.hook,
      blurbParagraphs: state.blurb.paragraphs,
    });
  }

  function setText(id, value) {
    byId(id).textContent = value;
  }

  function paragraphsFromExcerpt(excerpt) {
    const blocks = String(excerpt || "")
      .split(/\n\s*\n/)
      .map((item) => item.trim())
      .filter(Boolean);
    if (blocks.length >= 5) return blocks.slice(0, 8);
    const sentences = String(excerpt || "").match(/[^.!?]+[.!?]+/g) || [];
    return sentences.map((sentence) => sentence.trim()).filter(Boolean).slice(0, 10);
  }

  function renderPreview() {
    const imported = Boolean(state.manuscriptText);
    elements.emptyManuscript.hidden = imported;
    elements.pageStage.hidden = !imported;
    if (!imported) return;

    const paragraphs = paragraphsFromExcerpt(state.analysis.excerpt);
    const midpoint = Math.max(1, Math.ceil(paragraphs.length / 2));
    const renderInto = (target, values) => {
      target.replaceChildren();
      for (const value of values) {
        const p = document.createElement("p");
        p.textContent = value;
        target.appendChild(p);
      }
    };
    renderInto(byId("previewLeft"), paragraphs.slice(0, midpoint));
    renderInto(byId("previewRight"), paragraphs.slice(midpoint));
    setText("previewChapter", state.analysis.title || elements.title.value);
    document.querySelectorAll(".bf-page").forEach((page) => page.setAttribute("data-ornament", state.ornament));
    setText("previewPageCount", String(Number(elements.pages.value) || state.analysis.estimatedPages || "—"));
  }

  const SVG_NS = "http://www.w3.org/2000/svg";

  function svgNode(tag, attributes, text) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attributes || {})) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function heatColor(heat) {
    if (heat >= 55) return "#e24d2c";
    if (heat >= 32) return "#e7a141";
    return "#64aeb6";
  }

  function detailMeta(values) {
    const row = document.createElement("div");
    row.className = "bf-fire-detail-meta";
    values.filter(Boolean).forEach((value) => {
      const item = document.createElement("span");
      item.textContent = value;
      row.appendChild(item);
    });
    return row;
  }

  function showFireDetail(kind, item) {
    const panel = byId("fireGraphDetails");
    panel.replaceChildren();
    const eyebrow = document.createElement("span");
    eyebrow.className = "bf-fire-eyebrow";
    eyebrow.textContent = kind === "chapter" ? `Chapter ${item.index}` : `${item.character} · chapter ${item.chapterIndex}`;
    const title = document.createElement("h3");
    const body = document.createElement("p");
    if (kind === "chapter") {
      title.textContent = item.title;
      body.textContent = item.excerpt || "No excerpt was available.";
      panel.append(eyebrow, title, detailMeta([`Heat ${item.heat}/100`, `${item.wordCount.toLocaleString()} words`, `${item.characters.length} mapped characters`]), body);
      if (item.characters.length) {
        const names = document.createElement("div");
        names.className = "bf-fire-character-list";
        item.characters.forEach((name) => {
          const chip = document.createElement("span");
          chip.textContent = name;
          names.appendChild(chip);
        });
        panel.appendChild(names);
      }
    } else {
      const chapter = state.storyGraph.chapters.find((candidate) => candidate.id === item.chapterId);
      title.textContent = chapter ? chapter.title : "Character moment";
      body.textContent = item.text;
      panel.append(eyebrow, title, detailMeta([`Heat ${item.heat}/100`, item.type]), body);
    }
  }

  function makeGraphNode(kind, item, cx, cy, radius) {
    const circle = svgNode("circle", {
      class: "bf-fire-node",
      "data-kind": kind,
      cx,
      cy,
      r: radius,
      fill: heatColor(item.heat),
      tabindex: 0,
      role: "button",
      "aria-label": kind === "chapter" ? `Chapter ${item.index}, ${item.title}, heat ${item.heat}` : `${item.character} in chapter ${item.chapterIndex}, heat ${item.heat}`,
    });
    const label = kind === "chapter" ? `Chapter ${item.index}: ${item.title}` : `${item.character}: ${item.text}`;
    circle.appendChild(svgNode("title", {}, `${label} · heat ${item.heat}`));
    const select = () => showFireDetail(kind, item);
    circle.addEventListener("click", select);
    circle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
    return circle;
  }

  function renderFireGraph() {
    const graph = state.storyGraph;
    const svg = elements.fireGraphSvg;
    svg.replaceChildren();
    if (!graph.chapters.length) {
      svg.setAttribute("viewBox", "0 0 900 520");
      svg.appendChild(svgNode("text", { x: 450, y: 250, "text-anchor": "middle", class: "bf-fire-label" }, "Import a manuscript to light the story graph."));
      return;
    }

    const selectedCharacter = elements.fireCharacterFilter.value;
    const minimumHeat = Number(elements.fireHeatFilter.value) || 5;
    const activeCharacters = selectedCharacter === "all"
      ? graph.characters
      : graph.characters.filter((character) => character.id === selectedCharacter);
    const activeIds = new Set(activeCharacters.map((character) => character.id));
    const moments = graph.moments.filter((moment) => moment.heat >= minimumHeat && activeIds.has(moment.characterId));
    const left = 145;
    const top = 55;
    const laneGap = 58;
    const width = Math.max(900, left + graph.chapters.length * 92 + 50);
    const chapterY = top + activeCharacters.length * laneGap + 64;
    const height = Math.max(520, chapterY + 120);
    const usableWidth = width - left - 55;
    const xForChapter = (index) => left + (graph.chapters.length === 1 ? usableWidth / 2 : ((index - 1) / (graph.chapters.length - 1)) * usableWidth);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);

    activeCharacters.forEach((character, laneIndex) => {
      const y = top + laneIndex * laneGap;
      svg.appendChild(svgNode("line", { x1: left, y1: y, x2: width - 40, y2: y, class: "bf-fire-lane" }));
      svg.appendChild(svgNode("text", { x: 18, y: y + 4, class: "bf-fire-label" }, character.name));
      const points = moments
        .filter((moment) => moment.characterId === character.id)
        .sort((a, b) => a.chapterIndex - b.chapterIndex)
        .map((moment) => `${xForChapter(moment.chapterIndex)},${y}`)
        .join(" ");
      if (points.includes(" ")) svg.appendChild(svgNode("polyline", { points, class: "bf-fire-path" }));
    });

    svg.appendChild(svgNode("line", { x1: left, y1: chapterY, x2: width - 40, y2: chapterY, class: "bf-fire-baseline" }));
    graph.chapters.forEach((chapter) => {
      const x = xForChapter(chapter.index);
      svg.appendChild(makeGraphNode("chapter", chapter, x, chapterY, 7 + chapter.heat / 12));
      const label = svgNode("text", { x: x + 4, y: chapterY + 28, class: "bf-fire-chapter-label", transform: `rotate(42 ${x + 4} ${chapterY + 28})` }, `${chapter.index}. ${chapter.title.slice(0, 34)}`);
      svg.appendChild(label);
    });

    const laneByCharacter = new Map(activeCharacters.map((character, index) => [character.id, top + index * laneGap]));
    const momentTotals = new Map();
    moments.forEach((moment) => {
      const key = `${moment.characterId}:${moment.chapterId}`;
      momentTotals.set(key, (momentTotals.get(key) || 0) + 1);
    });
    const momentSeen = new Map();
    moments.forEach((moment) => {
      const y = laneByCharacter.get(moment.characterId);
      const key = `${moment.characterId}:${moment.chapterId}`;
      const ordinal = momentSeen.get(key) || 0;
      momentSeen.set(key, ordinal + 1);
      const x = xForChapter(moment.chapterIndex) + (ordinal - (momentTotals.get(key) - 1) / 2) * 10;
      svg.appendChild(svgNode("line", { x1: x, y1: y + 9, x2: x, y2: chapterY - 12, class: "bf-fire-lane" }));
      svg.appendChild(makeGraphNode("moment", moment, x, y, 4 + moment.heat / 18));
    });

    setText("fireHeatValue", String(minimumHeat));
    setText("fireGraphStats", `${graph.chapters.length} chapters · ${activeCharacters.length} character lanes · ${moments.length} visible moments`);
  }

  function prepareFireGraph() {
    state.storyGraph = core.analyzeStoryGraph(state.manuscriptText, { maxCharacters: 10, maxMomentsPerChapter: 4 });
    const button = byId("openFireGraph");
    button.disabled = !state.storyGraph.chapters.length;
    const stats = state.storyGraph.stats;
    setText(
      "fireGraphSummary",
      stats.chapterCount
        ? `${stats.chapterCount} chapters · ${stats.characterCount} recurring characters · ${stats.momentCount} mapped moments`
        : "Import a manuscript to map chapters and character moments.",
    );
    const current = elements.fireCharacterFilter.value;
    elements.fireCharacterFilter.replaceChildren(new Option("All recurring characters", "all"));
    state.storyGraph.characters.forEach((character) => {
      elements.fireCharacterFilter.appendChild(new Option(`${character.name} (${character.appearances} chapters)`, character.id));
    });
    elements.fireCharacterFilter.value = state.storyGraph.characters.some((character) => character.id === current) ? current : "all";
  }

  function openFireGraph() {
    if (!state.manuscriptText) {
      toast("Import a manuscript before opening the story graph.");
      return;
    }
    renderFireGraph();
    const hottest = state.storyGraph.chapters.find((chapter) => chapter.id === state.storyGraph.stats.hottestChapterId) || state.storyGraph.chapters[0];
    if (hottest) showFireDetail("chapter", hottest);
    byId("fireGraphDialog").showModal();
    window.requestAnimationFrame(() => {
      const wrap = document.querySelector(".bf-fire-canvas-wrap");
      if (!wrap || !hottest || state.storyGraph.chapters.length < 2) return;
      const progress = (hottest.index - 1) / (state.storyGraph.chapters.length - 1);
      wrap.scrollLeft = Math.max(0, progress * wrap.scrollWidth - wrap.clientWidth / 2);
    });
  }

  function exportFireGraphSvg() {
    if (!state.storyGraph.chapters.length) return;
    const clone = elements.fireGraphSvg.cloneNode(true);
    clone.setAttribute("xmlns", SVG_NS);
    clone.setAttribute("style", "background:#0d2430;font-family:Segoe UI,Arial,sans-serif");
    const style = svgNode(
      "style",
      {},
      ".bf-fire-lane{stroke:rgba(159,200,208,.22);stroke-width:1;stroke-dasharray:3 7}.bf-fire-baseline{stroke:#e07a3f;stroke-width:2;opacity:.7}.bf-fire-path{fill:none;stroke:#73b5bd;stroke-width:1.5;opacity:.5}.bf-fire-label{fill:#c4dce0;font-size:12px;font-weight:700}.bf-fire-chapter-label{fill:#a8c2c8;font-size:10px}.bf-fire-node[data-kind=chapter]{stroke:#ffe7bc;stroke-width:1.8}.bf-fire-node[data-kind=moment]{stroke:rgba(255,246,226,.75);stroke-width:1}",
    );
    clone.prepend(style);
    const source = `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(clone)}\n`;
    downloadText(`${slugify(elements.title.value)}-story-fire-graph.svg`, source, "image/svg+xml;charset=utf-8");
  }

  function applyBookIdentity() {
    const title = elements.title.value.trim() || "Untitled book";
    const author = elements.author.value.trim() || "Author";
    setText("frontTitle", title);
    setText("spineTitle", title);
    setText("frontAuthor", author.toUpperCase());
  }

  function applyBlurbToPreview() {
    setText("backHook", state.blurb.hook || "Back-cover hook");
    setText("backCopy", state.blurb.paragraphs.join(" ") || "Import a manuscript, then draft or paste the back-cover copy.");
    byId("blurbHook").value = state.blurb.hook || "";
    byId("blurbBody").value = state.blurb.paragraphs.join("\n\n");
    byId("blurbProvenance").textContent = state.blurb.provenance || "Draft copy is editable and should be reviewed against the full story.";
  }

  function updateFormatControls() {
    const binding = elements.binding.value;
    const ebook = binding === "ebook";
    elements.trim.disabled = ebook;
    elements.pages.disabled = ebook;
    elements.ink.disabled = ebook;
    elements.paper.disabled = ebook || elements.ink.value !== "bw";
    byId("simulatedGold").disabled = binding !== "hardcover";
    if (binding !== "hardcover") byId("simulatedGold").checked = false;
    if (binding === "hardcover" && elements.ink.value === "color_standard") elements.ink.value = "color_premium";
    if (elements.ink.value !== "bw") {
      elements.paper.value = "white";
      elements.paper.disabled = true;
    }
  }

  function renderPrintSpec() {
    updateFormatControls();
    const binding = elements.binding.value;
    if (binding === "ebook") {
      elements.printSpec.dataset.tone = "";
      elements.printSpec.textContent = "Kindle cover: front-only RGB image, ideally 1600 × 2560 px. No print wrap or spine.";
      return;
    }
    const spec = core.calculatePrintSpec(currentOptions());
    const message = spec.templateRequired
      ? `Spine estimate ${spec.spineIn.toFixed(3)} in. Exact hardcover dimensions require KDP's template.`
      : `Spine ${spec.spineIn.toFixed(3)} in · wrap ${spec.coverWidthIn.toFixed(3)} × ${spec.coverHeightIn.toFixed(3)} in.`;
    elements.printSpec.textContent = spec.errors[0] || spec.warnings[0] || message;
    elements.printSpec.dataset.tone = spec.errors.length ? "fail" : spec.warnings.length ? "warn" : "";
  }

  function renderChecks() {
    const result = core.preflight(currentOptions());
    elements.preflightChecks.replaceChildren();
    for (const check of result.checks) {
      const item = document.createElement("article");
      item.className = "bf-check";
      item.dataset.status = check.status;
      const label = document.createElement("span");
      label.textContent = check.label;
      const status = document.createElement("strong");
      status.textContent = check.status === "pass" ? "Ready" : check.status === "fail" ? "Fix" : check.status === "manual" ? "Manual" : "Check";
      const detail = document.createElement("small");
      detail.textContent = check.detail;
      item.append(label, status, detail);
      elements.preflightChecks.appendChild(item);
    }
    return result;
  }

  function reportText() {
    const result = renderChecks();
    const lines = [
      "AETHERMOORE BOOK STUDIO — KDP PREFLIGHT",
      `Generated: ${new Date().toISOString()}`,
      `Title: ${elements.title.value.trim() || "Untitled book"}`,
      `Edition: ${state.edition}`,
      `Format: ${elements.binding.value}`,
      `Trim: ${elements.trim.value}`,
      `Pages: ${elements.pages.value || "not final"}`,
      `Ink / paper: ${elements.ink.value} / ${elements.paper.value}`,
      "",
      ...result.checks.map((check) => `[${check.status.toUpperCase()}] ${check.label}: ${check.detail}`),
      "",
      "MANUAL GATES",
      "- Verify final title/author metadata matches the files.",
      "- Run KDP Print Previewer after upload.",
      "- Order a physical proof before publication.",
      "- Disclose AI-generated cover art or text when required by KDP.",
      "- Simulated gold is process color, not foil or metallic ink.",
    ];
    return lines.join("\n");
  }

  function updateAll() {
    applyBookIdentity();
    renderPreview();
    renderPrintSpec();
    renderChecks();
    updateImageDpi();
  }

  async function importManuscript(file) {
    if (!file) return;
    if (!/\.(md|txt)$/i.test(file.name)) {
      toast("Use a UTF-8 Markdown or text manuscript in this first release.");
      return;
    }
    const text = await file.text();
    state.manuscriptText = text;
    state.manuscriptName = file.name;
    state.analysis = core.analyzeManuscript(text);
    prepareFireGraph();
    elements.manuscriptName.textContent = file.name;
    setText("wordCount", state.analysis.wordCount.toLocaleString());
    setText("chapterCount", String(state.analysis.chapterCount));
    setText("estimatedPages", String(state.analysis.estimatedPages));
    if (elements.title.value === "Untitled book" || !elements.title.value.trim()) elements.title.value = state.analysis.title;
    if (!Number(elements.pages.value)) elements.pages.value = String(state.analysis.estimatedPages);
    renderPreview();
    draftBlurb(false);
    updateAll();
    toast(`${file.name} imported locally.`);
  }

  function draftBlurb(openEditor) {
    if (!state.manuscriptText) {
      toast("Import a manuscript before drafting the blurb.");
      return;
    }
    const drafted = core.draftBlurb({ text: state.manuscriptText, title: elements.title.value.trim() });
    state.blurb = { hook: drafted.hook, paragraphs: drafted.paragraphs, provenance: drafted.provenance };
    applyBlurbToPreview();
    if (openEditor !== false) byId("blurbDialog").showModal();
  }

  function applyBlurbEditor() {
    state.blurb.hook = byId("blurbHook").value.trim();
    state.blurb.paragraphs = byId("blurbBody").value.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean);
    applyBlurbToPreview();
    applyBookIdentity();
    byId("blurbDialog").close();
    toast("Cover copy updated.");
  }

  function renderAdjustedImage() {
    if (!state.coverImageElement) return;
    const image = state.coverImageElement;
    const canvas = elements.canvas;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const contrast = Number(elements.contrast.value);
    const saturation = Number(elements.saturation.value);
    ctx.save();
    ctx.filter = `contrast(${100 + contrast}%) saturate(${100 + saturation}%)`;
    ctx.drawImage(image, 0, 0);
    ctx.restore();

    const blackPoint = Number(elements.blackPoint.value);
    if (blackPoint > 0) {
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const scale = 255 / (255 - blackPoint);
      for (let i = 0; i < imageData.data.length; i += 4) {
        imageData.data[i] = core.clamp((imageData.data[i] - blackPoint) * scale, 0, 255);
        imageData.data[i + 1] = core.clamp((imageData.data[i + 1] - blackPoint) * scale, 0, 255);
        imageData.data[i + 2] = core.clamp((imageData.data[i + 2] - blackPoint) * scale, 0, 255);
      }
      ctx.putImageData(imageData, 0, 0);
    }

    const sample = document.createElement("canvas");
    const sampleScale = Math.min(1, 320 / Math.max(canvas.width, canvas.height));
    sample.width = Math.max(1, Math.round(canvas.width * sampleScale));
    sample.height = Math.max(1, Math.round(canvas.height * sampleScale));
    const sampleCtx = sample.getContext("2d", { willReadFrequently: true });
    sampleCtx.drawImage(canvas, 0, 0, sample.width, sample.height);
    state.imageMetrics = core.analyzePixels(sampleCtx.getImageData(0, 0, sample.width, sample.height));
    setText("shadowClip", `${state.imageMetrics.shadowClipPct.toFixed(1)}%`);
    setText("highlightClip", `${state.imageMetrics.highlightClipPct.toFixed(1)}%`);
    elements.canvas.classList.add("has-image");
    byId("downloadImage").disabled = false;
    updateImageDpi();
    renderChecks();
  }

  function scheduleImageRender() {
    window.cancelAnimationFrame(imageFrame);
    imageFrame = window.requestAnimationFrame(renderAdjustedImage);
  }

  function updateImageDpi() {
    if (!state.coverImageElement) return;
    const trim = core.TRIM_SIZES[elements.trim.value] || [5, 8];
    state.imageDpi = core.effectiveDpi(
      state.coverImageElement.naturalWidth,
      state.coverImageElement.naturalHeight,
      trim[0],
      trim[1],
    );
    setText("imageDpi", `${Math.round(state.imageDpi)} DPI`);
  }

  async function importCover(file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast("Choose a cover image file.");
      return;
    }
    if (state.coverObjectUrl) URL.revokeObjectURL(state.coverObjectUrl);
    state.coverObjectUrl = URL.createObjectURL(file);
    state.coverFileName = file.name;
    const image = new Image();
    image.onload = () => {
      state.coverImageElement = image;
      const coverImage = byId("coverImage");
      coverImage.src = state.coverObjectUrl;
      coverImage.hidden = false;
      elements.coverName.textContent = `${file.name} · ${image.naturalWidth} × ${image.naturalHeight}px`;
      renderAdjustedImage();
      updateAll();
      toast("Cover art imported. Original preserved.");
    };
    image.onerror = () => toast("The browser could not decode that cover image.");
    image.src = state.coverObjectUrl;
  }

  function resetImage() {
    elements.blackPoint.value = "0";
    elements.contrast.value = "0";
    elements.saturation.value = "0";
    updateSliderLabels();
    scheduleImageRender();
  }

  function updateSliderLabels() {
    byId("blackPointValue").value = elements.blackPoint.value;
    byId("contrastValue").value = `${elements.contrast.value}%`;
    byId("saturationValue").value = `${elements.saturation.value}%`;
  }

  function exportAdjustedImage() {
    if (!state.coverImageElement) return;
    const trim = core.TRIM_SIZES[elements.trim.value] || [5, 8];
    const target = document.createElement("canvas");
    target.width = Math.ceil(trim[0] * 300);
    target.height = Math.ceil(trim[1] * 300);
    const targetContext = target.getContext("2d");
    targetContext.imageSmoothingEnabled = true;
    targetContext.imageSmoothingQuality = "high";
    const scale = Math.max(target.width / elements.canvas.width, target.height / elements.canvas.height);
    const width = elements.canvas.width * scale;
    const height = elements.canvas.height * scale;
    targetContext.drawImage(elements.canvas, (target.width - width) / 2, (target.height - height) / 2, width, height);
    target.toBlob((blob) => {
      if (!blob) return;
      downloadBlob(`${slugify(elements.title.value)}-cover-print.png`, blob);
    }, "image/png");
  }

  function projectPayload() {
    return {
      schema: "aethermoore.bookforge-studio.v1",
      saved_at: new Date().toISOString(),
      profile: currentProfile(),
      studio: {
        edition: state.edition,
        manuscript_name: state.manuscriptName,
        cover_source_name: state.coverFileName,
        analysis: state.analysis,
        image_metrics: state.imageMetrics,
        blurb_provenance: state.blurb.provenance,
        story_graph_stats: state.storyGraph.stats,
      },
      manuscript: state.manuscriptText,
    };
  }

  function saveProject() {
    try {
      localStorage.setItem("aethermoore.bookforge-studio.project", JSON.stringify(projectPayload()));
      toast("Project saved in this browser.");
    } catch (error) {
      toast(`Project was not saved: ${error.message}`);
    }
  }

  function restoreProject() {
    const saved = localStorage.getItem("aethermoore.bookforge-studio.project");
    if (!saved) return;
    try {
      const payload = JSON.parse(saved);
      const profile = payload.profile || {};
      elements.title.value = profile.title || "Untitled book";
      elements.subtitle.value = profile.subtitle || "";
      elements.author.value = profile.author || "Issac Davis";
      elements.binding.value = profile.binding || "paperback";
      elements.trim.value = typeof profile.trim === "string" ? profile.trim : "5x8";
      elements.pages.value = profile.page_count || 0;
      elements.ink.value = profile.print?.ink || "bw";
      elements.paper.value = profile.print?.paper || "cream";
      elements.coverFinish.value = profile.print?.cover_finish || "matte";
      state.edition = payload.studio?.edition || "novel";
      state.ornament = profile.ornament?.style || "water_channel";
      state.manuscriptText = payload.manuscript || "";
      state.manuscriptName = payload.studio?.manuscript_name || "manuscript.md";
      state.analysis = core.analyzeManuscript(state.manuscriptText);
      prepareFireGraph();
      state.blurb = {
        hook: profile.hook || "",
        paragraphs: profile.blurb_paragraphs || [],
        provenance: payload.studio?.blurb_provenance || "Restored from local project.",
      };
      elements.manuscriptName.textContent = state.manuscriptName;
      setText("wordCount", state.analysis.wordCount.toLocaleString());
      setText("chapterCount", String(state.analysis.chapterCount));
      setText("estimatedPages", String(state.analysis.estimatedPages));
      document.querySelectorAll("[name='ornament']").forEach((input) => (input.checked = input.value === state.ornament));
      document.querySelectorAll("#editionType button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.value === state.edition)));
      applyBlurbToPreview();
      toast("Restored the project saved in this browser.");
    } catch (error) {
      console.warn("Could not restore Bookforge project", error);
    }
  }

  function exportPacket() {
    if (!state.manuscriptText) {
      toast("Import a manuscript before exporting the KDP packet.");
      return;
    }
    const slug = slugify(elements.title.value);
    const profile = currentProfile();
    const brief = core.coverBrief({ text: state.manuscriptText, title: profile.title, genre: elements.genre.value.trim() });
    downloadText("manuscript.md", state.manuscriptText, "text/markdown;charset=utf-8");
    window.setTimeout(() => downloadText("bookforge.json", `${JSON.stringify(profile, null, 2)}\n`, "application/json"), 160);
    window.setTimeout(() => downloadText(`${slug}-cover-brief.txt`, `${brief.prompt}\n\nAVOID\n${brief.avoid}\n`, "text/plain"), 320);
    window.setTimeout(() => downloadText(`${slug}-kdp-preflight.txt`, reportText(), "text/plain"), 480);
    window.setTimeout(() => downloadText(`${slug}-story-fire-graph.json`, `${JSON.stringify(state.storyGraph, null, 2)}\n`, "application/json"), 640);
    toast("Exporting manuscript, profile, cover brief, preflight, and story graph.");
  }

  function showReport() {
    byId("fullReport").textContent = reportText();
    byId("reportDialog").showModal();
  }

  elements.manuscriptFile.addEventListener("change", (event) => importManuscript(event.target.files[0]).catch((error) => toast(error.message)));
  elements.coverFile.addEventListener("change", (event) => importCover(event.target.files[0]));
  [elements.binding, elements.trim, elements.pages, elements.ink, elements.paper, elements.coverFinish].forEach((input) =>
    input.addEventListener("input", updateAll),
  );
  [elements.title, elements.author, elements.subtitle].forEach((input) => input.addEventListener("input", applyBookIdentity));

  document.querySelectorAll("#editionType button").forEach((button) => {
    button.addEventListener("click", () => {
      state.edition = button.dataset.value;
      document.querySelectorAll("#editionType button").forEach((candidate) => candidate.setAttribute("aria-pressed", String(candidate === button)));
      toast(`${button.textContent.trim()} edition selected.`);
    });
  });

  document.querySelectorAll("[name='ornament']").forEach((input) => {
    input.addEventListener("change", () => {
      state.ornament = input.value;
      renderPreview();
    });
  });

  document.querySelectorAll(".bf-step").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".bf-step").forEach((candidate) => candidate.removeAttribute("aria-current"));
      button.setAttribute("aria-current", "step");
      byId(button.dataset.target)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });

  elements.previewMode.addEventListener("change", () => {
    const second = elements.spread.lastElementChild;
    const single = elements.previewMode.value === "single";
    second.hidden = single;
    elements.spread.style.gridTemplateColumns = single ? "1fr" : "1fr 1fr";
    elements.spread.style.width = single ? "min(58%, 430px)" : "min(100%, 880px)";
    elements.spread.style.minWidth = single ? "360px" : "600px";
  });

  byId("zoomIn").addEventListener("click", () => {
    state.zoom = core.clamp(state.zoom + 0.1, 0.7, 1.3);
    elements.spread.style.transform = `scale(${state.zoom})`;
    setText("zoomValue", `${Math.round(state.zoom * 100)}%`);
  });
  byId("zoomOut").addEventListener("click", () => {
    state.zoom = core.clamp(state.zoom - 0.1, 0.7, 1.3);
    elements.spread.style.transform = `scale(${state.zoom})`;
    setText("zoomValue", `${Math.round(state.zoom * 100)}%`);
  });

  [elements.blackPoint, elements.contrast, elements.saturation].forEach((input) => {
    input.addEventListener("input", () => {
      updateSliderLabels();
      scheduleImageRender();
    });
  });

  byId("draftBlurb").addEventListener("click", () => draftBlurb(true));
  byId("editBlurb").addEventListener("click", () => byId("blurbDialog").showModal());
  byId("applyBlurb").addEventListener("click", applyBlurbEditor);
  byId("simulatedGold").addEventListener("change", (event) => byId("coverWrapPreview").classList.toggle("simulated-gold", event.target.checked));
  byId("resetImage").addEventListener("click", resetImage);
  byId("downloadImage").addEventListener("click", exportAdjustedImage);
  byId("saveProject").addEventListener("click", saveProject);
  byId("exportPacket").addEventListener("click", exportPacket);
  byId("viewReport").addEventListener("click", showReport);
  byId("downloadReport").addEventListener("click", () => downloadText(`${slugify(elements.title.value)}-kdp-preflight.txt`, reportText()));
  byId("openFireGraph").addEventListener("click", openFireGraph);
  elements.fireCharacterFilter.addEventListener("change", renderFireGraph);
  elements.fireHeatFilter.addEventListener("input", renderFireGraph);
  byId("downloadFireGraph").addEventListener("click", () => downloadText(`${slugify(elements.title.value)}-story-fire-graph.json`, `${JSON.stringify(state.storyGraph, null, 2)}\n`, "application/json"));
  byId("downloadFireGraphSvg").addEventListener("click", exportFireGraphSvg);
  document.querySelectorAll("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => byId(button.dataset.closeDialog).close()));

  restoreProject();
  updateSliderLabels();
  applyBlurbToPreview();
  updateAll();
})();
