#!/usr/bin/env python3
"""Shopify storefront launch pack.

Creates standardized product images, evaluates catalog quality, and optionally
publishes products + images to Shopify Admin.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from scripts.system.html_text import html_to_text


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.shopify_bridge import ShopifyCLIBridge  # noqa: E402


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts)[:64] if parts else "item"


def strip_html(raw: str) -> str:
    return html.unescape(html_to_text(raw or ""))


def _resolve_output_dir(raw_path: str) -> Path:
    target = (REPO_ROOT / raw_path).resolve()
    artifacts_root = (REPO_ROOT / "artifacts").resolve()
    if target != artifacts_root and artifacts_root not in target.parents:
        raise ValueError("output path must stay under artifacts/")
    return target


def first_sku(product: Dict[str, Any]) -> str:
    variants = product.get("variants", [])
    if not variants or not isinstance(variants[0], dict):
        return ""
    return str(variants[0].get("sku", "")).strip()


def first_price(product: Dict[str, Any]) -> str:
    variants = product.get("variants", [])
    if not variants or not isinstance(variants[0], dict):
        return "0.00"
    return str(variants[0].get("price", "0.00")).strip() or "0.00"


def palette_for_product(product_type: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    key = (product_type or "").lower()
    if "api" in key:
        return (18, 28, 58), (45, 98, 255), (221, 233, 255)
    if "education" in key:
        return (22, 42, 30), (64, 192, 122), (224, 248, 231)
    if "game" in key:
        return (38, 22, 52), (176, 88, 255), (241, 230, 255)
    return (22, 18, 36), (230, 178, 74), (252, 246, 231)


@dataclass
class ProductMediaRecord:
    title: str
    sku: str
    price: str
    product_type: str
    image_path: str
    alt_text: str
    score: int
    score_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "sku": self.sku,
            "price": self.price,
            "product_type": self.product_type,
            "image_path": self.image_path,
            "alt_text": self.alt_text,
            "score": self.score,
            "score_reasons": self.score_reasons,
        }


def draw_gradient(img: Image.Image, top_rgb: Tuple[int, int, int], bottom_rgb: Tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(img)
    width, height = img.size
    for y in range(height):
        t = y / max(height - 1, 1)
        rgb = tuple(int(top_rgb[i] * (1 - t) + bottom_rgb[i] * t) for i in range(3))
        draw.line([(0, y), (width, y)], fill=rgb)


def find_fonts() -> Tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for c in candidates:
        if c.exists():
            try:
                return ImageFont.truetype(str(c), 92), ImageFont.truetype(str(c), 50)
            except Exception:
                continue
    default = ImageFont.load_default()
    return default, default


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    current: List[str] = []
    for w in words:
        probe = " ".join(current + [w]).strip()
        bbox = draw.textbbox((0, 0), probe, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width or not current:
            current.append(w)
        else:
            lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines[:4]


def score_product(product: Dict[str, Any]) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    score = 100
    title = str(product.get("title", "")).strip()
    body = strip_html(str(product.get("body_html", "")))
    tags = str(product.get("tags", "")).strip()
    price = first_price(product)

    if len(title) < 12:
        score -= 12
        reasons.append("Title too short; increase specificity.")
    if len(title) > 85:
        score -= 8
        reasons.append("Title too long; shorten for conversion.")
    if len(body) < 260:
        score -= 16
        reasons.append("Description too short; add concrete outcomes.")
    if len(tags.split(",")) < 3:
        score -= 10
        reasons.append("Tag coverage is low.")
    try:
        p = float(price)
        if p <= 0:
            score -= 20
            reasons.append("Price is zero or invalid.")
    except ValueError:
        score -= 20
        reasons.append("Price value is invalid.")

    if "includes" not in body.lower() and "<li>" not in str(product.get("body_html", "")).lower():
        score -= 8
        reasons.append("No clear deliverables list detected.")

    score = max(score, 0)
    if not reasons:
        reasons.append("Catalog entry meets baseline launch quality.")
    return score, reasons


def render_image(
    *,
    title: str,
    sku: str,
    price: str,
    product_type: str,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 1600), (0, 0, 0))
    bg_top, bg_bottom, accent = palette_for_product(product_type)
    draw_gradient(img, bg_top, bg_bottom)
    draw = ImageDraw.Draw(img)
    title_font, body_font = find_fonts()

    # Border frame
    draw.rounded_rectangle((72, 72, 1528, 1528), radius=44, outline=accent, width=6)
    draw.rounded_rectangle((120, 120, 1480, 1480), radius=32, outline=(255, 255, 255), width=2)

    # Brand bar
    draw.rectangle((150, 180, 1450, 300), fill=(8, 8, 14))
    draw.text((180, 205), "AETHERMOORE WORKS", fill=accent, font=body_font)

    # Product title
    lines = wrap_text(draw, title.upper(), title_font, max_width=1200)
    y = 420
    for line in lines:
        draw.text((180, y), line, fill=(245, 247, 255), font=title_font)
        y += 116

    # SKU and price
    draw.text((180, 1180), f"SKU: {sku}", fill=(218, 226, 255), font=body_font)
    draw.text((180, 1260), f"PRICE: ${price}", fill=(255, 255, 255), font=body_font)
    draw.text((180, 1340), f"TYPE: {product_type or 'Digital'}", fill=(200, 213, 255), font=body_font)

    # CTA label
    draw.rounded_rectangle((180, 1430, 860, 1510), radius=14, fill=accent)
    draw.text((220, 1450), "READY TO SHIP", fill=(10, 12, 20), font=body_font)

    img.save(out_path, format="PNG", optimize=True)


def build_records(products: List[Dict[str, Any]], out_dir: Path) -> List[ProductMediaRecord]:
    records: List[ProductMediaRecord] = []
    for row in products:
        product = row.get("product", {}) if isinstance(row, dict) else {}
        title = str(product.get("title", "Untitled Product")).strip()
        sku = first_sku(product) or safe_slug(title).upper()
        price = first_price(product)
        product_type = str(product.get("product_type", "Digital")).strip()
        score, reasons = score_product(product)

        filename = f"{safe_slug(sku)}.png"
        image_path = out_dir / filename
        render_image(
            title=title,
            sku=sku,
            price=price,
            product_type=product_type,
            out_path=image_path,
        )

        records.append(
            ProductMediaRecord(
                title=title,
                sku=sku,
                price=price,
                product_type=product_type,
                image_path=str(image_path.resolve()),
                alt_text=f"{title} product cover image",
                score=score,
                score_reasons=reasons,
            )
        )
    return records


def upload_images_live(
    bridge: ShopifyCLIBridge, sync_summary: Dict[str, Any], records: List[ProductMediaRecord]
) -> Dict[str, Any]:
    sku_to_id: Dict[str, int] = {}
    for result in sync_summary.get("results", []):
        action = str(result.get("action", ""))
        if action not in {"created", "updated"}:
            continue
        sku = str(result.get("sku", "")).strip()
        pid = result.get("product_id")
        if sku and isinstance(pid, int):
            sku_to_id[sku] = pid

    uploads: List[Dict[str, Any]] = []
    for rec in records:
        product_id = sku_to_id.get(rec.sku)
        if not product_id:
            uploads.append({"sku": rec.sku, "status": "skipped", "reason": "product_id_not_found"})
            continue
        image_file = Path(rec.image_path)
        if not image_file.exists():
            uploads.append({"sku": rec.sku, "status": "skipped", "reason": "image_missing"})
            continue

        try:
            payload = {
                "image": {
                    "attachment": base64.b64encode(image_file.read_bytes()).decode("ascii"),
                    "filename": image_file.name,
                    "alt": rec.alt_text,
                }
            }
            bridge._shopify_request("POST", f"/products/{product_id}/images.json", payload=payload)
            uploads.append({"sku": rec.sku, "product_id": product_id, "status": "uploaded"})
        except Exception as exc:  # noqa: BLE001
            uploads.append({"sku": rec.sku, "product_id": product_id, "status": "error", "error": str(exc)})

    return {
        "attempted": len(records),
        "uploaded": sum(1 for u in uploads if u.get("status") == "uploaded"),
        "errors": sum(1 for u in uploads if u.get("status") == "error"),
        "results": uploads,
    }


def run_playwright_health(store_domain: str, out_dir: Path) -> Dict[str, Any]:
    script = REPO_ROOT / "scripts" / "shopify_both_side_test.py"
    if not script.exists():
        return {"ok": False, "reason": "shopify_both_side_test_missing"}
    cmd = [
        sys.executable,
        str(script),
        "--store-domain",
        store_domain,
        "--screenshot-dir",
        str(out_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(REPO_ROOT))
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Shopify launch assets and optionally sync live.")
    parser.add_argument("--store", default="aethermore-code.myshopify.com", help="Shopify store domain")
    parser.add_argument("--output-dir", default="artifacts/shopify-launch-pack", help="Output directory root")
    parser.add_argument("--run-both-side-test", action="store_true", help="Run storefront/admin Playwright smoke test")
    parser.add_argument("--publish-live", action="store_true", help="Publish products and upload generated images")
    parser.add_argument(
        "--emit-crosstalk", action="store_true", help="Emit cross-talk packet via terminal emitter script"
    )
    parser.add_argument("--session-tag", default="shopify-launch-pack", help="Task/session tag for artifacts")
    return parser.parse_args()


def emit_crosstalk(task_id: str, summary: str, next_action: str) -> Dict[str, Any]:
    script = REPO_ROOT / "scripts" / "system" / "terminal_crosstalk_emit.ps1"
    if not script.exists():
        return {"ok": False, "reason": "terminal_crosstalk_emit_missing"}

    cmd = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-TaskId",
        task_id,
        "-Summary",
        summary,
        "-NextAction",
        next_action,
        "-Recipient",
        "agent.claude",
        "-Status",
        "in_progress",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(REPO_ROOT))
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def main() -> int:
    args = parse_args()
    stamp = utc_stamp()
    out_root = (REPO_ROOT / args.output_dir / stamp).resolve()
    media_dir = out_root / "media"
    out_root.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    bridge = ShopifyCLIBridge(store=args.store)
    catalog = bridge.revenue_products_to_shopify()
    records = build_records(catalog, media_dir)

    avg_score = round(sum(r.score for r in records) / max(len(records), 1), 2)
    health_result = {"ok": False, "reason": "not_requested"}
    if args.run_both_side_test:
        health_result = run_playwright_health(args.store, out_root / "both-side")

    live_sync = {"ok": False, "reason": "not_requested"}
    image_upload = {"ok": False, "reason": "not_requested"}
    if args.publish_live:
        try:
            sync_summary = bridge.sync_products_live()
            live_sync = {"ok": True, "summary": sync_summary}
            image_upload = {"ok": True, "summary": upload_images_live(bridge, sync_summary, records)}
        except Exception as exc:  # noqa: BLE001
            live_sync = {"ok": False, "error": str(exc)}
            image_upload = {"ok": False, "reason": "sync_failed"}

    payload = {
        "ok": True,
        "generated_at": utc_now_iso(),
        "store": args.store,
        "session_tag": args.session_tag,
        "products_count": len(records),
        "avg_catalog_score": avg_score,
        "records": [r.to_dict() for r in records],
        "health_test": health_result,
        "live_sync": live_sync,
        "image_upload": image_upload,
        "output_dir": str(out_root),
    }

    json_path = out_root / "shopify-launch-pack.json"
    md_path = out_root / "shopify-launch-pack.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        "# Shopify Launch Pack",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Store: {args.store}",
        f"- Product assets generated: {len(records)}",
        f"- Average catalog score: {avg_score}",
        f"- Health test requested: {args.run_both_side_test}",
        f"- Live publish requested: {args.publish_live}",
        "",
        "## Top Issues",
    ]
    weak = sorted(records, key=lambda r: r.score)[:3]
    for item in weak:
        md_lines.append(f"- `{item.sku}` ({item.score}/100): {item.score_reasons[0]}")
    md_lines.extend(
        [
            "",
            "## Next Actions",
            "1. Disable storefront password in Shopify Admin > Online Store > Preferences.",
            "2. Verify home page shows product cards instead of password gate.",
            "3. Publish or update products with generated media if API token is configured.",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    crosstalk_result = {"ok": False, "reason": "not_requested"}
    if args.emit_crosstalk:
        crosstalk_result = emit_crosstalk(
            task_id="SHOPIFY-LAUNCH-PACK",
            summary=(
                f"Generated Shopify launch pack for {args.store}: " f"{len(records)} assets, avg score {avg_score}"
            ),
            next_action="Disable storefront password and run live publish once token is configured.",
        )
        payload["crosstalk"] = crosstalk_result
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "json_path": str(json_path),
                "md_path": str(md_path),
                "media_dir": str(media_dir),
                "avg_catalog_score": avg_score,
                "health_test": health_result,
                "live_sync": live_sync,
                "image_upload": image_upload,
                "crosstalk": crosstalk_result,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
