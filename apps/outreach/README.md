# Aethermoor Outreach

AI-powered civic and business workflow engine for Port Angeles, WA.

**This is an assistive interface, not an official government agent.**
Human review is required on all outbound communication.

## Quick Start

From the repo root (`C:\Users\issda\SCBE-AETHERMOORE`):

```bash
python apps/outreach/run.py
```

This single command:
1. Creates the SQLite database (`apps/outreach/outreach.db`)
2. Seeds routing targets (11 real agencies with verified contact info)
3. Loads opportunity profiles (4 Port Angeles areas)
4. Starts FastAPI on `http://127.0.0.1:8300`

Then open your browser to **http://127.0.0.1:8300**

## Requirements

- Python >= 3.11
- `pip install fastapi uvicorn sqlalchemy`

(These are already in the SCBE-AETHERMOORE project dependencies.)

## What It Does

### Intent Classification
Submit what you want to do in plain language. The system classifies it into:
- **start_business** -- LLC, sole prop, corporation formation
- **permit_inquiry** -- building permits, zoning, land use
- **grant_discovery** -- grants, loans, financial assistance
- **patent_filing** -- patents, trademarks, IP protection
- **general_inquiry** -- anything else

### Workflow Generation
Based on your classified intent, you get a step-by-step workflow with:
- Real agencies and departments
- Estimated timelines
- Required documents
- Actual costs (fees accurate as of 2026)

### Location Opportunity Profiles
Select your area of Port Angeles to see:
- Commercial rent ranges
- Competition level
- Business type opportunities
- Key highlights and challenges
- Local contacts

### Document Generation
Generate ready-to-customize templates:
- Business plan summaries
- Permit inquiry letters
- Grant inquiry emails
- Invention disclosure forms
- General inquiry emails

### Routing
Get contact info for the right agencies:
- Phone numbers (verified)
- Email addresses
- Office hours
- Websites

### Case Tracking
Every intake creates a tracked case with:
- Workflow progress
- Generated documents
- Timeline of events
- Notes and updates

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/intake` | Submit intent |
| GET | `/api/intake/{id}` | Get project details |
| POST | `/api/intent/compile` | Classify intent text |
| GET | `/api/locations` | List location areas |
| GET | `/api/locations/{loc}/opportunity` | Get opportunity profile |
| POST | `/api/documents/generate` | Generate a document |
| GET | `/api/documents/types` | List document types |
| POST | `/api/routing/recommend` | Get routing targets |
| GET | `/api/routing/targets` | List all routing targets |
| POST | `/api/messages/draft` | Draft outreach message |
| POST | `/api/cases` | Create a case |
| GET | `/api/cases/{id}` | Get case details |
| POST | `/api/cases/{id}/events` | Add event to case |
| GET | `/api/dashboard` | All projects summary |
| GET | `/api/intents` | List intent categories |

Interactive API docs at: `http://127.0.0.1:8300/docs`

## Project Structure

```
apps/outreach/
  run.py                    # Single-command launcher
  outreach.db               # SQLite database (created on first run)
  README.md                 # This file
  backend/
    __init__.py
    main.py                 # FastAPI app with all endpoints
    models.py               # SQLAlchemy models (7 tables)
    services/
      __init__.py
      intent.py             # Intent classification
      workflow.py           # Workflow generation (Port Angeles specific)
      documents.py          # Document template generation
      routing.py            # Agency routing targets
      opportunity.py        # Location opportunity profiles
  frontend/
    index.html              # Single-page app (vanilla JS, dark theme)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTREACH_HOST` | `127.0.0.1` | Server bind address |
| `OUTREACH_PORT` | `8300` | Server port |

## Data Accuracy

All contact information, phone numbers, addresses, and fee amounts are for
Port Angeles, WA and Clallam County as of early 2026. Users should verify
current hours and fees before acting on this information.

## Compliance

- This tool is labeled as an "assistive interface" throughout
- It is not an official government agent or legal advisor
- All outbound messages are generated as drafts requiring human review
- No messages are sent automatically
