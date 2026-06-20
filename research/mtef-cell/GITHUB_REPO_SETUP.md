# GitHub Setup Notes

This package was originally prepared as a standalone repository named `mtef-cell`, but the available GitHub connector could not create a new repository directly.

It has therefore been staged inside the existing repository at:

```text
research/mtef-cell/
```

## Recommended long-term paths

### Option A — keep nested inside SCBE-AETHERMOORE

Use this if M-TEF remains part of the broader Aethermoore research vault.

Pros:

- easy to keep with other research packets
- no new repository overhead
- can link to SCBE governance / evaluation infrastructure later

Cons:

- hardware work may get buried inside a large AI/security repo
- CI and project identity are less clean

### Option B — split into a standalone repo later

Use this if M-TEF becomes a hardware/product track.

Suggested repo name:

```text
mtef-cell
```

Suggested command after creating an empty GitHub repo manually:

```bash
git subtree split --prefix=research/mtef-cell -b split-mtef-cell
git push https://github.com/issdandavis/mtef-cell.git split-mtef-cell:main
```

## Publication warning

Because this repository is public, do not add confidential invention disclosures, signed forms, SSNs/TINs, private addresses, or patent-sensitive claim language unless you intentionally want it public.
