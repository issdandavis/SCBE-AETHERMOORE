from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_INCLUDES_TERMS = [
    "decision record",
    "threshold",
    "pilot checklist",
    "review notes",
    "manual",
    "delivery",
]


@dataclass
class PageAudit:
    path: str
    title: str
    primary_cta_count: int
    secondary_cta_count: int
    internal_links: int
    external_links: int
    word_count: int
    flags: dict[str, bool]
    metrics: dict[str, float]
    risks: list[str]
    strengths: list[str]


class _HTMLTextExtractor(HTMLParser):
    """Extract visible text from HTML, skipping script/style content."""

    _SKIP_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__()
        self._buf = StringIO()
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._buf.write(data)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", self._buf.getvalue()).strip()


def strip_html(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


class _LinkExtractor(HTMLParser):
    """Extract href values from anchor tags."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() == "a":
            for attr, value in attrs:
                if attr.lower() == "href" and value:
                    self.links.append(value)


def count_links(html: str) -> tuple[int, int]:
    parser = _LinkExtractor()
    try:
        parser.feed(html)
    except Exception:
        return 0, 0
    external = sum(1 for href in parser.links if href.startswith(("http://", "https://")))
    internal = len(parser.links) - external
    return internal, external


def clamp_0_10(value: float) -> float:
    return max(0.0, min(10.0, value))


def extract_section_by_id(html: str, section_id: str) -> str:
    pattern = re.compile(
        rf"<section[^>]*\bid=\"{re.escape(section_id)}\"[^>]*>[\s\S]*?</section>",
        flags=re.I,
    )
    m = pattern.search(html)
    if not m:
        raise ValueError(f"Section id not found: {section_id}")
    return m.group(0)


def replace_section_by_id(html: str, section_id: str, replacement: str) -> str:
    pattern = re.compile(
        rf"<section[^>]*\bid=\"{re.escape(section_id)}\"[^>]*>[\s\S]*?</section>",
        flags=re.I,
    )
    if not pattern.search(html):
        raise ValueError(f"Section id not found: {section_id}")
    return pattern.sub(replacement, html, count=1)


def page_flags(html: str) -> dict[str, bool]:
    lower = html.lower()

    includes_match = re.search(r"<section[^>]*\bid=\"includes\"[^>]*>([\s\S]*?)</section>", lower)
    includes_text = includes_match.group(1) if includes_match else ""

    offer_match = re.search(r"<section[^>]*\bid=\"offer\"[^>]*>([\s\S]*?)</section>", lower)
    offer_text = offer_match.group(1) if offer_match else ""

    has_concrete_includes = all(term in includes_text for term in REQUIRED_INCLUDES_TERMS)

    return {
        "has_h1": "<h1" in lower,
        "has_price": ("$29" in html) or ('"price": "29"' in html) or ('"price":"29"' in html),
        "has_one_time": ("one-time" in lower) or ("one time" in lower),
        "has_no_subscription": "no subscription" in lower,
        "has_manual": "manual" in lower,
        "has_delivery": "delivery" in lower,
        "has_support": "support" in lower or "mailto:" in lower,
        "has_faq": "<section id=\"faq\"" in lower,
        "has_buyer_fit": ("good fit" in lower) and ("not for" in lower),
        "has_success_check": ("success check" in lower) or ("first win" in lower),
        "has_hero_image": ("<img" in lower) and ('src="hero.png"' in lower),
        "has_concrete_includes": has_concrete_includes,
        "has_primary_cta_in_hero": "btn btn-primary" in offer_text,
        "has_final_cta": "final cta" in lower,
        "has_use_cases_link": "use-cases/governed-ai-workflows.html" in lower,
        "has_manual_proof_link": "proof/why-the-manual-exists.html" in lower,
        "has_comparison_link": "comparison/toolkit-vs-full-repo.html" in lower,
        "has_redteam_link": "redteam.html" in lower,
        "has_redteam_summary_link": "proof/red-team-summary.html" in lower,
    }


def score_page(html: str) -> tuple[dict[str, float], list[str], list[str]]:
    lower = html.lower()
    text = strip_html(html)
    word_count = len(text.split())
    primary_cta = len(re.findall(r"btn btn-primary", html))
    secondary_cta = len(re.findall(r"btn btn-secondary", html))

    flags = page_flags(html)

    includes_match = re.search(r"<section[^>]*\bid=\"includes\"[^>]*>([\s\S]*?)</section>", lower)
    includes_text = includes_match.group(1) if includes_match else ""

    # Category scoring (0-10): strict and discriminating.
    clarity = 0.0
    clarity += 2.0 if flags["has_h1"] else 0.0
    clarity += 2.0 if (550 <= word_count <= 1050) else 1.0 if (450 <= word_count <= 1350) else 0.0
    clarity += 2.0 if ("what you get" in lower or "inside the package" in lower) else 0.0
    clarity += 1.0 if flags["has_faq"] else 0.0
    clarity += 2.0 if flags["has_concrete_includes"] else 0.5 if "manual" in includes_text else 0.0
    clarity += 1.0 if flags["has_success_check"] else 0.0
    clarity = clamp_0_10(clarity)

    offer_strength = 0.0
    offer_strength += 3.0 if flags["has_price"] else 0.0
    offer_strength += 1.5 if flags["has_one_time"] else 0.0
    offer_strength += 1.0 if flags["has_no_subscription"] else 0.0
    offer_strength += 2.0 if ("buy" in lower or "checkout" in lower) else 0.0
    offer_strength += 1.5 if flags["has_concrete_includes"] else 0.0
    offer_strength += 1.0 if flags["has_success_check"] else 0.0
    offer_strength = clamp_0_10(offer_strength)

    proof = 0.0
    proof += 2.0 if (flags["has_manual"] and flags["has_delivery"] and flags["has_support"]) else 1.0 if (
        flags["has_manual"] and flags["has_support"]
    ) else 0.0
    proof += 1.5 if flags["has_hero_image"] else 0.0
    proof += 1.0 if flags["has_use_cases_link"] else 0.0
    proof += 1.0 if flags["has_comparison_link"] else 0.0
    proof += 1.0 if flags["has_manual_proof_link"] else 0.0
    proof += 1.5 if flags["has_redteam_link"] else 0.5 if "research" in lower else 0.0
    proof += 1.0 if flags["has_success_check"] else 0.0
    proof += 1.0 if flags["has_redteam_summary_link"] else 0.0
    proof = clamp_0_10(proof)

    buyer_fit = 0.0
    buyer_fit += 4.0 if flags["has_buyer_fit"] else 0.0
    buyer_fit += 2.0 if flags["has_use_cases_link"] else 0.0
    buyer_fit += 2.0 if flags["has_comparison_link"] else 0.0
    buyer_fit += 2.0 if ("consulting" in lower and "not for" in lower) else 0.0
    buyer_fit = clamp_0_10(buyer_fit)

    cta_discipline = 0.0
    cta_discipline += 3.5 if 2 <= primary_cta <= 3 else 2.0 if primary_cta == 1 else 0.0
    cta_discipline += 2.0 if secondary_cta <= 5 else 1.0 if secondary_cta <= 7 else 0.0
    cta_discipline += 2.5 if flags["has_primary_cta_in_hero"] else 0.0
    cta_discipline += 2.0 if flags["has_final_cta"] else 0.0
    cta_discipline = clamp_0_10(cta_discipline)

    friction = 0.0
    friction += 3.0 if "github" not in html.split("<main>", 1)[0].lower() else 0.0
    friction += 1.5 if flags["has_delivery"] else 0.0
    friction += 1.5 if flags["has_support"] else 0.0
    friction += 1.0 if flags["has_manual"] else 0.0
    friction += 1.0 if flags["has_no_subscription"] else 0.0
    friction += 1.0 if flags["has_faq"] else 0.0
    friction += 1.0 if "delivery link after checkout" in lower else 0.0
    friction = clamp_0_10(friction)

    risks: list[str] = []
    strengths: list[str] = []

    if primary_cta == 0:
        risks.append("No primary CTA found.")
    if secondary_cta > 7:
        risks.append("Too many secondary CTAs on page.")
    if not flags["has_hero_image"]:
        risks.append("Hero has no visible product image (only metadata).")
    if not flags["has_concrete_includes"]:
        risks.append("Includes section is still abstract; missing concrete deliverables phrasing.")
    if not flags["has_success_check"]:
        risks.append("Missing explicit success check / first win criteria.")
    if not flags["has_faq"]:
        risks.append("Missing FAQ objection handling.")

    if flags["has_buyer_fit"]:
        strengths.append("Buyer fit is explicitly scoped (good fit + not for).")
    if flags["has_manual"] and flags["has_delivery"] and flags["has_support"]:
        strengths.append("Trust path is inspectable before checkout (manual + delivery + support).")
    if flags["has_price"] and flags["has_one_time"] and flags["has_no_subscription"]:
        strengths.append("Offer is explicit (price + one-time + no subscription).")
    if flags["has_use_cases_link"] and flags["has_comparison_link"] and flags["has_manual_proof_link"]:
        strengths.append("Supporting pages exist (use cases + comparison + manual proof).")
    if flags["has_concrete_includes"]:
        strengths.append("Deliverables are concrete (templates/worksheet/checklist/notes/manual/delivery).")

    metrics = {
        "clarity": round(clarity, 2),
        "offer_strength": round(offer_strength, 2),
        "proof": round(proof, 2),
        "buyer_fit": round(buyer_fit, 2),
        "cta_discipline": round(cta_discipline, 2),
        "friction_control": round(friction, 2),
        "overall": round((clarity + offer_strength + proof + buyer_fit + cta_discipline + friction) / 6, 2),
    }
    return metrics, risks, strengths


def audit_html(path: Path, html: str) -> PageAudit:
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    title = title_match.group(1).strip() if title_match else path.name
    metrics, risks, strengths = score_page(html)
    internal_links, external_links = count_links(html)
    word_count = len(strip_html(html).split())
    return PageAudit(
        path=str(path.relative_to(ROOT)),
        title=title,
        primary_cta_count=len(re.findall(r"btn btn-primary", html)),
        secondary_cta_count=len(re.findall(r"btn btn-secondary", html)),
        internal_links=internal_links,
        external_links=external_links,
        word_count=word_count,
        flags=page_flags(html),
        metrics=metrics,
        risks=risks,
        strengths=strengths,
    )


def audit_page(path: Path) -> PageAudit:
    return audit_html(path, path.read_text(encoding="utf-8"))


def build_backlog(audit: PageAudit) -> list[dict[str, str]]:
    candidates = [
        {
            "page_slug": "use-cases/governed-ai-workflows.html",
            "reason": "Translate abstract governance language into concrete buyer scenarios.",
            "parent_surface": "docs/index.html",
            "cta": "Buy the toolkit",
        },
        {
            "page_slug": "proof/why-the-manual-exists.html",
            "reason": "Explain why the manual-first delivery path reduces buyer friction.",
            "parent_surface": "docs/index.html",
            "cta": "Read the manual",
        },
        {
            "page_slug": "comparison/toolkit-vs-full-repo.html",
            "reason": "Show what the starter pack includes versus the wider repo to reduce mismatch.",
            "parent_surface": "docs/index.html",
            "cta": "See exactly what is included",
        },
    ]

    backlog: list[dict[str, str]] = []
    for item in candidates:
        if not (ROOT / "docs" / item["page_slug"]).exists():
            backlog.append(item)

    if audit.metrics["proof"] < 8.5 and not (ROOT / "docs" / "proof/red-team-summary.html").exists():
        backlog.insert(
            0,
            {
                "page_slug": "proof/red-team-summary.html",
                "reason": "Summarize proof surface in plain buyer language.",
                "parent_surface": "docs/index.html",
                "cta": "Review proof",
            },
        )

    return backlog


def build_model_packets(audit: PageAudit, backlog: Iterable[dict[str, str]]) -> dict[str, str]:
    backlog_lines = "\n".join(f"- {item['page_slug']}: {item['reason']}" for item in backlog)
    summary = json.dumps(audit.metrics, indent=2)
    return {
        "closer_pass": (
            "Review this page as a closer. Tighten the offer, reduce hesitation, and improve the hero and CTA flow.\n"
            f"Current scores:\n{summary}\n"
            f"Risks: {', '.join(audit.risks) if audit.risks else 'none'}"
        ),
        "operator_pass": (
            "Review this page as an operator. Focus on delivery, manual, buyer path, support, and post-checkout trust.\n"
            f"Strengths: {', '.join(audit.strengths) if audit.strengths else 'none'}"
        ),
        "proof_pass": "Review this page for defensible claims. Flag any language that overstates implementation, proof, or scope.",
        "expansion_pass": (
            "Propose the next three supporting sales pages that should exist.\n"
            f"Current backlog:\n{backlog_lines}"
        ),
    }


def ollama_generate(*, base_url: str, model: str, prompt: str, timeout_s: int = 120) -> str:
    url = base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 700,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama request failed ({model}): {e}") from e
    return str(out.get("response", "")).strip()


def extract_first_json_obj(text: str) -> dict[str, object]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    raw = text[start : end + 1]
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Model output JSON must be an object.")
    return parsed


def escape_text(value: str) -> str:
    return html_lib.escape(value, quote=True)


def build_ul(items: list[str], *, klass: str | None = None) -> str:
    class_attr = f' class="{klass}"' if klass else ""
    lis = "\n".join(f"              <li>{escape_text(item.strip())}</li>" for item in items if item.strip())
    return f"            <ul{class_attr}>\n{lis}\n            </ul>"


def build_includes_section(packet: dict[str, object]) -> str:
    headline = escape_text(str(packet.get("headline", "This is the part you can open and use first.")).strip())
    paragraph = escape_text(str(packet.get("paragraph", "")).strip())
    inside = [str(x) for x in (packet.get("inside_package_bullets") or [])]
    first_win_title = escape_text(str(packet.get("first_win_title", "First win")).strip())
    first_win = [str(x) for x in (packet.get("first_win_bullets") or [])]
    helps = [str(x) for x in (packet.get("helps_you_do_bullets") or [])]

    if not paragraph:
        paragraph = (
            "The toolkit is built for fast starts: concrete templates, a pilot-first worksheet path, and a short manual that tells you what to do first."
        )

    return f"""<section id="includes">
      <div class="section-inner">
        <div class="section-head">
          <div class="eyebrow">What you get</div>
          <h2>{headline}</h2>
          <p>
            {paragraph}
          </p>
        </div>
        <div class="split split-3">
          <article class="slab">
            <h3>Inside the package</h3>
{build_ul(inside)}
          </article>
          <article class="slab">
            <h3>{first_win_title}</h3>
{build_ul(first_win, klass="checklist")}
            <p style="margin-top:12px; color: var(--muted); font-size: 16px;">If you can do those steps, the toolkit is working.</p>
          </article>
          <article class="slab">
            <h3>What this helps you do</h3>
{build_ul(helps)}
          </article>
        </div>
      </div>
    </section>"""


def validate_includes_packet(packet: dict[str, object]) -> list[str]:
    issues: list[str] = []
    inside_text = " ".join(str(x).lower() for x in (packet.get("inside_package_bullets") or []))
    if not inside_text:
        issues.append("inside_package_bullets is empty")
        return issues

    for term in REQUIRED_INCLUDES_TERMS:
        if term not in inside_text:
            issues.append(f"missing required term in inside_package_bullets: {term}")

    # Cheap length checks so the UI doesn't become a novel.
    for k in ["inside_package_bullets", "first_win_bullets", "helps_you_do_bullets"]:
        for item in (packet.get(k) or []):
            if len(str(item)) > 120:
                issues.append(f"{k} bullet too long")
                break

    return issues


def build_includes_prompt(*, current_section_text: str) -> str:
    return (
        "You are improving one section of a landing page: the \"What you get\" section for a $29 one-time purchase called the "
        "SCBE AI Governance Toolkit.\n\n"
        "Write buyer-first, concrete copy. No enterprise promises, no hype, no guarantees. Avoid deep internal jargon.\n\n"
        "Return ONLY valid JSON. No markdown.\n\n"
        "JSON schema:\n"
        "{\n"
        "  \"headline\": \"...\",\n"
        "  \"paragraph\": \"...\",\n"
        "  \"inside_package_bullets\": [\"...\"],\n"
        "  \"first_win_title\": \"...\",\n"
        "  \"first_win_bullets\": [\"...\"],\n"
        "  \"helps_you_do_bullets\": [\"...\"]\n"
        "}\n\n"
        "Hard constraints:\n"
        "- inside_package_bullets MUST mention: decision record template, threshold worksheet, pilot checklist, review notes format, manual, delivery + recovery.\n"
        "- Bullet length <= 16 words each.\n"
        "- first_win_bullets should be 3-6 short steps.\n\n"
        "Current section text (for context):\n"
        f"{current_section_text}\n"
    )


def pick_best_includes_rewrite(
    *,
    base_html: str,
    base_url: str,
    models: list[str],
    output_dir: Path,
) -> tuple[str | None, dict[str, object]]:
    current_section = extract_section_by_id(base_html, "includes")
    current_text = strip_html(current_section)

    prompt = build_includes_prompt(current_section_text=current_text)
    candidates: list[dict[str, object]] = []

    for model in models:
        raw = ollama_generate(base_url=base_url, model=model, prompt=prompt)
        try:
            packet = extract_first_json_obj(raw)
            packet["_model"] = model
            packet["_raw"] = raw[:1500]
            packet["_issues"] = validate_includes_packet(packet)
        except Exception as e:
            packet = {"_model": model, "_raw": raw[:1500], "_issues": [f"parse_error: {e}"]}
        candidates.append(packet)

    best: dict[str, object] | None = None
    best_html: str | None = None
    best_score = -1.0

    for packet in candidates:
        issues = list(packet.get("_issues") or [])
        if issues:
            continue
        try:
            new_includes = build_includes_section(packet)
            trial_html = replace_section_by_id(base_html, "includes", new_includes)
            trial_metrics, trial_risks, _trial_strengths = score_page(trial_html)
            trial_overall = float(trial_metrics.get("overall", 0.0))
            packet["_trial_metrics"] = trial_metrics
            packet["_trial_risks"] = trial_risks
        except Exception as e:
            packet["_issues"] = [f"apply_error: {e}"]
            continue

        if trial_overall > best_score:
            best_score = trial_overall
            best = packet
            best_html = trial_html

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rewrite_candidates.json").write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    if best is None or best_html is None:
        return None, {"error": "no_valid_rewrite"}

    (output_dir / "chosen_rewrite.json").write_text(json.dumps(best, indent=2), encoding="utf-8")
    return best_html, best


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a repeatable sales-improvement audit and packet builder for the website.")
    parser.add_argument("--page", default="docs/index.html", help="Target page relative to repo root.")
    parser.add_argument(
        "--output-dir",
        default="artifacts/marketing/website_sales_train",
        help="Output directory relative to repo root.",
    )
    parser.add_argument("--iterations", type=int, default=0, help="If set, run iterative include-section rewrite passes.")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Base URL for local Ollama.")
    parser.add_argument(
        "--models",
        default="llama3.2,AetherBot",
        help="Comma-separated Ollama models to propose rewrites (multi-model pass).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write improved HTML back to the target page during iterations (backup is created once).",
    )
    parser.add_argument("--sleep-ms", type=int, default=0, help="Optional delay between iterations.")
    args = parser.parse_args()

    page = ROOT / args.page
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    html = page.read_text(encoding="utf-8")

    if args.iterations <= 0:
        audit = audit_html(page, html)
        backlog = build_backlog(audit)
        packets = build_model_packets(audit, backlog)

        (output_dir / "audit.json").write_text(json.dumps(asdict(audit), indent=2), encoding="utf-8")
        (output_dir / "backlog.json").write_text(json.dumps(backlog, indent=2), encoding="utf-8")
        (output_dir / "model_packets.json").write_text(json.dumps(packets, indent=2), encoding="utf-8")

        summary = {
            "page": audit.path,
            "overall": audit.metrics["overall"],
            "top_risks": audit.risks[:3],
            "next_pages": [item["page_slug"] for item in backlog[:3]],
            "flags": audit.flags,
        }
        print(json.dumps(summary, indent=2))
        return

    if args.apply:
        backup_path = page.with_suffix(page.suffix + ".bak")
        if not backup_path.exists():
            backup_path.write_text(html, encoding="utf-8")

    models = [m.strip() for m in str(args.models).split(",") if m.strip()]
    best_html = html
    best_audit = audit_html(page, best_html)

    for i in range(1, args.iterations + 1):
        iter_dir = output_dir / f"iter_{i:02d}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        audit = audit_html(page, best_html)
        backlog = build_backlog(audit)
        packets = build_model_packets(audit, backlog)
        (iter_dir / "audit.json").write_text(json.dumps(asdict(audit), indent=2), encoding="utf-8")
        (iter_dir / "backlog.json").write_text(json.dumps(backlog, indent=2), encoding="utf-8")
        (iter_dir / "model_packets.json").write_text(json.dumps(packets, indent=2), encoding="utf-8")

        rewritten_html, chosen = pick_best_includes_rewrite(
            base_html=best_html,
            base_url=str(args.ollama_url),
            models=models,
            output_dir=iter_dir,
        )

        if rewritten_html:
            rewritten_audit = audit_html(page, rewritten_html)
            if rewritten_audit.metrics["overall"] >= best_audit.metrics["overall"]:
                best_html = rewritten_html
                best_audit = rewritten_audit

            (iter_dir / "page_snapshot.html").write_text(best_html, encoding="utf-8")
            if args.apply:
                page.write_text(best_html, encoding="utf-8")
        else:
            (iter_dir / "page_snapshot.html").write_text(best_html, encoding="utf-8")
            (iter_dir / "rewrite_failed.json").write_text(json.dumps(chosen, indent=2), encoding="utf-8")

        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    print(
        json.dumps(
            {
                "page": str(page.relative_to(ROOT)),
                "overall": best_audit.metrics["overall"],
                "top_risks": best_audit.risks[:3],
                "flags": best_audit.flags,
                "output_dir": str(output_dir.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
