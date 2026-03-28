(() => {
  "use strict";

  const DATA_ROOT = "./sphere-grid";
  const MANIFEST_URL = `${DATA_ROOT}/sphere_manifest.json`;
  const SKILL_INDEX_URL = `${DATA_ROOT}/codex_skill_sphere_index.public.json`;

  const TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"];
  const TONGUE_COLORS = {
    KO: "#ffd36e",
    AV: "#6dd8ff",
    RU: "#ff6bd6",
    CA: "#7cf3db",
    UM: "#8fffd3",
    DR: "#9160ff",
  };
  const TONGUE_NAMES = {
    KO: "Command",
    AV: "Transport",
    RU: "Entropy",
    CA: "Compute",
    UM: "Security",
    DR: "Structure",
  };

  const canvas = document.getElementById("grid");
  const ctx = canvas.getContext("2d", { alpha: true });

  const searchEl = document.getElementById("search");
  const legendEl = document.getElementById("legend");
  const resetBtn = document.getElementById("resetView");

  const panelEl = document.getElementById("panel");
  const panelTitleEl = document.getElementById("panelTitle");
  const panelMetaEl = document.getElementById("panelMeta");
  const panelBodyEl = document.getElementById("panelBody");
  const closePanelBtn = document.getElementById("closePanel");

  const state = {
    spheres: [],
    skills: [],
    skillsBySphere: new Map(),
    nodes: [],
    filterTongue: null,
    search: "",
    hoverId: null,
  };

  const lastMouse = { x: -9999, y: -9999 };
  let dragging = false;
  let dragStart = { x: 0, y: 0, yaw: 0, pitch: 0 };

  const camera = {
    yaw: 0.6,
    pitch: 0.22,
    dist: 11.5,
    tyaw: 0.6,
    tpitch: 0.22,
    tdist: 11.5,
  };

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function stripFrontmatter(md) {
    return md.replace(/^---\\s*\\n[\\s\\S]*?\\n---\\s*\\n/, "");
  }

  function preprocessWikiLinks(md) {
    return md
      .replace(/\\[\\[([^\\]|]+)\\|([^\\]]+)\\]\\]/g, (_, target, label) => `[${label}](wikilink:${target})`)
      .replace(/\\[\\[([^\\]]+)\\]\\]/g, (_, target) => `[${target}](wikilink:${target})`);
  }

  function resolveWikiTarget(target) {
    let t = String(target || "").trim();
    if (!t) return null;
    t = t.replace(/^\\.\\//, "");
    if (!t.endsWith(".md")) t = `${t}.md`;
    return t;
  }

  function renderInline(text) {
    let s = escapeHtml(text);
    s = s.replace(/`([^`]+)`/g, (_, code) => `<code>${escapeHtml(code)}</code>`);
    s = s.replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>");
    s = s.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, (_, label, href) => {
      const raw = String(href || "").trim();
      if (raw.startsWith("wikilink:")) {
        const target = raw.slice("wikilink:".length);
        return `<a href=\"#\" data-wiki=\"${escapeHtml(target)}\">${escapeHtml(label)}</a>`;
      }
      return `<a href=\"${escapeHtml(raw)}\" target=\"_blank\" rel=\"noreferrer\">${escapeHtml(label)}</a>`;
    });
    return s;
  }

  function renderMarkdown(md) {
    const src = preprocessWikiLinks(stripFrontmatter(md));
    const lines = src.split(/\\r?\\n/);
    let i = 0;
    const out = [];
    const para = [];

    function flushPara() {
      const text = para.join(" ").trim();
      para.length = 0;
      if (text) out.push(`<p>${renderInline(text)}</p>`);
    }

    function parseTable(start) {
      const rows = [];
      let j = start;
      while (j < lines.length) {
        const line = lines[j].trim();
        if (!line.startsWith("|") || !line.includes("|")) break;
        rows.push(line);
        j++;
      }
      if (rows.length < 2) return null;
      if (!rows[1].includes("---")) return null;
      const header = rows[0].split("|").map((x) => x.trim()).filter(Boolean);
      const bodyRows = rows.slice(2).map((r) => r.split("|").map((x) => x.trim()).filter(Boolean));
      const th = header.map((h) => `<th>${renderInline(h)}</th>`).join("");
      const trs = bodyRows
        .map((cols) => `<tr>${cols.map((c) => `<td>${renderInline(c)}</td>`).join("")}</tr>`)
        .join("");
      return { html: `<table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table>`, end: j };
    }

    while (i < lines.length) {
      const raw = lines[i];
      const line = raw.trimEnd();

      if (line.startsWith("```")) {
        flushPara();
        const fence = line.slice(3).trim();
        const code = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith("```")) {
          code.push(lines[i]);
          i++;
        }
        out.push(`<pre><code data-lang=\"${escapeHtml(fence)}\">${escapeHtml(code.join(\"\\n\"))}</code></pre>`);
        i++;
        continue;
      }

      if (line.trim().startsWith("|") && line.includes("|")) {
        const t = parseTable(i);
        if (t) {
          flushPara();
          out.push(t.html);
          i = t.end;
          continue;
        }
      }

      const hm = line.match(/^(#{1,3})\\s+(.*)$/);
      if (hm) {
        flushPara();
        const level = hm[1].length;
        out.push(`<h${level}>${renderInline(hm[2].trim())}</h${level}>`);
        i++;
        continue;
      }

      if (line.startsWith(">")) {
        flushPara();
        out.push(`<blockquote>${renderInline(line.replace(/^>\\s?/, \"\"))}</blockquote>`);
        i++;
        continue;
      }

      if (/^[-*]\\s+/.test(line)) {
        flushPara();
        const items = [];
        while (i < lines.length && /^[-*]\\s+/.test(lines[i].trim())) {
          items.push(`<li>${renderInline(lines[i].trim().replace(/^[-*]\\s+/, \"\"))}</li>`);
          i++;
        }
        out.push(`<ul>${items.join(\"\")}</ul>`);
        continue;
      }

      if (!line.trim()) {
        flushPara();
        i++;
        continue;
      }

      para.push(line.trim());
      i++;
    }
    flushPara();
    return out.join("");
  }

  function buildLegend() {
    legendEl.innerHTML = "";
    for (const t of TONGUE_ORDER) {
      const el = document.createElement("div");
      el.className = "tag";
      el.textContent = `${t} • ${TONGUE_NAMES[t]}`;
      el.addEventListener("click", () => {
        state.filterTongue = state.filterTongue === t ? null : t;
      });
      legendEl.appendChild(el);
    }
  }

  function buildSkillsBySphere(items) {
    const m = new Map();
    for (const it of items) {
      const p = it.primary || {};
      const link = p.sphere_link;
      if (!link) continue;
      if (!m.has(link)) m.set(link, []);
      m.get(link).push(it);
    }
    for (const [k, v] of m.entries()) {
      v.sort((a, b) => String(a.skill).localeCompare(String(b.skill)));
      m.set(k, v);
    }
    return m;
  }

  function hashToAngle(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    const u = (h >>> 0) / 4294967295;
    return u * Math.PI * 2;
  }

  function rotY(x, z, a) {
    const c = Math.cos(a);
    const s = Math.sin(a);
    return { x: x * c - z * s, z: x * s + z * c };
  }
  function rotX(y, z, a) {
    const c = Math.cos(a);
    const s = Math.sin(a);
    return { y: y * c - z * s, z: y * s + z * c };
  }

  function project(p) {
    let x = p.x;
    let y = p.y;
    let z = p.z;
    ({ x, z } = rotY(x, z, camera.yaw));
    ({ y, z } = rotX(y, z, camera.pitch));
    z += camera.dist;

    const fov = 740;
    const scale = fov / (fov + z * 120);
    const cx = canvas.clientWidth / 2;
    const cy = canvas.clientHeight / 2;
    return {
      sx: cx + x * scale * 120,
      sy: cy + y * scale * 120,
      scale,
      z,
    };
  }

  function visibleNode(n) {
    if (state.filterTongue && n.tongue !== state.filterTongue) return false;
    if (!state.search) return true;
    const q = state.search.toLowerCase();
    if (n.kind === "sphere") {
      if (String(n.name).toLowerCase().includes(q)) return true;
      for (const it of n.skills || []) {
        const name = String(it.skill || "").toLowerCase();
        const desc = String(it.description || "").toLowerCase();
        if (name.includes(q) || desc.includes(q)) return true;
      }
      return false;
    }
    if (n.kind === "tongue") {
      return String(n.tongue).toLowerCase().includes(q) || String(TONGUE_NAMES[n.tongue]).toLowerCase().includes(q);
    }
    return true;
  }

  function buildNodes() {
    state.nodes = [];
    const tongueCenters = new Map();
    const ringR = 3.35;

    for (let i = 0; i < TONGUE_ORDER.length; i++) {
      const tongue = TONGUE_ORDER[i];
      const a = (i / TONGUE_ORDER.length) * Math.PI * 2;
      const x = Math.cos(a) * ringR;
      const y = Math.sin(a) * ringR;
      const z = (i - 2.5) * 0.22;
      const id = `tongue:${tongue}`;
      const n = {
        id,
        kind: "tongue",
        tongue,
        label: `${tongue} • ${TONGUE_NAMES[tongue]}`,
        x,
        y,
        z,
        r: 18,
        color: TONGUE_COLORS[tongue],
      };
      tongueCenters.set(tongue, n);
      state.nodes.push(n);
    }

    for (const s of state.spheres) {
      const center = tongueCenters.get(s.tongue);
      if (!center) continue;
      const tier = Number(s.tier || 1);
      const a = hashToAngle(`${s.rel_link}:${s.name}`);
      const tierR = 0.55 + (tier - 1) * 0.58;
      const x = center.x + Math.cos(a) * tierR;
      const y = center.y + Math.sin(a) * tierR;
      const z = center.z + (tier - 2.5) * 0.18;
      const link = s.rel_link;
      const skills = state.skillsBySphere.get(link) || [];
      state.nodes.push({
        id: `sphere:${link}`,
        kind: "sphere",
        tongue: s.tongue,
        tier,
        name: s.name,
        label: `${s.tongue} T${tier} • ${s.name}`,
        x,
        y,
        z,
        r: 10 + tier * 2.2,
        color: TONGUE_COLORS[s.tongue] || "#fff",
        rel_md: s.rel_md,
        rel_link: s.rel_link,
        skills,
      });
    }
  }

  async function fetchText(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    return await res.text();
  }

  function buildInvocationPrompt(skillName, skillMarkdown, userTaskPlaceholder) {
    return [
      "SYSTEM: You are an operator model. You must follow the SKILL playbook below. If you are missing info, ask ONE question at a time. Do not hallucinate tools/results.",
      "",
      `SKILL: ${skillName}`,
      "",
      "=== SKILL.md ===",
      skillMarkdown.trim(),
      "=== END SKILL.md ===",
      "",
      "USER TASK:",
      userTaskPlaceholder || "<paste the task here>",
      "",
      "OUTPUT:",
      "1. First: restate the task in one sentence.",
      "2. Then: the smallest safe plan (numbered).",
      "3. Then: execute what you can. If blocked, ask the next required question.",
      "",
    ].join("\\n");
  }

  async function openSkill(it) {
    const name = String(it.skill || it.skill_dir || "Skill");
    const doc = String(it.skill_doc || "");
    if (!doc) return;
    panelTitleEl.textContent = name;
    panelMetaEl.textContent = "Codex skill playbook (SKILL.md).";
    panelBodyEl.innerHTML = "<p>Loading…</p>";
    panelEl.classList.add("open");
    try {
      const md = await fetchText(`${DATA_ROOT}/${doc}`);
      const html = renderMarkdown(md);
      const prompt = buildInvocationPrompt(name, md, "");
      panelBodyEl.innerHTML = `
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px;">
          <button type="button" class="closeBtn" id="copyPromptBtn" title="Copy a ready-to-run prompt for Llama (Ollama) or Hugging Face">Copy agent prompt</button>
          <a class="closeBtn" href="${DATA_ROOT}/${doc}" target="_blank" rel="noreferrer">Open raw SKILL.md</a>
        </div>
        ${html}
      `;
      const btn = panelBodyEl.querySelector("#copyPromptBtn");
      if (btn) {
        btn.addEventListener("click", async () => {
          try {
            await navigator.clipboard.writeText(prompt);
            panelMetaEl.textContent = "Prompt copied. Paste into Ollama (Llama) or Hugging Face chat.";
          } catch {
            panelMetaEl.textContent = "Copy failed. Select and copy manually from the raw SKILL.md link.";
          }
        });
      }
      panelBodyEl.querySelectorAll("a[data-wiki]").forEach((a) => {
        a.addEventListener("click", async (e) => {
          e.preventDefault();
          const target = a.getAttribute("data-wiki");
          const rel = resolveWikiTarget(target);
          if (!rel) return;
          await openDoc(rel, String(target), "Wiki link");
          history.replaceState(null, "", `#doc=${encodeURIComponent(target)}`);
        });
      });
    } catch (err) {
      panelBodyEl.innerHTML = `<p>Failed to load skill: <code>${escapeHtml(String(err))}</code></p>`;
    }
  }

  async function openDoc(relMdPath, title, meta) {
    panelTitleEl.textContent = title || "Document";
    panelMetaEl.textContent = meta || "";
    panelBodyEl.innerHTML = "<p>Loading…</p>";
    panelEl.classList.add("open");
    try {
      const md = await fetchText(`${DATA_ROOT}/${relMdPath}`);
      panelBodyEl.innerHTML = renderMarkdown(md);
      panelBodyEl.querySelectorAll("a[data-wiki]").forEach((a) => {
        a.addEventListener("click", async (e) => {
          e.preventDefault();
          const target = a.getAttribute("data-wiki");
          const rel = resolveWikiTarget(target);
          if (!rel) return;
          await openDoc(rel, String(target), "Wiki link");
          history.replaceState(null, "", `#doc=${encodeURIComponent(target)}`);
        });
      });
    } catch (err) {
      panelBodyEl.innerHTML = `<p>Failed to load doc: <code>${escapeHtml(String(err))}</code></p>`;
    }
  }

  async function openSphere(n) {
    const skills = n.skills || [];
    const title = `${n.tongue} T${n.tier} • ${n.name}`;
    const meta = `${skills.length} mapped skill${skills.length === 1 ? "" : "s"} here.`;
    panelTitleEl.textContent = title;
    panelMetaEl.textContent = meta;
    panelBodyEl.innerHTML = "<p>Loading…</p>";
    panelEl.classList.add("open");

    const listHtml = skills.length
      ? `<h3>Mapped skills</h3><ul>${skills
          .map((it) => {
            const skill = escapeHtml(it.skill || "");
            const desc = escapeHtml(it.description || "");
            return `<li><a href=\"#\" data-skill=\"${escapeHtml(it.skill || "")}\"><strong>${skill}</strong></a><br><span style=\"color:#aab0d6; font-size:12px;\">${desc}</span></li>`;
          })
          .join("")}</ul>`
      : `<p>No skills mapped to this sphere yet.</p>`;

    try {
      const md = await fetchText(`${DATA_ROOT}/${n.rel_md}`);
      panelBodyEl.innerHTML = `${listHtml}<div style=\"height:12px\"></div>${renderMarkdown(md)}`;
      panelBodyEl.querySelectorAll("a[data-skill]").forEach((a) => {
        a.addEventListener("click", (e) => {
          e.preventDefault();
          const name = a.getAttribute("data-skill");
          const it = state.skills.find((s) => String(s.skill) === String(name));
          if (it) openSkill(it);
        });
      });
      panelBodyEl.querySelectorAll("a[data-wiki]").forEach((a) => {
        a.addEventListener("click", async (e) => {
          e.preventDefault();
          const target = a.getAttribute("data-wiki");
          const rel = resolveWikiTarget(target);
          if (!rel) return;
          await openDoc(rel, String(target), "Wiki link");
          history.replaceState(null, "", `#doc=${encodeURIComponent(target)}`);
        });
      });
      history.replaceState(null, "", `#sphere=${encodeURIComponent(n.rel_link)}`);
    } catch (err) {
      panelBodyEl.innerHTML = `${listHtml}<p>Failed to load sphere doc: <code>${escapeHtml(String(err))}</code></p>`;
    }
  }

  function nodeById(id) {
    return state.nodes.find((n) => n.id === id) || null;
  }

  function focusOnNode(id) {
    const n = nodeById(id);
    if (!n) return;
    camera.tdist = clamp(camera.tdist * 0.78, 4.2, 22);
  }

  function resize() {
    const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    canvas.width = Math.floor(canvas.clientWidth * dpr);
    canvas.height = Math.floor(canvas.clientHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function draw() {
    camera.yaw += (camera.tyaw - camera.yaw) * 0.12;
    camera.pitch += (camera.tpitch - camera.pitch) * 0.12;
    camera.dist += (camera.tdist - camera.dist) * 0.1;

    ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);

    // star noise
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.fillStyle = "rgba(255,255,255,0.05)";
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    for (let i = 0; i < 120; i++) {
      const x = (Math.sin(i * 999.1) * 0.5 + 0.5) * w;
      const y = (Math.sin(i * 1337.7) * 0.5 + 0.5) * h;
      ctx.fillRect(x, y, 1, 1);
    }
    ctx.restore();

    const projected = [];
    for (const n of state.nodes) {
      if (!visibleNode(n)) continue;
      projected.push({ n, p: project(n) });
    }
    projected.sort((a, b) => a.p.z - b.p.z);

    // connections
    ctx.save();
    ctx.lineWidth = 1;
    for (const it of projected) {
      const n = it.n;
      if (n.kind !== "sphere") continue;
      const tongueNode = state.nodes.find((t) => t.kind === "tongue" && t.tongue === n.tongue);
      if (!tongueNode) continue;
      const a = project(tongueNode);
      const b = it.p;
      ctx.strokeStyle = "rgba(123,140,255,0.10)";
      ctx.beginPath();
      ctx.moveTo(a.sx, a.sy);
      ctx.lineTo(b.sx, b.sy);
      ctx.stroke();
    }
    ctx.restore();

    state.hoverId = null;
    const mx = lastMouse.x;
    const my = lastMouse.y;

    for (let i = projected.length - 1; i >= 0; i--) {
      const { n, p } = projected[i];
      const r = (n.r || 10) * (0.65 + p.scale * 1.1);
      const dx = mx - p.sx;
      const dy = my - p.sy;
      const hit = dx * dx + dy * dy <= r * r;
      if (hit && !state.hoverId) state.hoverId = n.id;

      // glow
      ctx.save();
      ctx.globalAlpha = 0.95;
      const g = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, r * 2.4);
      const c = n.color || "#fff";
      g.addColorStop(0, `${c}66`);
      g.addColorStop(0.35, `${c}22`);
      g.addColorStop(1, "transparent");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(p.sx, p.sy, r * 2.4, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // core
      ctx.save();
      ctx.fillStyle = c;
      ctx.globalAlpha = n.kind === "tongue" ? 0.92 : 0.85;
      ctx.beginPath();
      ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // labels
      const showLabel = n.kind === "tongue" || state.hoverId === n.id;
      if (showLabel) {
        ctx.save();
        ctx.font = n.kind === "tongue" ? "700 12px ui-sans-serif, system-ui" : "600 12px ui-sans-serif, system-ui";
        ctx.fillStyle = "rgba(237,240,255,0.92)";
        ctx.shadowColor = "rgba(0,0,0,0.45)";
        ctx.shadowBlur = 14;
        ctx.fillText(n.label, p.sx + r + 10, p.sy + 4);
        if (n.kind === "sphere") {
          const k = (n.skills || []).length;
          ctx.font = "500 11px ui-sans-serif, system-ui";
          ctx.fillStyle = "rgba(180,185,223,0.92)";
          ctx.fillText(`${k} skill${k === 1 ? "" : "s"}`, p.sx + r + 10, p.sy + 18);
        }
        ctx.restore();
      }
    }

    requestAnimationFrame(draw);
  }

  async function init() {
    buildLegend();
    resize();

    const [manifest, skillIndex] = await Promise.all([
      fetch(MANIFEST_URL, { cache: "no-store" }).then((r) => r.json()),
      fetch(SKILL_INDEX_URL, { cache: "no-store" }).then((r) => r.json()),
    ]);

    state.spheres = (manifest.spheres || []).map((s) => s);
    state.skills = (skillIndex.items || []).map((it) => it);
    state.skillsBySphere = buildSkillsBySphere(state.skills);
    buildNodes();

    // Hash routing
    if (location.hash) {
      const h = location.hash.replace(/^#/, "");
      const params = new URLSearchParams(h);
      const sphere = params.get("sphere");
      const doc = params.get("doc");
      if (doc) {
        const rel = resolveWikiTarget(doc);
        if (rel) openDoc(rel, doc, "Linked document");
      } else if (sphere) {
        const n = nodeById(`sphere:${sphere}`);
        if (n) openSphere(n);
      }
    }

    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);

  canvas.addEventListener("mousedown", (e) => {
    dragging = true;
    dragStart = { x: e.clientX, y: e.clientY, yaw: camera.tyaw, pitch: camera.tpitch };
  });
  window.addEventListener("mouseup", () => {
    dragging = false;
  });
  window.addEventListener("mousemove", (e) => {
    lastMouse.x = e.clientX;
    lastMouse.y = e.clientY;
    if (!dragging) return;
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    camera.tyaw = dragStart.yaw + dx * 0.006;
    camera.tpitch = clamp(dragStart.pitch + dy * 0.0045, -0.8, 0.8);
  });
  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const delta = Math.sign(e.deltaY);
      camera.tdist = clamp(camera.tdist + delta * 0.8, 3.9, 26);
    },
    { passive: false }
  );

  canvas.addEventListener("click", () => {
    if (!state.hoverId) return;
    const n = nodeById(state.hoverId);
    if (!n) return;
    focusOnNode(n.id);
    if (n.kind === "sphere") openSphere(n);
  });

  searchEl.addEventListener("input", () => {
    state.search = (searchEl.value || "").trim();
  });
  resetBtn.addEventListener("click", () => {
    state.search = "";
    searchEl.value = "";
    state.filterTongue = null;
    camera.tyaw = 0.6;
    camera.tpitch = 0.22;
    camera.tdist = 11.5;
  });

  closePanelBtn.addEventListener("click", () => panelEl.classList.remove("open"));
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") panelEl.classList.remove("open");
  });

  init().catch((err) => {
    console.error(err);
    panelTitleEl.textContent = "Skill vault failed to load";
    panelMetaEl.textContent = "Run the exporter to generate the required JSON + markdown under docs/research/sphere-grid/.";
    panelBodyEl.innerHTML = `<p><code>${escapeHtml(String(err))}</code></p>`;
    panelEl.classList.add("open");
  });
})();

