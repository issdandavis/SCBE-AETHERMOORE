# SAM.gov Get Opportunities API Reference

Last updated: 2026-04-09  
Status: operational reference for the public opportunities search lane

## Purpose

This file captures the minimum official rules needed to operate the SCBE SAM.gov ingestion lane without relying on chat history.

Canonical runtime surfaces for this lane:

- `api/darpa_prep/client.py`
- `scripts/sam_gov_ingest.py`
- `config/research/source_registry.json`

Official public documentation source:

- `https://open.gsa.gov/api/get-opportunities-public-api/`

## Endpoint

Production v2 search endpoint:

- `https://api.sam.gov/opportunities/v2/search`

Alpha endpoint:

- `https://api-alpha.sam.gov/opportunities/v2/search`

## Required Request Rules

- `api_key` is required.
- `postedFrom` is required.
- `postedTo` is required.
- `postedFrom` and `postedTo` must use `MM/dd/yyyy` format.
- The date range between `postedFrom` and `postedTo` must not exceed 1 year.
- `limit` must be numeric and within `0-1000`.
- `offset` must be numeric and non-negative.

## Useful Request Parameters

- `title` - best current general-text search field for SCBE opportunity discovery.
- `ptype` - notice type filter.
- `solnum` - solicitation number.
- `noticeid` - specific notice identifier.
- `organizationName` - department or subtier general search.
- `state` / `zip` - place-of-performance filters.
- `typeOfSetAside` - set-aside filter.
- `ncode` - NAICS code.
- `ccode` - classification code.
- `rdlfrom` / `rdlto` - response deadline range.
- `status` - documented as coming soon in the official page; do not make it a hard dependency in local tooling.

## Procurement Type Values

Documented `ptype` values:

- `u` - Justification (J&A)
- `p` - Pre-solicitation
- `a` - Award Notice
- `r` - Sources Sought
- `s` - Special Notice
- `o` - Solicitation
- `g` - Sale of Surplus Property
- `k` - Combined Synopsis/Solicitation
- `i` - Intent to Bundle Requirements (DoD-funded)

## Response Fields Worth Preserving

When normalizing a SAM.gov result, preserve these if present:

- `title`
- `solicitationNumber`
- `fullParentPathName`
- `fullParentPathCode`
- `postedDate`
- `type`
- `baseType`
- `archiveDate`
- `setAside`
- `setAsideCode`
- `responseDeadLine`
- `naicsCode`
- `classificationCode`
- `active`
- `description`
- `uiLink`
- `resourceLinks`
- `pointOfContact`
- `placeOfPerformance`
- `data.award`

## Current SCBE Client Behavior

The local client currently uses:

- `title`
- `api_key`
- `postedFrom`
- `postedTo`
- `limit`
- `offset`

This matches the mandatory rules from the official documentation and keeps the search lane simple and deterministic.

Current implementation note:

- the local client defaults to a 180-day posted-date window to stay well inside the 1-year maximum and avoid avoidable request failures.

## Shell Usage

Set the key in the current shell, then run the helper:

```powershell
$env:SAM_GOV_API_KEY="<your-key>"
python .\scripts\sam_gov_ingest.py "DARPA" --limit 5
```

Optional file output:

```powershell
python .\scripts\sam_gov_ingest.py "artificial intelligence" --limit 10 --output artifacts\sam_gov\ai_query.json
```

## Error Conditions to Expect

Important documented API errors:

- `No api_key was supplied`
- `An invalid api_key was supplied`
- `PostedFrom and PostedTo are mandatory`
- `Invalid Date Entered. Expected date format is MM/dd/yyyy`
- `Date range must be 1 year(s) apart`
- `limit/offset must be a positive number.`
- `Limit valid range is 0-1000. Please provide valid input.`

## Operating Rule

Treat SAM.gov public API results as:

- `public`
- `publishable`
- `allowed_public_training`

But treat authenticated account views and account-only registration pages separately through the ingestion-rights classifier.
