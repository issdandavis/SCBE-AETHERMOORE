"""
Cube canvas — the whole system in one zoomable picture.
========================================================

Renders a cube program as a colored trajectory of stones across the 16x16 board
(board.to_point gives the exact position, board.rgb the color), connected in move
order, with the bicameral logic/intuition reconciliation and the L13 governance
verdict in the header. Output is one self-contained HTML file (inline SVG + CSS +
JS, no dependencies) you open in a browser: pan, zoom, hover a stone for its opcode,
tongue token, note, and byte.

Unlike tldraw's canvas, nothing here is guessed — every coordinate is an exact,
reversible decode of the same bijective object, and "run" is the exact opcode VM.

    scbe canvas "+ sqrt * inc" --out cube.html
"""

from __future__ import annotations

from typing import List, Sequence

from . import bicameral as B
from . import board as BOARD
from . import cognition_syscall as CS
from . import frontdoor as F
from . import polyglot as P

_DECISION_COLOR = {"ALLOW": "#2e7d32", "QUARANTINE": "#f9a825", "ESCALATE": "#ef6c00", "DENY": "#c62828"}
_BANDS = ("arithmetic", "logic", "comparison", "aggregation")


def _stones(prog: Sequence[int], tongue: str):
    root = F._tongue_freq(tongue) if F._HAVE_TONGUES else 440.0
    out = []
    for i, b in enumerate(prog, 1):
        row, col = BOARD.to_point(b)
        r, g, bl = BOARD.rgb(b)
        tok = F.tongue_spell([b], tongue) if F._HAVE_TONGUES else ""
        out.append(
            dict(
                move=i,
                byte=b,
                row=row,
                col=col,
                name=P.BYTE_TO_NAME[b],
                color="#%02x%02x%02x" % (r, g, bl),
                note=BOARD.opcode_note(b, root)[1],
                token=tok,
            )
        )
    return out


