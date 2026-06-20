# Polly lead email — SMTP wire-up

The `polly-training-capture` workflow emails leads via plain SMTP when the
following GitHub repo secrets are set. If any of `POLLY_LEAD_SMTP_HOST` /
`POLLY_LEAD_SMTP_USER` / `POLLY_LEAD_SMTP_PASS` is missing the email step bails
quietly and the only signal channels remain the auto-filed GitHub issue + the
private HF dataset row.

## Required secrets

| Secret | Purpose |
|---|---|
| `POLLY_LEAD_SMTP_HOST` | SMTP server hostname |
| `POLLY_LEAD_SMTP_PORT` | optional, defaults to `587` (STARTTLS); use `465` for implicit TLS |
| `POLLY_LEAD_SMTP_USER` | SMTP username |
| `POLLY_LEAD_SMTP_PASS` | SMTP password (or app password) |
| `POLLY_LEAD_SMTP_FROM` | optional, defaults to `POLLY_LEAD_SMTP_USER` |
| `POLLY_LEAD_SMTP_TO` | optional, defaults to `POLLY_LEAD_SMTP_USER` |

Set them with `gh secret set POLLY_LEAD_SMTP_HOST` etc., or via the repo
Settings → Secrets and variables → Actions UI.

## Provider configurations

### Proton Mail (Plus / Pro / Business)

Bridge runs locally and only listens on `127.0.0.1`, so a hosted GitHub
runner can't reach it. You have two viable paths:

1. **Proton SMTP submission** (cleanest, no local infra):
   - `POLLY_LEAD_SMTP_HOST = smtp.protonmail.ch`
   - `POLLY_LEAD_SMTP_PORT = 587`
   - `POLLY_LEAD_SMTP_USER = your-bridge-issued-username` (find it in
     Bridge → Mailbox details → SMTP)
   - `POLLY_LEAD_SMTP_PASS = your-bridge-issued-password`
   - `POLLY_LEAD_SMTP_FROM = you@protonmail.com`
   - `POLLY_LEAD_SMTP_TO = wherever-you-want-leads-delivered`

2. **Local Bridge via Cloudflare Tunnel** (uses real Bridge):
   - Run `cloudflared tunnel --url smtp://127.0.0.1:1025` on the machine that
     has Bridge installed. Cloudflare Tunnel issues a public hostname.
   - `POLLY_LEAD_SMTP_HOST = the-tunnel-hostname`
   - `POLLY_LEAD_SMTP_PORT = 1025` (or whichever Bridge exposes)
   - The Bridge-issued SMTP user/pass you'd otherwise paste into
     Thunderbird.

### Gmail (App Passwords)

- Enable 2FA on the Google account.
- Visit <https://myaccount.google.com/apppasswords> → generate "Mail" → 16-char
  app password.
- Settings:
  - `POLLY_LEAD_SMTP_HOST = smtp.gmail.com`
  - `POLLY_LEAD_SMTP_PORT = 587`
  - `POLLY_LEAD_SMTP_USER = you@gmail.com`
  - `POLLY_LEAD_SMTP_PASS = the-16-char-app-password`

### Mailgun (free tier)

- Sign up, verify a domain.
- Settings → Domain → SMTP credentials.
- Settings:
  - `POLLY_LEAD_SMTP_HOST = smtp.mailgun.org`
  - `POLLY_LEAD_SMTP_PORT = 587`
  - `POLLY_LEAD_SMTP_USER = postmaster@yourdomain`
  - `POLLY_LEAD_SMTP_PASS = the-domain-smtp-password`

### SendGrid (free tier)

- API → SMTP Relay.
- Settings:
  - `POLLY_LEAD_SMTP_HOST = smtp.sendgrid.net`
  - `POLLY_LEAD_SMTP_PORT = 587`
  - `POLLY_LEAD_SMTP_USER = apikey`
  - `POLLY_LEAD_SMTP_PASS = your-sendgrid-api-key`

## Email shape

Each lead-triggered email has:

- Subject: `[polly lead] <project_type> - <budget> - <timeline>`
- Reply-To: the contact field from the lead (so a single reply goes back to
  the prospect)
- Body: contact / project / budget / timeline / source / description, plus a
  pointer to the private HF dataset row

PII is in the email body and the HF dataset only. The companion GitHub issue
(see `polly-training-capture.yml`) deliberately omits contact + description.

## Smoke test

After setting secrets:

1. Submit a test lead via <https://aethermoore.com/SCBE-AETHERMOORE/hire.html>
2. Watch the workflow run at
   <https://github.com/issdandavis/SCBE-AETHERMOORE/actions/workflows/polly-training-capture.yml>
3. Check the inbox you set as `POLLY_LEAD_SMTP_TO`
4. If the workflow shows "SMTP credentials missing" — your secrets aren't set
   yet
5. If the workflow shows an SMTP error — auth almost always; double-check the
   provider's app-password vs account-password requirement
