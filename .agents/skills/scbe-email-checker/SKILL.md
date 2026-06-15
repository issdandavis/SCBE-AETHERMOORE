---
name: scbe-email-checker
description: Check ProtonMail and Gmail for important emails — patent updates, revenue notifications, outreach replies, security alerts. Use when asked to "check email", "check my inbox", "any new emails", "patent email", "check proton", "check gmail", or at session start for a quick email briefing.
---

# SCBE Email Checker

Check ProtonMail (via Bridge IMAP) and Gmail (via IMAP) for important emails without leaving the terminal.

## When to Use

- User says "check email", "check inbox", "any emails", "check proton", "check gmail"
- Daily patent check (USPTO follow-ups)
- Revenue monitoring (Stripe, Shopify, Gumroad receipts)
- Outreach replies (NIST, CISA, collaborators)
- Security alerts (GitHub, npm, Dependabot)
- Session start briefing

## Accounts

| Account | Protocol | Host | Port | Username |
|---------|----------|------|------|----------|
| ProtonMail | IMAP (Bridge) | 127.0.0.1 | 1143 | issdandavis@proton.me |
| Gmail | IMAP SSL | imap.gmail.com | 993 | issdandavis7795@gmail.com |

Aliases on same ProtonMail account: `aethermoregames@pm.me`, `issdandavis@protonmail.com`

## Credentials

Load from `config/connector_oauth/.env.connector.oauth`:
- `PROTONMAIL_BRIDGE_PASSWORD` — Bridge-generated password (NOT Proton login)
- `PROTONMAIL_USER` — defaults to `issdandavis@proton.me`
- `GMAIL_APP_PASSWORD` — Google App Password (NOT Google login)
- `GMAIL_USER` — defaults to `issdandavis7795@gmail.com`

ProtonMail Bridge must be running locally for IMAP to work.
Gmail requires an App Password (generate at https://myaccount.google.com/apppasswords).

## Workflow

### Step 1: Load credentials

```python
import os
env_path = "config/connector_oauth/.env.connector.oauth"
for line in open(env_path).read().splitlines():
    if line.strip() and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
```

### Step 2: Connect to ProtonMail via Bridge

```python
import imaplib
mail = imaplib.IMAP4("127.0.0.1", 1143)
mail.login(os.environ["PROTONMAIL_USER"], os.environ["PROTONMAIL_BRIDGE_PASSWORD"])
mail.select("INBOX")
```

### Step 3: Connect to Gmail via IMAP SSL

```python
gmail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
gmail.login(os.environ.get("GMAIL_USER", "issdandavis7795@gmail.com"), os.environ["GMAIL_APP_PASSWORD"])
gmail.select("INBOX")
```

### Step 4: Search for important emails

Priority search terms (run against both accounts):

```python
PRIORITY_SEARCHES = [
    # Patent
    ("USPTO", 'FROM "uspto.gov"'),
    ("Patent EBC", 'FROM "ebc@uspto.gov"'),
    ("Patent AAU", 'FROM "HelpAAU@uspto.gov"'),
    # Revenue
    ("Stripe", 'FROM "stripe.com"'),
    ("Shopify", 'FROM "shopify.com"'),
    ("Gumroad", 'FROM "gumroad.com"'),
    # Outreach
    ("NIST", 'FROM "nist.gov"'),
    ("CISA", 'FROM "cisa.gov"'),
    # Security
    ("GitHub Security", 'FROM "noreply@github.com" SUBJECT "security"'),
    ("npm Advisory", 'FROM "npm"'),
    # Recent (last 3 days)
    ("Recent Unread", '(UNSEEN SINCE {3_days_ago})'),
]
```

### Step 5: Display results

For each match, show:
- From, Subject, Date (one line per email)
- Flag anything from USPTO, Stripe, or outreach contacts as HIGH PRIORITY
- Count unread messages

### Step 6: Patent-specific check

If user asks about patent specifically, run the full patent check:
```bash
python scripts/system/daily_patent_check.py --check-email
```

## Important Notes

- NEVER display full email bodies (copyright + privacy)
- Show From/Subject/Date only — enough to know what's there
- ProtonMail Bridge must be running (check: `Get-Process bridge`)
- Gmail App Password is NOT the Google account password
- If Bridge is not running, skip ProtonMail and report that it's down
- If Gmail creds are missing, skip Gmail and report what's needed

## Output Format

```
EMAIL CHECK — 2026-03-26
========================================
PROTONMAIL (issdandavis@proton.me):
  [HIGH] USPTO — "AIA/122 form" from ebc@uspto.gov (Mar 26)
  [new]  3 unread messages

GMAIL (issdandavis7795@gmail.com):
  [new]  GitHub — "Security alert" from noreply@github.com (Mar 25)
  [new]  7 unread messages

PATENT STATUS: Waiting (5 biz days from Mar 26 → follow up Apr 2)
========================================
```

## Quick Test

```bash
python scripts/system/daily_patent_check.py --check-email
```
