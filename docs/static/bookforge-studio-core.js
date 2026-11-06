(function (root) {
  "use strict";

  const TRIM_SIZES = Object.freeze({
    "5x8": [5, 8],
    "5.25x8": [5.25, 8],
    "5.5x8.5": [5.5, 8.5],
    "6x9": [6, 9],
    "6.14x9.21": [6.14, 9.21],
    "7x10": [7, 10],
    "8.25x11": [8.25, 11],
    "8.5x11": [8.5, 11],
  });

  const SPINE_PER_PAGE = Object.freeze({
    bw_cream: 0.0025,
    bw_white: 0.002252,
    color_standard: 0.002252,
    color_premium: 0.002347,
  });

  const STOP_WORDS = new Set(
    "a an and are as at be been but by for from had has have he her hers him his i if in into is it its me my no not of on or our she so than that the their them then there they this to too up was we were what when where which who will with would you your".split(
      " ",
    ),
  );

  const CHARACTER_STOP_NAMES = new Set(
    "A An And After Already Anybody Anywhere At Before Book But By Chapter Contents Copyright During Eight Eleven Elsewhere Epilogue Even Everybody Everyone Everywhere Five For Four From He Her Here Hers His How I I'd I'll I'm I've If In Into It Its Just Later Maybe Nine No Nobody Not Now Of Okay On One Only Part Perhaps Please Prologue Really Seven She Six So Someone Something Somewhere Still Ten That The Their Them Then There These They This Those Three Through To Twelve Two Under Until Very We Well What When Where Which While Who Why With Without Yes Yet You Your".split(
      " ",
    ),
  );

  const NON_CHARACTER_SUFFIXES = new Set("Bridge City Court Forest Gate Hall Lake Mountain Office Palace Peak Ridge River Road Sect Temple Tower Valley Village Wall Zong".split(" "));

  const HEAT_TERMS = Object.freeze({
    conflict: ["attack", "battle", "blade", "blood", "break", "burn", "clash", "danger", "death", "duel", "explode", "fight", "fire", "fist", "force", "hurt", "kill", "rage", "shatter", "spear", "strike", "sword", "threat", "war", "weapon", "wound"],
    revelation: ["discover", "learn", "realize", "reveal", "secret", "truth", "understand", "remember", "recognize", "finally"],
    choice: ["choose", "choice", "decide", "decision", "must", "promise", "refuse", "sacrifice", "swear", "will not"],
    bond: ["embrace", "friend", "forgive", "grief", "love", "mother", "father", "sister", "brother", "trust", "together"],
    crossing: ["arrive", "cross", "escape", "enter", "fall", "flee", "leave", "open", "return", "run", "wake"],
  });

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function normalizeInk(value) {
    const key = String(value || "bw").toLowerCase().replace(/\s+/g, "_");
    if (["black", "black_and_white", "b&w", "bw"].includes(key)) return "bw";
    if (["color", "standard", "standard_color", "color_standard"].includes(key)) return "color_standard";
    if (["premium", "premium_color", "color_premium"].includes(key)) return "color_premium";
    return key;
  }

  function printKey(ink, paper) {
    const normalized = normalizeInk(ink);
    if (normalized === "bw") return paper === "white" ? "bw_white" : "bw_cream";
    return normalized;
  }

  function calculatePrintSpec(options) {
    const trimKey = options.trim || "5x8";
    const trim = TRIM_SIZES[trimKey];
    if (!trim) throw new Error(`Unknown trim size: ${trimKey}`);

    const binding = options.binding || "paperback";
    const ink = normalizeInk(options.ink);
    const paper = options.paper || (ink === "bw" ? "cream" : "white");
    const pages = Math.max(0, Number.parseInt(options.pageCount || 0, 10));
    const factor = SPINE_PER_PAGE[printKey(ink, paper)] || SPINE_PER_PAGE.bw_cream;
    const spineIn = pages * factor;
    const warnings = [];
    const errors = [];

    if (binding === "ebook") {
      return {
        binding,
        trimKey,
        trimWidthIn: trim[0],
        trimHeightIn: trim[1],
        pageCount: pages,
        ink,
        paper,
        spineIn: 0,
        coverWidthIn: null,
        coverHeightIn: null,
        spineTextAllowed: false,
        templateRequired: false,
        warnings: ["Kindle eBooks use a front-only RGB cover image, not a print wrap."],
        errors,
      };
    }

    if (binding === "hardcover") {
      if (!["5.5x8.5", "6x9", "6.14x9.21", "7x10", "8.25x11"].includes(trimKey)) {
        errors.push("That trim size is not in KDP's hardcover trim list.");
      }
      if (ink === "color_standard") errors.push("KDP does not offer standard color for hardcover.");
      if (pages && (pages < 75 || pages > 550)) errors.push("KDP hardcover page count must be 75–550 pages.");
      warnings.push("Hardcover case laminate uses 0.51 in wrap and 0.4 in hinges. Import KDP's exact template before final export.");
      return {
        binding,
        trimKey,
        trimWidthIn: trim[0],
        trimHeightIn: trim[1],
        pageCount: pages,
        ink,
        paper,
        spineIn,
        coverWidthIn: null,
        coverHeightIn: null,
        spineTextAllowed: pages >= 80,
        templateRequired: true,
        warnings,
        errors,
      };
    }

    const minimum = ink === "color_standard" ? 72 : 24;
    if (pages && pages < minimum) errors.push(`This paperback print option needs at least ${minimum} pages.`);
    if (pages % 2 === 1) warnings.push("KDP rounds an odd print page count up to the next even number for cover sizing.");
    if (pages > 828) warnings.push("Check KDP's trim-specific maximum page count before export.");
    const bleed = 0.125;
    return {
      binding,
      trimKey,
      trimWidthIn: trim[0],
      trimHeightIn: trim[1],
      pageCount: pages,
      ink,
      paper,
      spineIn,
      coverWidthIn: trim[0] * 2 + spineIn + bleed * 2,
      coverHeightIn: trim[1] + bleed * 2,
      spineTextAllowed: pages >= 80,
      templateRequired: false,
      warnings,
      errors,
    };
  }

  function meaningfulParagraphs(text) {
    return String(text || "")
      .replace(/```[\s\S]*?```/g, " ")
      .split(/\n\s*\n/)
      .map((paragraph) =>
        paragraph
          .replace(/^#{1,6}\s+/gm, "")
          .replace(/^[-*>]\s+/gm, "")
          .replace(/[*_`]/g, "")
          .replace(/\s+/g, " ")
          .trim(),
      )
      .filter((paragraph) => paragraph.length >= 45);
  }

  function sentenceList(text) {
    return meaningfulParagraphs(text)
      .join(" ")
      .match(/[^.!?]+[.!?]+|[^.!?]+$/g)?.map((sentence) => sentence.trim())
      .filter((sentence) => sentence.length >= 35 && sentence.length <= 280) || [];
  }

  function titleFromText(text, fallback) {
    const h1 = String(text || "").match(/^#\s+(.+)$/m);
    return (h1 && h1[1].trim()) || fallback || "Untitled book";
  }

  function topTerms(text, limit) {
    const counts = new Map();
    const words = String(text || "").toLowerCase().match(/[a-z][a-z'-]{3,}/g) || [];
    for (const word of words) {
      if (STOP_WORDS.has(word) || /^(chapter|copyright|contents)$/.test(word)) continue;
      counts.set(word, (counts.get(word) || 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, limit || 8)
      .map(([term, count]) => ({ term, count }));
  }

  function analyzeManuscript(text) {
    const source = String(text || "");
    const words = source.match(/[\p{L}\p{N}][\p{L}\p{N}'’_-]*/gu) || [];
    const headings = source.match(/^#{1,3}\s+.+$/gm) || [];
    const h2Chapters = source.match(/^##\s+.+$/gm) || [];
    const namedChapters = source.match(/^#{1,3}\s+(?:chapter|prologue|epilogue)\b.+$/gim) || [];
    const chapters = h2Chapters.length ? h2Chapters : namedChapters;
    const paragraphs = meaningfulParagraphs(source);
    const estimatedPages = words.length ? Math.max(1, Math.ceil(words.length / 275)) : 0;
    return {
      title: titleFromText(source),
      wordCount: words.length,
      characterCount: source.length,
      headingCount: headings.length,
      chapterCount: chapters.length,
      paragraphCount: paragraphs.length,
      estimatedPages,
      readingMinutes: Math.ceil(words.length / 230),
      terms: topTerms(source, 8),
      excerpt: paragraphs.slice(0, 4).join("\n\n"),
    };
  }

  function stripStoryMarkup(text) {
    return String(text || "")
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/^#{1,6}\s+.*$/gm, " ")
      .replace(/^\s*---+\s*$/gm, " ")
      .replace(/^\s*[-*>]\s+/gm, "")
      .replace(/[*_`~]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function splitStoryChapters(text) {
    const source = String(text || "");
    const headings = [...source.matchAll(/^##\s+(.+)$/gm)];
    const selected = headings.length ? headings : [...source.matchAll(/^#{1,3}\s+((?:chapter|prologue|epilogue)\b.+)$/gim)];
    if (!selected.length) {
      const content = stripStoryMarkup(source);
      return content ? [{ id: "ch-1", index: 1, title: titleFromText(source, "Manuscript"), content }] : [];
    }
    return selected.map((match, position) => {
      const start = match.index + match[0].length;
      const end = position + 1 < selected.length ? selected[position + 1].index : source.length;
      return {
        id: `ch-${position + 1}`,
        index: position + 1,
        title: match[1].replace(/[*_`]/g, "").trim(),
        content: stripStoryMarkup(source.slice(start, end)),
      };
    });
  }

  function sentenceParts(text) {
    return String(text || "")
      .match(/[^.!?]+[.!?]+|[^.!?]+$/g)?.map((sentence) => sentence.replace(/\s+/g, " ").trim())
      .filter((sentence) => sentence.length >= 24) || [];
  }

  function heatBreakdown(text) {
    const source = String(text || "");
    const lower = source.toLowerCase();
    const signals = {};
    let score = 8;
    for (const [type, terms] of Object.entries(HEAT_TERMS)) {
      const matches = terms.filter((term) => new RegExp(`\\b${term.replace(/\s+/g, "\\s+")}\\b`, "i").test(lower)).length;
      signals[type] = matches;
      score += matches * (type === "conflict" ? 10 : 6);
    }
    score += Math.min(10, (source.match(/!/g) || []).length * 4);
    score += Math.min(6, (source.match(/\?/g) || []).length * 2);
    score += Math.min(6, (source.match(/[“”"]/g) || []).length);
    const dominant = Object.entries(signals).sort((a, b) => b[1] - a[1])[0];
    return {
      heat: Math.round(clamp(10 + (score - 8) * 3.3, 5, 100)),
      type: dominant && dominant[1] ? dominant[0] : "character",
      signals,
    };
  }

  function characterCandidates(chapters, title) {
    const titleWords = new Set(String(title || "").split(/\s+/).map((word) => word.replace(/[^\p{L}'’-]/gu, "")).filter(Boolean));
    const records = new Map();
    const pattern = /\b[\p{Lu}][\p{L}'’.-]*(?:\s+[\p{Lu}][\p{L}'’.-]*){0,2}\b/gu;
    for (const chapter of chapters) {
      const chapterSeen = new Set();
      for (const match of chapter.content.matchAll(pattern)) {
        const name = match[0].replace(/['’]s$/u, "").replace(/[.’]$/, "").trim();
        const words = name.split(/\s+/);
        if (!name || words.some((word) => CHARACTER_STOP_NAMES.has(word)) || NON_CHARACTER_SUFFIXES.has(words[words.length - 1]) || words.every((word) => titleWords.has(word))) continue;
        if (name.length < 3 || /^\d/.test(name) || words.length > 3) continue;
        const record = records.get(name) || { name, mentions: 0, chapterIds: new Set() };
        record.mentions += 1;
        record.chapterIds.add(chapter.id);
        records.set(name, record);
        chapterSeen.add(name);
      }
    }
    return [...records.values()]
      .filter((record) => (record.name.includes(" ") ? record.mentions >= 2 : record.mentions >= 4) && record.chapterIds.size >= 2)
      .sort((a, b) => b.chapterIds.size - a.chapterIds.size || b.mentions - a.mentions || a.name.localeCompare(b.name));
  }

  function analyzeStoryGraph(text, options) {
    const settings = options || {};
    const maxCharacters = clamp(Number(settings.maxCharacters) || 10, 3, 18);
    const maxMomentsPerChapter = clamp(Number(settings.maxMomentsPerChapter) || 4, 1, 8);
    const title = titleFromText(text);
    const sourceChapters = splitStoryChapters(text);
    const candidates = characterCandidates(sourceChapters, title).slice(0, maxCharacters);
    const characters = candidates.map((record, index) => ({
      id: `char-${index + 1}`,
      name: record.name,
      mentions: record.mentions,
      appearances: record.chapterIds.size,
      chapterIds: [...record.chapterIds],
      momentCount: 0,
    }));
    const characterByName = new Map(characters.map((character) => [character.name, character]));
    const moments = [];
    const chapters = sourceChapters.map((chapter) => {
      const sentences = sentenceParts(chapter.content);
      const sentenceHeat = sentences.map((sentence) => ({ sentence, ...heatBreakdown(sentence) }));
      const chapterCharacters = characters.filter((character) => new RegExp(`\\b${character.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "u").test(chapter.content));
      const candidatesForChapter = [];
      for (const item of sentenceHeat) {
        for (const character of chapterCharacters) {
          const exact = new RegExp(`\\b${character.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "u");
          if (!exact.test(item.sentence)) continue;
          candidatesForChapter.push({ character, ...item });
        }
      }
      candidatesForChapter
        .sort((a, b) => b.heat - a.heat || a.sentence.localeCompare(b.sentence))
        .slice(0, maxMomentsPerChapter)
        .forEach((item) => {
          const moment = {
            id: `moment-${moments.length + 1}`,
            chapterId: chapter.id,
            chapterIndex: chapter.index,
            characterId: item.character.id,
            character: item.character.name,
            text: item.sentence.length > 240 ? `${item.sentence.slice(0, 237).trim()}…` : item.sentence,
            heat: item.heat,
            type: item.type,
          };
          moments.push(moment);
          characterByName.get(item.character.name).momentCount += 1;
        });
      const hottest = sentenceHeat.sort((a, b) => b.heat - a.heat).slice(0, 5);
      const heat = hottest.length ? Math.round(hottest.reduce((sum, item) => sum + item.heat, 0) / hottest.length) : 5;
      return {
        id: chapter.id,
        index: chapter.index,
        title: chapter.title,
        wordCount: (chapter.content.match(/[\p{L}\p{N}][\p{L}\p{N}'’_-]*/gu) || []).length,
        heat,
        characters: chapterCharacters.map((character) => character.name),
        excerpt: sentences[0] || chapter.content.slice(0, 240),
      };
    });
    return {
      schema: "aethermoore.story-fire-graph.v1",
      title,
      generatedBy: "Deterministic local heuristic; author review required.",
      chapters,
      characters: characters.filter((character) => character.momentCount > 0),
      moments,
      stats: {
        chapterCount: chapters.length,
        characterCount: characters.filter((character) => character.momentCount > 0).length,
        momentCount: moments.length,
        hottestChapterId: [...chapters].sort((a, b) => b.heat - a.heat)[0]?.id || null,
      },
    };
  }

  function draftBlurb(options) {
    const text = String(options.text || "");
    const title = options.title || titleFromText(text);
    const sentences = sentenceList(text);
    const terms = topTerms(text, 5).map((item) => item.term);
    const hook = sentences[0] || `${title} begins with a pressure its characters can no longer avoid.`;
    const body = [];
    if (sentences[1]) body.push(sentences[1]);
    if (sentences[2]) body.push(sentences[2]);
    if (!body.length) body.push(`A story shaped by ${terms.slice(0, 3).join(", ") || "choice, consequence, and change"}.`);
    const close = terms.length
      ? `What follows is a story of ${terms.slice(0, 3).join(", ")}—and the cost of crossing what once held.`
      : "What follows is a story about the cost of crossing what once held.";
    return {
      hook,
      paragraphs: [body.join(" "), close],
      short: [hook, body[0]].filter(Boolean).join(" "),
      keywords: terms,
      provenance: "Drafted locally from opening manuscript sentences and repeated terms; author review required.",
    };
  }

  function coverBrief(options) {
    const analysis = analyzeManuscript(options.text || "");
    const title = options.title || analysis.title;
    const genre = options.genre || "fiction";
    const motifs = analysis.terms.slice(0, 5).map((item) => item.term);
    return {
      title,
      genre,
      motifs,
      prompt: `Portrait cover art for ${title}, ${genre}. Build one clear protagonist or symbolic focal point from: ${motifs.join(", ") || "the manuscript's central setting and conflict"}. Leave the upper third calm for typography. Strong silhouette and thumbnail readability. No text, logo, barcode, or watermark.`,
      avoid: "No generated typography, fake author name, watermark, floating-face collage, or visual element absent from the manuscript.",
    };
  }

  function analyzePixels(pixelData) {
    const data = pixelData && pixelData.data ? pixelData.data : pixelData;
    if (!data || !data.length) return { averageLuminance: 0, shadowClipPct: 0, highlightClipPct: 0, averageSaturation: 0 };
    let pixels = 0;
    let luminance = 0;
    let shadow = 0;
    let highlight = 0;
    let saturation = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i + 3] === 0) continue;
      const r = data[i] / 255;
      const g = data[i + 1] / 255;
      const b = data[i + 2] / 255;
      const y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const max = Math.max(r, g, b);
      const min = Math.min(r, g, b);
      luminance += y;
      saturation += max === 0 ? 0 : (max - min) / max;
      if (y <= 8 / 255) shadow += 1;
      if (y >= 247 / 255) highlight += 1;
      pixels += 1;
    }
    if (!pixels) return { averageLuminance: 0, shadowClipPct: 0, highlightClipPct: 0, averageSaturation: 0 };
    return {
      averageLuminance: luminance / pixels,
      shadowClipPct: (shadow / pixels) * 100,
      highlightClipPct: (highlight / pixels) * 100,
      averageSaturation: saturation / pixels,
    };
  }

  function effectiveDpi(pixelWidth, pixelHeight, printWidthIn, printHeightIn) {
    if (!printWidthIn || !printHeightIn) return 0;
    return Math.min(pixelWidth / printWidthIn, pixelHeight / printHeightIn);
  }

  function buildProfile(options) {
    const title = options.title || "Untitled book";
    const ink = normalizeInk(options.ink);
    const profile = {
      title,
      subtitle: options.subtitle || "",
      author: options.author || "",
      copyright_year: Number(options.copyrightYear) || new Date().getFullYear(),
      publisher: options.publisher || options.author || "",
      source: options.source || "manuscript.md",
      output_dir: "build/bookforge",
      binding: options.binding || "paperback",
      trim: options.trim || "5x8",
      page_count: Number(options.pageCount) || null,
      print: {
        paper: ink === "bw" ? options.paper || "cream" : "white",
        ink,
        cover_finish: options.coverFinish || "matte",
      },
      interior_engine: options.ornament && options.ornament !== "none" ? "reportlab" : "auto",
      ornament: {
        style: options.ornament || "none",
        color: options.ornamentColor || "#2a7180",
        opacity: 0.22,
      },
      cover: {
        art: options.coverArtName || "",
        simulated_gold: Boolean(options.simulatedGold),
        note: options.simulatedGold ? "Printed process-color simulation only; not foil or metallic ink." : "",
      },
      hook: options.hook || "",
      blurb_paragraphs: options.blurbParagraphs || [],
      author_bio: options.authorBio || "",
    };
    return profile;
  }

  function preflight(options) {
    const spec = calculatePrintSpec(options);
    const checks = [];
    const add = (id, label, status, detail) => checks.push({ id, label, status, detail });
    const dpi = Number(options.dpi || 0);
    add("manuscript", "Manuscript imported", options.wordCount > 0 ? "pass" : "warn", options.wordCount ? `${options.wordCount.toLocaleString()} words` : "Import a .md or .txt file");
    add("pages", "Page count", spec.errors.length ? "fail" : spec.pageCount ? "pass" : "warn", spec.errors[0] || (spec.pageCount ? `${spec.pageCount} pages` : "Use final interior page count"));
    add("dpi", "Cover resolution", dpi >= 300 ? "pass" : dpi ? "fail" : "warn", dpi ? `${Math.round(dpi)} DPI at intended size` : "Import cover art to measure");
    add("spine", "Spine text", spec.spineTextAllowed ? "pass" : "warn", spec.spineTextAllowed ? "Allowed; verify safe area" : "Disabled below 80 pages");
    add(
      "template",
      "Cover dimensions",
      spec.binding === "ebook" ? "pass" : spec.templateRequired ? "manual" : "pass",
      spec.binding === "ebook"
        ? "Front-only image; 1600 × 2560 px recommended"
        : spec.templateRequired
          ? "Import exact KDP hardcover template"
          : `${spec.coverWidthIn.toFixed(3)} × ${spec.coverHeightIn.toFixed(3)} in`,
    );
    add("fonts", "Embedded fonts", "manual", "Check the exported PDF");
    add("previewer", "KDP Print Previewer", "manual", "Still required before publishing");
    return { spec, checks };
  }

  const api = {
    TRIM_SIZES,
    SPINE_PER_PAGE,
    clamp,
    normalizeInk,
    calculatePrintSpec,
    analyzeManuscript,
    analyzeStoryGraph,
    draftBlurb,
    coverBrief,
    analyzePixels,
    effectiveDpi,
    buildProfile,
    preflight,
  };

  root.BookforgeStudioCore = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
