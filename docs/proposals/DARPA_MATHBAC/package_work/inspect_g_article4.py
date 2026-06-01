"""Inspect Article 4 POC section in G docx to find exact placeholder text."""
import docx

G = (
    "docs/proposals/DARPA_MATHBAC/package_work/07_attachment_g_model_ot/"
    "Attachment_G_SCBE_FILLED.docx"
)
doc = docx.Document(G)

BLUE = "00B0F0"

def is_blue(run):
    try:
        return run.font.color.rgb and str(run.font.color.rgb) == BLUE
    except Exception:
        return False

in_range = False
for idx, para in enumerate(doc.paragraphs):
    t = para.text or ""
    # Enter article 4 region
    if "Article 4" in t or "AGREEMENT ADMINISTRATION" in t.upper():
        in_range = True
    # Exit region at Article 5
    if in_range and ("Article 5" in t or "OBLIGATION" in t.upper() or "PAYMENT" in t.upper()):
        in_range = False

    if in_range:
        # Print all paragraphs and flag blue runs
        blue_runs = [f"[{r.text!r}]" for r in para.runs if is_blue(r) and r.text.strip()]
        if t.strip() or blue_runs:
            print(f"P{idx:03d}: {t[:120]!r}")
            if blue_runs:
                print(f"  BLUE: {' '.join(blue_runs)}")