def build_html(text: str, tongue: str = "ko") -> str:
    names, prog = F.tokens_to_program(text, tongue)
    thought = B.think(prog)
    receipt = CS.receipt_from_program(names)
    stones = _stones(prog, tongue)

    cell, pad = 44, 80
    w = h = 16 * cell + 2 * pad
    svg: List[str] = []
    # faint 16x16 grid
    for k in range(17):
        p = pad + k * cell
        svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" class="grid"/>' % (pad, p, w - pad, p))
        svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" class="grid"/>' % (p, pad, p, h - pad))
    # band labels (rows 0-3)
    for r, label in enumerate(_BANDS):
        svg.append('<text x="%d" y="%d" class="band">%s</text>' % (pad - 8, pad + r * cell + cell // 2 + 4, label))
    # the trajectory path through the stones (the program as a walk)
    if len(stones) > 1:
        pts = " ".join("%d,%d" % (pad + s["col"] * cell + cell // 2, pad + s["row"] * cell + cell // 2) for s in stones)
        svg.append('<polyline points="%s" class="path"/>' % pts)
    # stones
    for s in stones:
        cx = pad + s["col"] * cell + cell // 2
        cy = pad + s["row"] * cell + cell // 2
        svg.append(
            '<g class="stone" data-info="#%d %s  byte 0x%02x  %s  note %s%s">'
            '<circle cx="%d" cy="%d" r="%d" fill="%s"/>'
            '<text x="%d" y="%d" class="num">%d</text></g>'
            % (
                s["move"],
                s["name"],
                s["byte"],
                s["color"],
                s["note"],
                ("  " + s["token"]) if s["token"] else "",
                cx,
                cy,
                cell // 2 - 4,
                s["color"],
                cx,
                cy + 5,
                s["move"],
            )
        )

    decision = str(receipt["decision"])
    dcolor = _DECISION_COLOR.get(decision, "#555")
    conf = float(receipt["confidence"])
    head = """
<div id="head">
  <div class="title">SCBE cube canvas &middot; <span class="mono">%(prog)s</span></div>
  <div class="row">
    <span class="badge" style="background:%(dcolor)s">%(decision)s &rarr; %(action)s</span>
    <span class="conf">confidence <b>%(conf).0f%%</b></span>
    <span class="rel">logic <b>%(logic)s</b> &nbsp; intuition <b>%(intu)s</b> &nbsp; relation <b>%(rel)s</b></span>
  </div>
  <div class="why">%(why)s</div>
</div>""" % dict(
        prog=" ".join(names) or "(empty)",
        dcolor=dcolor,
        decision=decision,
        action=receipt["action"],
        conf=100 * conf,
        logic=B._fmt(thought["logic"]),
        intu=B._fmt(thought["intuition"]),
        rel=thought["relation"],
        why=thought["interpretation"],
    )

    return _PAGE % dict(head=head, w=w, h=h, svg="\n".join(svg))


_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>SCBE cube canvas</title>
<style>
  body{margin:0;background:#0d1117;color:#e6edf3;font:14px/1.4 -apple-system,Segoe UI,sans-serif}
  #head{padding:14px 18px;border-bottom:1px solid #222}
  .title{font-size:18px;font-weight:600;margin-bottom:8px}
  .mono{font-family:ui-monospace,Consolas,monospace;color:#7ee787}
  .row{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
  .badge{padding:3px 10px;border-radius:12px;color:#fff;font-weight:600}
  .conf,.rel{color:#9da7b3}.rel b,.conf b{color:#e6edf3}
  .why{margin-top:6px;color:#8b949e;font-style:italic}
  svg{display:block;cursor:grab}svg:active{cursor:grabbing}
  .grid{stroke:#1b2230;stroke-width:1}
  .band{fill:#586069;font-size:11px;text-anchor:end}
  .path{fill:none;stroke:#30363d;stroke-width:2;stroke-dasharray:4 4}
  .num{fill:#fff;font-size:13px;font-weight:700;text-anchor:middle;paint-order:stroke;stroke:#000;stroke-width:.6px}
  .stone{cursor:pointer}.stone:hover circle{stroke:#fff;stroke-width:2}
  #tip{position:fixed;pointer-events:none;background:#161b22;border:1px solid #30363d;
       padding:4px 8px;border-radius:6px;font-family:ui-monospace,monospace;font-size:12px;display:none}
  #hint{padding:8px 18px;color:#586069;font-size:12px}
</style></head><body>
%(head)s
<svg id="cv" viewBox="0 0 %(w)d %(h)d" width="100%%" height="72vh">%(svg)s</svg>
<div id="hint">scroll to zoom &middot; drag to pan &middot; hover a stone</div>
<div id="tip"></div>
<script>
const svg=document.getElementById('cv'),tip=document.getElementById('tip');
let vb={x:0,y:0,w:%(w)d,h:%(h)d};const set=()=>svg.setAttribute('viewBox',`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
svg.addEventListener('wheel',e=>{e.preventDefault();const k=e.deltaY<0?0.9:1.1;
  const mx=vb.x+vb.w*e.offsetX/svg.clientWidth,my=vb.y+vb.h*e.offsetY/svg.clientHeight;
  vb.x=mx-(mx-vb.x)*k;vb.y=my-(my-vb.y)*k;vb.w*=k;vb.h*=k;set();},{passive:false});
let pan=null;svg.addEventListener('mousedown',e=>pan={x:e.clientX,y:e.clientY});
addEventListener('mouseup',()=>pan=null);
addEventListener('mousemove',e=>{if(pan){vb.x-=(e.clientX-pan.x)*vb.w/svg.clientWidth;
  vb.y-=(e.clientY-pan.y)*vb.h/svg.clientHeight;pan={x:e.clientX,y:e.clientY};set();}});
document.querySelectorAll('.stone').forEach(g=>{
  g.addEventListener('mousemove',e=>{tip.style.display='block';tip.style.left=(e.clientX+12)+'px';
    tip.style.top=(e.clientY+12)+'px';tip.textContent=g.dataset.info;});
  g.addEventListener('mouseleave',()=>tip.style.display='none');});
</script></body></html>
"""


_GALLERY_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>SCBE illuminated archive</title>
<style>
  body{margin:0;background:#0d1117;color:#e6edf3;font:14px/1.4 -apple-system,Segoe UI,sans-serif}
  #head{padding:14px 18px;border-bottom:1px solid #222}
  .title{font-size:18px;font-weight:600;margin-bottom:8px}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .why{margin-top:6px;color:#8b949e;font-style:italic}
  .badge{padding:2px 9px;border-radius:11px;color:#fff;font-weight:600;font-size:12px}
  #grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;padding:16px}
  .card{background:#11161d;border:1px solid #30363d;border-left-width:4px;border-radius:8px;padding:10px}
  .mini{background:#0a0d12;border-radius:5px;padding:5px;margin-bottom:7px}
  .mini svg{width:100%;height:auto;display:block}
  .prog{font-family:ui-monospace,Consolas,monospace;color:#7ee787;font-size:12px;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .meta{display:flex;justify-content:space-between;align-items:center;margin:6px 0 2px}
  .conf{color:#9da7b3;font-size:12px}
  .niche{color:#586069;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
</style></head><body>
<!--HEAD-->
<div id="grid">
<!--CARDS-->
</div></body></html>
"""


def _mini_svg(prog: Sequence[int], tongue: str) -> str:
    """A compact board-trajectory thumbnail (the 4 core bands), for a gallery tile."""
    cell, pad = 9, 3
    w, h = 16 * cell + 2 * pad, 4 * cell + 2 * pad
    stones = _stones(prog, tongue)
    parts: List[str] = []
    if len(stones) > 1:
        pts = " ".join(
            "%d,%d" % (pad + s["col"] * cell + cell // 2, pad + min(s["row"], 3) * cell + cell // 2) for s in stones
        )
        parts.append(
            '<polyline points="%s" fill="none" stroke="#30363d" ' 'stroke-width="1.5" stroke-dasharray="2 2"/>' % pts
        )
    for s in stones:
        cx = pad + s["col"] * cell + cell // 2
        cy = pad + min(s["row"], 3) * cell + cell // 2
        parts.append('<circle cx="%d" cy="%d" r="%d" fill="%s"/>' % (cx, cy, cell // 2 - 1, s["color"]))
    return '<svg viewBox="0 0 %d %d" width="%d" height="%d">%s</svg>' % (w, h, w, h, "".join(parts))


def build_gallery(archive, tongue: str = "ko") -> str:
    """Render an illuminate() MAP-Elites archive as a governance-sorted gallery of
    mini cube-canvases — the over-creation archive made navigable."""
    counts = {"ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0}
    items = []
    for (sig, rel), e in archive.items():
        receipt = CS.receipt_from_program(e["ops"])
        decision = str(receipt["decision"])
        counts[decision] = counts.get(decision, 0) + 1
        items.append((decision, e, sig, rel))
    order = {"ALLOW": 0, "QUARANTINE": 1, "ESCALATE": 2, "DENY": 3}
    items.sort(key=lambda it: (order.get(it[0], 9), -float(it[1]["confidence"])))

    cards: List[str] = []
    for decision, e, sig, rel in items:
        prog = P.program_bytes(*e["ops"])
        dcolor = _DECISION_COLOR.get(decision, "#555")
        label = "+".join(sig) if sig else "(linear)"
        cards.append(
            '<div class="card" style="border-color:%s">'
            '<div class="mini">%s</div>'
            '<div class="prog">%s</div>'
            '<div class="meta"><span class="badge" style="background:%s">%s</span>'
            '<span class="conf">%.0f%%</span></div>'
            '<div class="niche">%s &middot; %s &middot; logic %s</div></div>'
            % (
                dcolor,
                _mini_svg(prog, tongue),
                " ".join(e["ops"]) or "(empty)",
                dcolor,
                decision,
                100 * float(e["confidence"]),
                label,
                rel,
                B._fmt(e["logic"]),
            )
        )

    legend = " &nbsp; ".join(
        '<span class="badge" style="background:%s">%s %d</span>' % (_DECISION_COLOR[d], d, counts[d])
        for d in ("ALLOW", "QUARANTINE", "ESCALATE", "DENY")
    )
    head = (
        '<div id="head"><div class="title">SCBE illuminated archive '
        '&middot; %d niches</div><div class="row">%s</div>'
        '<div class="why">mass-generated cube programs, curated by the bicameral gap '
        "(logic vs intuition), sorted by L13 governance</div></div>" % (len(archive), legend)
    )
    return _GALLERY_PAGE.replace("<!--HEAD-->", head).replace("<!--CARDS-->", "\n".join(cards))


def _demo() -> None:
    print(build_html("+ sqrt * inc")[:400])


if __name__ == "__main__":
    _demo()
