# DARPA CLARA Full Proposal Portal Submission Checklist

**Solicitation**: `DARPA-PA-25-07-02`  
**Program**: `Compositional Learning-And-Reasoning for AI Complex Systems Engineering (CLARA)`  
**Office**: `DSO`  
**Portal URL**: `https://baa.darpa.mil/Submissions/StartSubmissions.aspx`  
**Last updated**: `2026-04-09`

---

## Purpose

This file turns the authenticated DARPA BAA portal full-proposal form into an operator checklist for the SCBE CLARA submission lane.

Use it to:

- track what the portal requires before finalization
- keep portal-entry work aligned with the proposal packet already in `docs/proposals/DARPA_CLARA/`
- record the current blocker state without storing sensitive personal or financial data in repo files

---

## Current Submission Reality

- DARPA BAA portal access is working.
- The CLARA full proposal form can be opened.
- SAM.gov shows a `Submitted Registration` record for `ISSAC D DAVIS`.
- UEI is confirmed as `J4NXHM6N5F59`.
- **Current blocker**: `Activation Date` is blank and `CAGE/NCAGE` is blank.
- Until SAM.gov activation completes and the CAGE code is assigned, treat the CLARA full proposal finalization path as **blocked / not ready to submit**.

---

## Portal Timeout / Save Rules

- Save periodically if the form cannot be completed within `15 minutes`.
- The session times out on inactivity.
- Typing into fields alone may not count as activity.
- Do not wait until the upload/finalize step to save work.

---

## Full Proposal Form Fields

### Organization / cover-sheet section

- `Organization`
  - current portal value seen: `ISSAC D DAVIS`
- `Organization Type`
  - current portal value seen: `Small Business`
- `Submission Title`
- `Proposed Cost`
  - round to the nearest dollar
- `Duration In Months`

### Proposer Information

This is the technical point of contact lane, for example PI or program manager.

- `Salutation`
- `First Name`
- `Last Name`
- `Organization Name`
- `Country`
- `Address 1`
- `Address 2`
- `City`
- `State`
- `Zip/Postal Code`
  - portal requests full `9-digit ZIP`
- `Phone`
- `Fax`
- `Email`

### Authorized Representative

This is the contracting or grant-officer lane.

- `Salutation`
- `First Name`
- `Last Name`
- `Organization Name`
- `Country`
- `Address 1`
- `Address 2`
- `City`
- `State`
- `Zip/Postal Code`
  - portal requests full `9-digit ZIP`
- `Phone`
- `Fax`
- `Email`

### Team Members

- If there are no partner organizations, check:
  - `I do not have any team members.`
- If there are team members, the form requests:
  - `Organization Name`
  - `Division`
  - `Organization Type`
  - `Postal Code`

### Upload

- `Full Proposal Upload` is required.
- The portal expects a single `zip file` containing all files required by the solicitation.
- Do not finalize until the zip contents are verified against the compliance matrix and technical/cost packet.

### Program Manager awareness

- `ATTN: Program Manager` dropdown is optional.
- Use only when you are confident the selected PM is appropriate for the submission.

### Finalization

- `Finalize Full Proposal` makes the submission non-editable.
- Treat finalization as a one-way action.
- Do not click finalize until registration, upload package, and internal review checks are complete.

---

## Current Blocking Conditions

- [x] No CAGE code assigned yet
- [x] SAM.gov registration not fully active yet
- [ ] Portal confirms CLARA full proposal may proceed without CAGE / full activation
- [ ] Proposal zip package is complete and verified
- [ ] Authorized representative details are ready

If the first two boxes remain true, treat submission as blocked.

---

## Submission Packet Dependencies

These files are the current repo-backed packet for CLARA and should be reconciled before upload:

- `docs/proposals/DARPA_CLARA/02_CLARA_COMPLIANCE_MATRIX.md`
- `docs/proposals/DARPA_CLARA/03_WHITE_PAPER_OUTLINE.md`
- `docs/proposals/DARPA_CLARA/04_TECHNICAL_VOLUME_DRAFT.md`
- `docs/proposals/DARPA_CLARA/05_COST_WORKBOOK_NOTES.md`
- `docs/proposals/DARPA_CLARA/06_PM_RESEARCH_BENJAMIN_GROSOF.md`
- `docs/proposals/DARPA_CLARA/CLARA_ABSTRACT_1page.md`
- `docs/proposals/DARPA_CLARA/CLARA_ABSTRACT_v1.md`

---

## Help Contacts

### General / portal support

- General Help Desk email: `baat_support@darpa.mil`
- Help desk hours: `7:00 AM - 7:00 PM ET`, Monday-Friday
- Technical offices: `9:00 AM - 5:00 PM ET`

### Office-specific addresses

- `ACO`: `BAAT_Support@darpa.mil`
- `BTO`: `btobaahelp@darpa.mil`
- `DSO`: `baat_support@darpa.mil`
- `I2O`: `I2OBAAHelp@darpa.mil`
- `MTO`: `mtobaacoordinators@darpa.mil`
- `STO`: `baat_support@darpa.mil`
- `TTO`: `baat_support@darpa.mil`

For CLARA-specific questions, continue to keep `CLARA@darpa.mil` in the contact lane documented in `docs/operations/DARPA_SAM_GOV_CONTACTS_AND_PROPOSAL_STATUS.md`.

---

## Operator Rule

Do not treat portal access as proof that submission is ready. Submission readiness requires:

- active registration state
- CAGE code availability or confirmed alternate path
- a verified upload package
- internal consistency between cover-sheet data, technical volume, and cost material
