"""
alphafold_gate.py — AlphaFold EBI REST API integration for the drug-discovery
answer-space probe (prime_fog_of_war_probe.py).

Provides trit[6]: the structure-quality gate.
  trit=0 (fail):      No AF entry found, or mean pLDDT < 50 (predicted disordered)
  trit=1 (near-miss): Mean pLDDT 50-70 (low-confidence fold — cliff edge)
  trit=2 (pass):      Mean pLDDT ≥ 70 (confident fold — valid binding geometry)

API surface (AlphaFold EBI, no authentication required):

  Prediction metadata (JSON):
    GET https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}
    Returns: list[dict] with fields:
      entryId, gene, uniprotAccession, uniprotId, uniprotDescription,
      taxId, organismScientificName, uniprotStart, uniprotEnd,
      uniprotSequence, modelCreatedDate, latestVersion,
      allVersions, isReviewed, isReferenceProteome,
      cifUrl, bcifUrl, pdbUrl, paeImageUrl, paeDocUrl,
      confidenceUrl  ← the per-residue pLDDT JSON

  Per-residue pLDDT (JSON):
    GET {confidenceUrl}   (e.g. .../AF-P00520-F1-confidence_v4.json)
    Returns: {"residueNumber": [...], "confidenceScore": [...], "confidenceCategory": [...]}

  Structure file (PDB):
    GET {pdbUrl}   (plain text PDB format)

  Structure file (mmCIF):
    GET {cifUrl}

Usage in the probe:
    from scripts.research.alphafold_gate import alphafold_plddt_trit, alphafold_lookup

Example:
    result = alphafold_lookup("P00533")  # EGFR
    print(result["mean_plddt"], result["trit"])

Note on your geometry / wavelength observation:
  When a protein folds, it moves from a 1D amino-acid sequence (a linear axis, like
  the MW axis) into a 3D geometric object. The pLDDT score is the confidence that
  this *fold transition* succeeded. A low-pLDDT region is "rising in wavelength" —
  the chain is unstructured, sampling many geometries. A high-pLDDT region is "fallen
  back" into one stable geometry (one wavelength, one binding-pocket shape).
  The cliff at pLDDT=70 is the transition point: below it, the fold is still
  superposing over multiple geometries (near-miss); above it, it has collapsed to one.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


_ALPHAFOLD_BASE = "https://alphafold.ebi.ac.uk/api"
_TIMEOUT_S = 10


def _get_json(url: str) -> Any:
    """HTTP GET with 10s timeout, returns parsed JSON or raises."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}: {url}") from e


def alphafold_lookup(uniprot_id: str) -> dict:
    """Fetch AlphaFold prediction metadata + mean pLDDT for a UniProt accession.

    Returns a dict with:
      uniprot_id        — the queried accession
      entry_id          — AF entry ID (e.g. "AF-P00533-F1")
      gene              — gene name
      organism          — scientific name
      model_version     — latest model version number
      pdb_url           — direct PDB download URL
      confidence_url    — per-residue pLDDT JSON URL
      mean_plddt        — float, mean per-residue pLDDT (0-100)
      residue_count     — number of residues with pLDDT data
      high_confidence_frac — fraction of residues with pLDDT ≥ 70
      trit              — 0/1/2 gate value (see module docstring)
      trit_label        — "fail" / "near-miss" / "pass"
      error             — None or error message string (if lookup failed)
    """
    result: dict = {
        "uniprot_id": uniprot_id,
        "entry_id": None,
        "gene": None,
        "organism": None,
        "model_version": None,
        "pdb_url": None,
        "confidence_url": None,
        "mean_plddt": None,
        "residue_count": None,
        "high_confidence_frac": None,
        "trit": 0,
        "trit_label": "fail",
        "error": None,
    }
    try:
        url = f"{_ALPHAFOLD_BASE}/prediction/{uniprot_id}"
        data = _get_json(url)
        if not data:
            result["error"] = "empty response"
            return result
        entry = data[0] if isinstance(data, list) else data
        entry_id = entry.get("entryId")  # e.g. "AF-P00533-F1"
        result["entry_id"] = entry_id
        result["gene"] = entry.get("gene")
        result["organism"] = entry.get("organismScientificName")
        model_ver = entry.get("latestVersion") or 4
        result["model_version"] = model_ver
        result["pdb_url"] = entry.get("pdbUrl")

        # Construct per-residue pLDDT URL directly from entry_id + version.
        # The paeDocUrl field points to the PAE matrix (inter-residue error),
        # NOT the per-residue pLDDT confidence JSON.  The correct pattern is:
        #   https://alphafold.ebi.ac.uk/files/{entry_id}-confidence_v{N}.json
        # where N matches the database version (4 for AF-DB v4, etc.).
        # We try the model version first, then fall back to v4 (the most common).
        base_url = "https://alphafold.ebi.ac.uk/files"
        candidate_urls = []
        if entry_id:
            candidate_urls.append(f"{base_url}/{entry_id}-confidence_v{model_ver}.json")
            if model_ver != 4:
                candidate_urls.append(f"{base_url}/{entry_id}-confidence_v4.json")
        confidence_url = None
        conf = None
        for curl in candidate_urls:
            try:
                conf = _get_json(curl)
                confidence_url = curl
                break
            except RuntimeError:
                pass
        result["confidence_url"] = confidence_url
        if conf is not None:
            # Per-residue pLDDT: dict-of-arrays or list-of-dicts format
            if isinstance(conf, dict):
                scores = conf.get("confidenceScore") or conf.get("plddt") or []
            elif isinstance(conf, list):
                # Each element is {"residueNumber": N, "confidenceScore": X, ...}
                scores = [
                    r.get("confidenceScore", r.get("plddt", 0))
                    for r in conf if isinstance(r, dict)
                ]
            else:
                scores = []
            if scores:
                n = len(scores)
                mean_plddt = sum(scores) / n
                high_frac = sum(1 for s in scores if s >= 70.0) / n
                result["mean_plddt"] = round(mean_plddt, 2)
                result["residue_count"] = n
                result["high_confidence_frac"] = round(high_frac, 4)
                trit = alphafold_plddt_trit(mean_plddt)
                result["trit"] = trit
                result["trit_label"] = ["fail", "near-miss", "pass"][trit]
    except RuntimeError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = f"unexpected: {e}"
    return result


