"""
Rebuild Attachment X pptx with properly numbered slide files.
The broken file has duplicate slide4.xml entries (python-pptx bug when
duplicating slides). This script reads the source template, fills each
slide directly at the XML level, and writes a clean zip.
"""
import shutil
import zipfile
import re
import io
from copy import deepcopy
from lxml import etree

X_SRC = (
    "docs/proposals/DARPA_MATHBAC/official_templates/"
    "Attachment_X_Proposal_Overview_and_Proposed_Metrics.pptx"
)
X_OUT = (
    "docs/proposals/DARPA_MATHBAC/package_work/10_attachment_x_metrics/"
    "Attachment_X_SCBE_FILLED.pptx"
)

# ──────────────────────────────────────────────────────────────────────────────
# Content
# ──────────────────────────────────────────────────────────────────────────────

PLATFORM_DESC = (
    "# of agents: 2 (configurable per campaign)\n"
    "types of agents: Math-reasoning orchestrator + SSM science validator\n"
    "models: ChemBERTa-77M + Qwen2.5-Coder-0.5B-Instruct\n"
    "# tasks / domains: 2 NMR task families + 1 generalization lane (Hammett)\n"
    "months to build (current) platform: 18"
)

TA1_OVERVIEW = (
    "SCBE-AETHERMOORE proposes a TA1 mathematical framework for agentic communication "
    "protocols. The framework treats a multi-agent campaign as a composed operator "
    "T = L14 o ... o L1 acting on geometric state "
    "psi(t) = (psi_1(t),...,psi_N(t), G_t, pd(t)) in B^(nxN) x G_N x R+, "
    "where psi_i(t) is an agent state embedded in the Poincare ball, G_t is the "
    "evolving trust-weighted directed protocol graph, and pd(t) is the L11 predictive-"
    "density / triadic temporal term. Safety and communication quality are measured by "
    "hyperbolic distance, signed graph dynamics (CDPTI), trace-level mathematical "
    "evidence (MEE), axiom compliance (ACV), and protocol identity (PIS). "
    "Phase I: fixed pretrained agents, NMR spectroscopy task families, Hammett "
    "generalization. Phase II: remove static-agent constraint; use Phase I protocol "
    "measurements as reward and selection signals."
)

