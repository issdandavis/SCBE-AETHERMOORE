# Patent Center DOCX Warning Response - 2026-05-29

## Trigger

Patent Center reported four review warnings after upload of the SCBE nonprovisional DOCX:

1. Paragraph numbering is missing from the specification.
2. There may be a lack of antecedent basis in the claims section.
3. At least one claim appears to contain a claim that references two sets of claims to different features.
4. The claims appear to contain an improper dependency with at least one claim that depends on a missing or canceled claim.

## Authority Checked

- MPEP 608.01(g): specification paragraphs other than claims or abstract may be numbered and should use at least four Arabic numerals enclosed in square brackets, e.g. [0001]. Section headers are not numbered.
- MPEP 608.01(n): dependent claims must refer back properly; multiple dependent claims must be in the alternative only, may not reference two sets of claims for different features, and may not depend directly or indirectly from another multiple dependent claim.
- MPEP 2173.05(e): lack of antecedent basis is an indefiniteness issue only when claim meaning is unclear; explicit antecedent basis issues are usually correctable drafting oversights.
- MPEP 2173.05(f): references to limitations in another claim are not automatically improper, but can be rejected where the reference format creates confusion.
- USPTO DOCX guidance: a single multi-section DOCX may contain specification, claims, and abstract for a utility nonprovisional initial filing.

## Edits Applied

### Paragraph numbering

The DOCX builder now emits [0001]-style paragraph numbers for the specification body, including cross-reference, background, summary, figure descriptions, and detailed description. Claims and abstract remain unnumbered.

### Claim dependency cleanup

Patent Center was likely flagging claim text that depended from one claim while referencing a second claim body:

- Claim 8 changed from depending on claim 1 while referencing claim 6 to depending directly from claim 6.
- Claim 21 no longer references claim 7; it restates the fail-to-noise hash/re-hash mechanism.
- Claim 22 no longer references claim 7; it restates deterministic re-hashing seeded by the content hash.

This avoids accidental multiple-dependency interpretation while preserving the technical substance.

## Local Verification

- Rebuilt `docs/legal/SCBE_NONPROVISIONAL_SPEC_v1.docx` from `docs/legal/build_patent_docx.py`.
- Copied rebuilt DOCX into `docs/legal/filing-packet-scbe-2026-0001/01_SUBMIT_THESE_TO_PATENT_CENTER/SCBE_NONPROVISIONAL_SPEC_v1.docx`.
- Verified 28 claims and independent claims 1, 9, and 15.
- Verified no claim references a missing or later claim.
- Verified no dependent claim contains extra claim references beyond its direct dependency.
- Verified 280 numbered specification paragraphs.
- Verified no paragraph numbers appear in claims or abstract.

## Remaining Filing Note

The currently uploaded Patent Center DOCX should be replaced with the rebuilt filing-packet DOCX before final submit/payment. The multi-section detection message is expected and consistent with USPTO DOCX guidance.