def alphafold_plddt_trit(mean_plddt: float) -> int:
    """Gate 7 — AlphaFold structure quality (mean pLDDT).

    trit=0 (fail):      mean pLDDT < 50
      Predicted disordered: the chain samples multiple geometries simultaneously.
      No stable binding pocket geometry exists at this confidence level.
      pLDDT < 50 is a standard predictor of structural disorder (EBI training).

    trit=1 (near-miss): 50 ≤ mean pLDDT < 70
      Low-confidence fold: the geometry is partially resolved but not stable.
      This is the structure-space cliff — the molecule is 'rising in wavelength'
      (superposing over several geometries) but not yet collapsed to one.
      Docking predictions are possible but unreliable in this zone.
      Maps to the 'extended near-miss' zone in activity cliff research
      (arXiv:2302.07541, 2601.04507).

    trit=2 (pass):      mean pLDDT ≥ 70
      Confident fold: the structure has collapsed to a single geometry.
      'Fallen back' to one stable wavelength (one binding-pocket shape).
      Safe for docking and downstream ADME prediction.
      High-confidence residues (pLDDT ≥ 90) are suitable for crystallography-
      equivalent analysis.

    The cliff at pLDDT = 70 is the sharpest structural transition:
    below it, per-residue uncertainty exceeds the typical binding-pocket
    dimension (empirical EBI confidence-score guideline).
    """
    if mean_plddt < 50.0:
        return 0
    if mean_plddt < 70.0:
        return 1
    return 2


# ── Seed-compound UniProt target table ──────────────────────────────────────
# Maps compound name → representative target UniProt accession.
# Used for the seed-anchored pLDDT interpolation when no target is specified.
# Each compound is paired with its most common primary target.
SEED_TARGET_UNIPROT: dict[str, str] = {
    "caffeine":          "P00438",  # Adenosine A1 receptor
    "paracetamol":       "P00439",  # COX-1 (PTGS1)
    "glucose":           "P07550",  # Glucose transporter GLUT1 (SLC2A1)
    "sucrose":           "P19835",  # Sucrase-isomaltase (SI)
    "ascorbic_acid":     "P07327",  # SVCT2 (SLC23A2) — Vit-C transporter
    "aspirin":           "P35354",  # COX-2 (PTGS2)
    "hydrogen_peroxide": "P00722",  # Catalase (CAT)
    "ibuprofen":         "P35354",  # COX-2 (PTGS2)
    "metformin":         "P15127",  # AMPK alpha-1 (PRKAA1)
    "naproxen":          "P35354",  # COX-2 (PTGS2)
    "atorvastatin":      "P04035",  # HMG-CoA reductase (HMGCR)
    "omeprazole":        "P20648",  # H+/K+ ATPase alpha (ATP4A)
    "diazepam":          "P47869",  # GABA-A receptor alpha-1 (GABRA1)
    "warfarin":          "P00734",  # Prothrombin (F2) — warfarin blocks VK epoxide reductase
    "glycine":           "P23415",  # Glycine receptor alpha-1 (GLRA1)
}


def batch_seed_plddt() -> dict[str, dict]:
    """Fetch pLDDT data for all seed compound targets.

    Returns dict keyed by compound name → alphafold_lookup result.
    Network errors per compound are captured in result["error"].
    """
    results = {}
    for name, uniprot in SEED_TARGET_UNIPROT.items():
        results[name] = alphafold_lookup(uniprot)
    return results


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python alphafold_gate.py <UniProt accession> [...]")
        print("       python alphafold_gate.py --seeds   (batch seed-compound lookup)")
        sys.exit(1)

    if sys.argv[1] == "--seeds":
        print("Fetching pLDDT for all seed compound targets...\n")
        batch = batch_seed_plddt()
        print(f"  {'compound':<20}  {'uniprot':<10}  {'gene':<12}  {'mean pLDDT':>10}  {'frac≥70':>8}  {'trit':>5}")
        print("  " + "─" * 70)
        for name, r in batch.items():
            if r["error"]:
                print(f"  {name:<20}  {SEED_TARGET_UNIPROT[name]:<10}  ERROR: {r['error']}")
            else:
                print(
                    f"  {name:<20}  {r['uniprot_id']:<10}  {(r['gene'] or '?'):<12}  "
                    f"{r['mean_plddt']:>10}  {r['high_confidence_frac']:>8.2%}  "
                    f"{r['trit']:>5}  [{r['trit_label']}]"
                )
    else:
        for uid in sys.argv[1:]:
            r = alphafold_lookup(uid)
            print(json.dumps(r, indent=2))
