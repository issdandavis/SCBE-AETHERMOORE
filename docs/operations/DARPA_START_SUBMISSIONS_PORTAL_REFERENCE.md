# DARPA Start Submissions Portal Reference

Last updated: 2026-04-09  
Status: internal operational reference for the DARPA BAA submission dashboard

## Canonical URL

- `https://baa.darpa.mil/Submissions/StartSubmissions.aspx`

## Purpose

This page is the authenticated DARPA submission dashboard used to begin new submissions against currently open solicitations.

Treat this page as:

- `authorized_internal`
- `internal_only`
- `retrieval_only` by default

## What the Page Exposes

For each open solicitation, the page typically exposes:

- solicitation number
- office code
- public-facing title
- available submission entry types
- one or more submission deadlines
- whether proposal abstracts are encouraged
- whether a given deadline has already passed

## Submission Entry Types

The dashboard explicitly tells the operator to begin a new submission by selecting one of:

- `Submit Executive Summary`
- `Submit Proposal Abstract`
- `Submit Full Proposal`

Not every solicitation exposes all three.

## Known Deadline Fields

The page can expose the following deadline fields:

- `Executive Summary Deadline (ET)`
- `Proposal Abstract Deadline (ET)`
- `Full Proposal Initial Close Deadline (ET)`
- `Full Proposal Final Deadline (ET)`

It can also mark records with:

- `Submission Deadline Passed`
- `Requires an encouraged Proposal Abstract`

## Current SCBE Handling

The parser route for this page is:

- `POST /v1/opportunities/darpa-portal/parse`

Relevant runtime surfaces:

- `api/darpa_prep/darpa_portal.py`
- `api/darpa_prep/routes.py`

Use the parser when you have copied page text from the authenticated dashboard and want to convert it into structured opportunity records for internal ranking, deadline tracking, and proposal-prep workflows.