METRICS = [
    {
        "title": "Proposed Metric #1 — Mathematical Evidence Emission (MEE)",
        "content": (
            "Technical Area: TA1\n\n"
            "Description: MEE measures the rate and verification quality of checkable "
            "mathematical artifacts emitted during inter-agent communication: formulas, "
            "derivation steps, citations, executable code, and numerical assertions.\n\n"
            "Method for calculation: For each act, extract evidence artifacts and score each "
            "with a class-appropriate verifier (symbolic simplification, sandbox execution, "
            "dimensional checks, citation resolution). MEE = sum(scores) / # inter-agent messages. "
            "Report MEE_density, MEE_pass_rate, and artifact-class balance. "
            "IV&V inputs: governance_events.jsonl, evidence_artifacts.jsonl, task_manifests.json.\n\n"
            "Progress against program goals: MATHBAC seeks science-discovery protocols that are "
            "understandable, not only successful. MEE distinguishes a correct black-box answer "
            "from a campaign that leaves a mathematical audit trail.\n\n"
            "Supplement to current metrics: Program success, speed, and generalization are end-state "
            "measures. MEE is trace-level: did the protocol produce falsifiable scientific evidence?\n\n"
            "Adoption argument: MEE gives IV&V a low-cost audit surface using the same evidence log "
            "needed to check math content. Vendor-neutral; computable from JSONL without SCBE source.\n\n"
            "Literature: Minerva (arXiv:2206.14858), Polu/Sutskever (arXiv:2009.03393), "
            "AlphaGeometry (Nature 2024), LeanDojo (NeurIPS 2023).\n\n"
            "Phase I targets: M3 — extractor and verifier calibration. "
            "M9 — MEE density/pass-rate on NMR task families. "
            "M13 — compare vs. Mixtral-8x7B baseline."
        ),
    },
    {
        "title": "Proposed Metric #2 — Axiom Compliance Vector (ACV)",
        "content": (
            "Technical Area: TA1\n\n"
            "Description: ACV is a five-component vector in [0,1]^5 measuring per-act compliance "
            "with Unitarity, Locality, Causality, Symmetry, and Composition.\n\n"
            "Method for calculation: Evaluate five predicates per act: information conservation "
            "(Unitarity), bounded influence radius (Locality), dependency-graph topological order "
            "(Causality), role-permutation invariance (Symmetry), pipeline schema continuity "
            "(Composition). Campaign ACV = mean predicate vector. "
            "ACV_norm = (5 - ||1 - ACV||_1) / 5. "
            "IV&V inputs: governance_events.jsonl, latent_states.npz, task_manifests.json.\n\n"
            "Progress against program goals: TA1 seeks stability and convergence analysis. ACV "
            "measures whether structural conditions for operator well-posedness hold.\n\n"
            "Supplement to current metrics: A protocol can be fast and correct while violating "
            "causality or composition. ACV catches structurally pathological protocols.\n\n"
            "Adoption argument: Vendor-neutral — any performer can emit five predicate values "
            "from ordinary communication and latent-state logs. Provides Phase II teams a "
            "compatibility check before combining protocols.\n\n"
            "Literature: von Neumann formalism, Pearl causality, Mac Lane composition, Goyal RIM.\n\n"
            "Phase I targets: M3 — ACV field in event schema. M9 — mean ACV_norm >= 0.90."
        ),
    },
    {
        "title": "Proposed Metric #3 — Communication-Dynamics Phase-Transition Index (CDPTI)",
        "content": (
            "Technical Area: TA1\n\n"
            "Description: CDPTI measures signed regime changes in the multi-agent communication "
            "graph, detecting communication breakdown and coordinated adversarial convergence.\n\n"
            "Method for calculation: Build time-windowed directed graph G_t. Edge (i,j) weighted "
            "by communication energy, signed by harmonic-wall evaluation: "
            "w_ij(t) = sign(H_ij(t) - H_min) * ||log(S_ij)||. "
            "Trust-weighted directed Laplacian: L_H(G_t) = D_out(W_H) - W_H. "
            "Signed readout: CDPTI(t) = Re(lambda_2(L_H(G_t))) / Re(lambda_2(L_H(G_t0))). "
            "Negative signed-connectivity growth triggers escalation even if unsigned rises. "
            "IV&V inputs: governance_events.jsonl, latent_states.npz, protocol_graph_edges.jsonl.\n\n"
            "Progress against program goals: PA line 443 — characterize communication dynamics. "
            "CDPTI identifies regime changes and their direction (safe vs. adversarial basin).\n\n"
            "Supplement to current metrics: Outcome metrics don't show whether a campaign "
            "progressed smoothly or converged adversarially. CDPTI adds temporal/directional resolution.\n\n"
            "Adoption argument: Directly addresses non-compositional safety (Spera 2026): conjunctive "
            "drift appears as signed graph motion rather than isolated local actions.\n\n"
            "Literature: Newman spectra, Strogatz dynamics, Cohen-Steiner, Spera (arXiv:2603.15973).\n\n"
            "Phase I targets: M3 instrument L_H. M6 live CDPTI. M13 >= 95% recall, <= 5% FPR."
        ),
    },
    {
        "title": "Proposed Metric #4 — Protocol Information Signature (PIS)",
        "content": (
            "Technical Area: TA1\n\n"
            "Description: PIS is a fixed-dimensional protocol fingerprint summarizing the structural "
            "identity of a multi-agent protocol, independent of agent names and surface formatting.\n\n"
            "Method for calculation: Compute mutual-information features, conditional-entropy graph "
            "features, role-transition features, latent-delta covariance summaries, and persistent-"
            "homology features. Project via released pis_projection_matrix.json. Compare with cosine "
            "distance and cluster persistence. "
            "IV&V inputs: governance_events.jsonl, latent_states.npz, protocol_graph_edges.jsonl, "
            "pis_projection_matrix.json.\n\n"
            "Progress against program goals: TA1 deliverable C requires a protocol catalog. "
            "PIS is the catalog key: determines whether two protocols are structurally similar.\n\n"
            "Supplement to current metrics: Success/speed do not identify whether a protocol is new, "
            "redundant, or transferable. PIS adds identity and similarity structure to the rubric.\n\n"
            "Adoption argument: Detects benchmark gaming, supports cross-subdomain transfer, and "
            "enables catalog queries by structural similarity.\n\n"
            "Literature: Cover/Thomas, Tishby bottleneck, Indyk/Motwani ANN, "
            "Charikar similarity estimation, persistent-homology stability.\n\n"
            "Phase I targets: M6 — preliminary PIS feature extractor. "
            "M13 — catalog v1 with reference centroids and cluster-separation report."
        ),
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# XML helpers
# ──────────────────────────────────────────────────────────────────────────────

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PR = "http://schemas.openxmlformats.org/package/2006/relationships"


def _q(ns, tag):
    return f"{{{ns}}}{tag}"


def make_txbody(lines, font_pt=9):
    """Create an <a:txBody> element with given lines."""
    txBody = etree.Element(_q(NS_A, "txBody"))
    bodyPr = etree.SubElement(txBody, _q(NS_A, "bodyPr"))
    bodyPr.set("wrap", "square")
    bodyPr.set("rtlCol", "0")
    lstStyle = etree.SubElement(txBody, _q(NS_A, "lstStyle"))

    for line in lines:
        p = etree.SubElement(txBody, _q(NS_A, "p"))
        r = etree.SubElement(p, _q(NS_A, "r"))
        rPr = etree.SubElement(r, _q(NS_A, "rPr"))
        rPr.set("lang", "en-US")
        rPr.set("sz", str(font_pt * 100))
        rPr.set("dirty", "0")
        # Font
        solidFill = etree.SubElement(rPr, _q(NS_A, "solidFill"))
        srgbClr = etree.SubElement(solidFill, _q(NS_A, "srgbClr"))
        srgbClr.set("val", "000000")
        latin = etree.SubElement(rPr, _q(NS_A, "latin"))
        latin.set("typeface", "Tahoma")
        t = etree.SubElement(r, _q(NS_A, "t"))
        t.text = line

    return txBody


def set_shape_text(sp_tree, name_pattern, new_text, font_pt=9):
    """Find shape by name substring and replace its text."""
    for sp in sp_tree.iter(_q(NS_P, "sp")):
        nvSpPr = sp.find(_q(NS_P, "nvSpPr"))
        if nvSpPr is None:
            continue
        cNvPr = nvSpPr.find(_q(NS_P, "cNvPr"))
        if cNvPr is None:
            continue
        sp_name = cNvPr.get("name", "")
        # Get current text
        txBody = sp.find(_q(NS_P, "txBody"))
        if txBody is None:
            continue
        current_text = "".join(t.text or "" for t in txBody.iter(_q(NS_A, "t")))

        if name_pattern in sp_name or name_pattern in current_text:
            # Replace txBody
            sp.remove(txBody)
            new_txBody = make_txbody(new_text.split("\n"), font_pt)
            sp.append(new_txBody)
            return True
    return False


def clear_shape_by_text(sp_tree, text_fragment):
    """Clear (empty) a shape whose text contains the fragment."""
    for sp in sp_tree.iter(_q(NS_P, "sp")):
        txBody = sp.find(_q(NS_P, "txBody"))
        if txBody is None:
            continue
        current = "".join(t.text or "" for t in txBody.iter(_q(NS_A, "t")))
        if text_fragment in current:
            sp.remove(txBody)
            new_txBody = make_txbody([""], 9)
            sp.append(new_txBody)


def set_table_cell(tbl_elem, row, col, text, font_pt=9):
    """Set content of a table cell at (row, col)."""
    rows = tbl_elem.findall(_q(NS_A, "tr"))
    if row >= len(rows):
        return
    cells = rows[row].findall(_q(NS_A, "tc"))
    if col >= len(cells):
        return
    txBody = cells[col].find(_q(NS_A, "txBody"))
    if txBody is None:
        return
    # Remove existing paragraphs
    for p in txBody.findall(_q(NS_A, "p")):
        txBody.remove(p)
    # Add new content
    for line in text.split("\n"):
        p = etree.SubElement(txBody, _q(NS_A, "p"))
        r = etree.SubElement(p, _q(NS_A, "r"))
        rPr = etree.SubElement(r, _q(NS_A, "rPr"))
        rPr.set("lang", "en-US")
        rPr.set("sz", str(font_pt * 100))
        rPr.set("dirty", "0")
        latin = etree.SubElement(rPr, _q(NS_A, "latin"))
        latin.set("typeface", "Tahoma")
        t_el = etree.SubElement(r, _q(NS_A, "t"))
        t_el.text = line


def get_table_header_text(tbl_elem, row=0, col=0):
    rows = tbl_elem.findall(_q(NS_A, "tr"))
    if not rows:
        return ""
    cells = rows[0].findall(_q(NS_A, "tc"))
    if not cells:
        return ""
    return "".join(t.text or "" for t in cells[0].iter(_q(NS_A, "t")))


# ──────────────────────────────────────────────────────────────────────────────
# Read original template and build clean output
# ──────────────────────────────────────────────────────────────────────────────

with zipfile.ZipFile(X_SRC, "r") as zin:
    src_members = {name: zin.read(name) for name in zin.namelist()}

# Parse presentation rels to find slide mapping
prs_rels_xml = etree.fromstring(src_members["ppt/_rels/presentation.xml.rels"])
slide_rels = {}  # rId → slide filename
for rel in prs_rels_xml:
    target = rel.get("Target", "")
    if "slides/slide" in target and not "Layout" in target and not "Master" in target:
        # target is relative to ppt/ so prepend ppt/
        clean = target.lstrip("./").lstrip("../")
        if not clean.startswith("ppt/"):
            clean = "ppt/" + clean
        slide_rels[rel.get("Id")] = clean

print(f"Template slides: {list(slide_rels.values())}")

# Parse presentation.xml sldIdLst to get slide order
prs_xml = etree.fromstring(src_members["ppt/presentation.xml"])
sldIdLst = prs_xml.find(_q(NS_P, "sldIdLst"))
ordered_slide_rids = [el.get(_q(NS_R, "id")) for el in sldIdLst]
ordered_slide_files = [slide_rels[rid] for rid in ordered_slide_rids if rid in slide_rels]
print(f"Slide order: {ordered_slide_files}")
# Template: slide2=guidance, slide3=TA1, slide4=TA2, slide5=metric template
# We want: slide1=TA1, slide2-5=metrics

# Parse each slide
slides_xml = {}
for sf in ordered_slide_files:
    slides_xml[sf] = etree.fromstring(src_members[sf])

# ── Process TA1 slide (index 1, originally slide3.xml) ──
ta1_key = ordered_slide_files[1]
ta1_root = slides_xml[ta1_key]
sp_tree = ta1_root.find(f".//{_q(NS_P, 'spTree')}")

# Clear instruction boxes
clear_shape_by_text(sp_tree, "Instructions (delete before submitting)")
clear_shape_by_text(sp_tree, "How did you set your targets")
clear_shape_by_text(sp_tree, "Proposers are expected to")

# Platform description
set_shape_text(sp_tree, "# of agents:", PLATFORM_DESC, font_pt=9)

# Proposal overview (add to sp_tree — replace the graphic instruction box)
set_shape_text(sp_tree, "Include image of current agentic platform", TA1_OVERVIEW, font_pt=9)

# Fill tables
for tbl in ta1_root.iter(_q(NS_A, "tbl")):
    header = get_table_header_text(tbl)
    rows = tbl.findall(_q(NS_A, "tr"))
    n_rows = len(rows)
    n_cols = len(rows[0].findall(_q(NS_A, "tc"))) if rows else 0

    if "TA1 Rubric" in header and n_cols == 3:
        # 4x3: header + 3 data rows
        set_table_cell(tbl, 1, 0, "% success rate", 8)
        set_table_cell(tbl, 1, 1, "Terminal-bench: 13/13 (100%)\nPetri: 172/173 (99.42%)\nReal-patch: 5/5 (100%)", 8)
        set_table_cell(tbl, 1, 2, "CDPTI >=95% recall; ACV_norm >=0.90", 8)
        set_table_cell(tbl, 2, 0, "Governance overhead", 8)
        set_table_cell(tbl, 2, 1, "Zero overhead (terminal-bench-core-0.1.1)", 8)
        set_table_cell(tbl, 2, 2, "<=5% overhead on governed benchmark runs", 8)
        set_table_cell(tbl, 3, 0, "IV&V bundle format", 8)
        set_table_cell(tbl, 3, 1, "JSONL governance_events + latent_states.npz defined", 8)
        set_table_cell(tbl, 3, 2, "Bundle locked at M1; phi-ablation complete by M3", 8)
        print(f"  FILLED: TA1 rubric table ({n_rows}x{n_cols})")

    elif "TA1 Goal" in header and n_cols == 3:
        goal_rows = [
            ("(a)", "Poincare-ball operator T = L14 o...o L1", "Hyperbolic geometry (Ganea), Lyapunov (Khalil), Mac Lane"),
            ("(b)", "Trust-weighted directed Laplacian L_H(G_t)", "Newman graph spectra, Strogatz, Fiedler connectivity"),
            ("(c)", "CDPTI signed coherence drift index", "Spera non-comp. safety (arXiv:2603.15973), persistence"),
            ("(d)", "MEE artifact extraction and verification", "Minerva (arXiv:2206.14858), LeanDojo (NeurIPS 2023)"),
            ("(e)", "ACV 5-predicate compliance vector", "Pearl causality, von Neumann, Mac Lane, Goyal RIM"),
            ("(f)", "PIS protocol identity signature", "Cover/Thomas, Tishby, Indyk/Motwani, persistent homology"),
            ("(g)", "CDT: Lagrangian automation for new subdomains", "Phase I deliverable C; Hammett generalization by M9"),
        ]
        for i, (g, m, r) in enumerate(goal_rows):
            if i + 1 < n_rows:
                set_table_cell(tbl, i + 1, 0, g, 8)
                set_table_cell(tbl, i + 1, 1, m, 8)
                set_table_cell(tbl, i + 1, 2, r, 8)
        print(f"  FILLED: TA1 goals table ({n_rows}x{n_cols})")

    elif "TA1 " in header and n_cols == 2 and n_rows >= 4:
        set_table_cell(tbl, 0, 0, "TA1 Field", 9)
        set_table_cell(tbl, 0, 1, "Details", 9)
        set_table_cell(tbl, 1, 0, "Selected Science Subdomain(s)", 9)
        set_table_cell(tbl, 1, 1, "NMR spectroscopy (primary); Hammett equation (generalization)", 9)
        set_table_cell(tbl, 2, 0, "1st family of scientific tasks", 9)
        set_table_cell(tbl, 2, 1, "Task A: 1H NMR spectrum to molecular structure (BMRB+PDB)", 9)
        if n_rows > 3:
            set_table_cell(tbl, 3, 0, "2nd family of scientific tasks", 9)
            set_table_cell(tbl, 3, 1, "Task B: 2D COSY to vicinal J-coupling connectivity (BMRB)", 9)
        if n_rows > 4:
            set_table_cell(tbl, 4, 0, "Small science models (SSMs)", 9)
            set_table_cell(tbl, 4, 1, "ChemBERTa-77M + Qwen2.5-Coder-0.5B-Instruct", 9)
        print(f"  FILLED: TA1 details table ({n_rows}x{n_cols})")

print(f"  TA1 overview slide complete")

# ── Build metric slide XML from template (index 3 in original = slide5.xml) ──
metric_template_key = ordered_slide_files[3]
metric_template_xml = src_members[metric_template_key]


def make_metric_slide(metric):
    """Clone metric template and fill in metric content."""
    root = etree.fromstring(metric_template_xml)
    sp_tree = root.find(f".//{_q(NS_P, 'spTree')}")

    # Fill title placeholder
    for sp in sp_tree.iter(_q(NS_P, "sp")):
        txBody = sp.find(_q(NS_P, "txBody"))
        if txBody is None:
            continue
        curr = "".join(t.text or "" for t in txBody.iter(_q(NS_A, "t")))
        if "Proposed Metric" in curr and "Title" in (
            sp.find(f".//{_q(NS_P, 'cNvPr')}") or etree.Element("x")
        ).get("name", ""):
            for t_el in txBody.iter(_q(NS_A, "t")):
                t_el.text = ""
            # Set first text
            t_el = txBody.find(f".//{_q(NS_A, 't')}")
            if t_el is not None:
                t_el.text = metric["title"]
        # Main content box
        if "Technical Area:" in curr or "Description:" in curr:
            sp.remove(txBody)
            new_txBody = make_txbody(metric["content"].split("\n"), font_pt=9)
            sp.append(new_txBody)
        # Clear instructions
        if "Each proposed metric is limited to one slide" in curr:
            sp.remove(txBody)
            sp.append(make_txbody([""], 9))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


# ──────────────────────────────────────────────────────────────────────────────
# Assemble final pptx: slide1=TA1, slide2-5=4 metrics
# ──────────────────────────────────────────────────────────────────────────────

# Get metric template rels
metric_rels_src = metric_template_key.replace("slides/slide", "slides/_rels/slide").replace(".xml", ".xml.rels")

# Build new slide list: TA1 + 4 metrics
new_slides = [
    ("slide1.xml", etree.tostring(ta1_root, xml_declaration=True, encoding="UTF-8", standalone=True),
     ordered_slide_files[1].replace("ppt/slides/", "").replace(".xml", "")),  # layout source
]
for i, m in enumerate(METRICS):
    slide_name = f"slide{i+2}.xml"
    content = make_metric_slide(m)
    new_slides.append((slide_name, content, "metric"))

# Get the layout rels for TA1 and metric slides from original
ta1_rels_key = ta1_key.replace("slides/slide", "slides/_rels/slide").replace(".xml", ".xml.rels")
ta1_rels = src_members.get(ta1_rels_key, b"")
metric_rels = src_members.get(metric_rels_src, b"")

# Build rels for each new slide
slide_rels_map = {
    "slide1.xml": ta1_rels,
    "slide2.xml": metric_rels,
    "slide3.xml": metric_rels,
    "slide4.xml": metric_rels,
    "slide5.xml": metric_rels,
}

# Build new presentation.xml pointing to slide1-5
# Use the TA1 and metric template rIds as template
prs_rels_root = etree.fromstring(src_members["ppt/_rels/presentation.xml.rels"])
# Find TA1 rId and metric rId
ta1_rId = None
metric_rId = None
for rel in prs_rels_root:
    tgt = rel.get("Target", "")
    if ta1_key.replace("ppt/", "../") in tgt or "slide3.xml" in tgt:
        ta1_rId = rel.get("Id")
    if metric_template_key.replace("ppt/", "../") in tgt or "slide5.xml" in tgt:
        metric_rId = rel.get("Id")

print(f"  TA1 rId in template: {ta1_rId}")
print(f"  Metric template rId: {metric_rId}")

# Build new prs rels with 5 slide entries
new_prs_rels_root = deepcopy(prs_rels_root)
# Remove existing slide rels
for rel in list(new_prs_rels_root):
    if "slides/slide" in rel.get("Target", ""):
        new_prs_rels_root.remove(rel)

# Add new slide rels
ns_pr = "http://schemas.openxmlformats.org/package/2006/relationships"
slide_rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
max_rid = max(int(r.get("Id", "rId0")[3:]) for r in new_prs_rels_root) + 1

new_slide_rids = []
for i, (slide_fname, _, _) in enumerate(new_slides):
    rId = f"rId{max_rid + i}"
    new_slide_rids.append(rId)
    rel = etree.SubElement(new_prs_rels_root, "Relationship")
    rel.set("Id", rId)
    rel.set("Type", slide_rel_type)
    rel.set("Target", f"slides/{slide_fname}")

new_prs_rels_xml = etree.tostring(new_prs_rels_root, xml_declaration=True, encoding="UTF-8", standalone=True)

# Build new presentation.xml sldIdLst
new_prs_root = deepcopy(prs_xml)
new_sldIdLst = new_prs_root.find(_q(NS_P, "sldIdLst"))
if new_sldIdLst is None:
    new_sldIdLst = etree.SubElement(new_prs_root, _q(NS_P, "sldIdLst"))
# Clear existing
for child in list(new_sldIdLst):
    new_sldIdLst.remove(child)
# Add new
for i, rId in enumerate(new_slide_rids):
    sld_id = etree.SubElement(new_sldIdLst, _q(NS_P, "sldId"))
    sld_id.set("id", str(300 + i))
    sld_id.set(_q(NS_R, "id"), rId)

new_prs_xml = etree.tostring(new_prs_root, xml_declaration=True, encoding="UTF-8", standalone=True)

# ── Write final zip ──
with zipfile.ZipFile(X_OUT, "w", zipfile.ZIP_DEFLATED) as zout:
    # Copy all non-slide, non-prs-rels files
    skip_patterns = ["ppt/slides/", "ppt/slides/_rels/", "ppt/_rels/presentation.xml.rels",
                     "ppt/presentation.xml"]
    for name, data in src_members.items():
        skip = False
        for pat in skip_patterns:
            if name.startswith(pat) and name != pat:
                skip = True
                break
        if name in ("ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"):
            skip = True
        if not skip:
            zout.writestr(name, data)

    # Write new presentation files
    zout.writestr("ppt/presentation.xml", new_prs_xml)
    zout.writestr("ppt/_rels/presentation.xml.rels", new_prs_rels_xml)

    # Write new slide XMLs
    for slide_fname, slide_data, _ in new_slides:
        zout.writestr(f"ppt/slides/{slide_fname}", slide_data)
        # Write rels
        rels_data = slide_rels_map.get(slide_fname, b"")
        if rels_data:
            zout.writestr(f"ppt/slides/_rels/{slide_fname}.rels", rels_data)

print(f"\nWrote clean pptx: {X_OUT}")
print(f"  Slides: {len(new_slides)}")
for i, (fname, _, _) in enumerate(new_slides):
    label = "TA1 overview" if i == 0 else f"Metric {i}: {METRICS[i-1]['title'][:40]}"
    print(f"  [{i+1}] {fname} — {label}")
