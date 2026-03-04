# Email AI Backboard Router - Setup Guide

## Overview
Email AI Backboard router enables email-triggered AI workflows with self-healing CI/CD capabilities.

## Architecture
```
ProtonMail Inbox
    ↓
ProtonMail Bridge (IMAP)
    ↓
email-router.py (Python)
    ↓
Google AI Studio (Gemini Knight) - Classification
    ↓
Routing Decision (YAML)
    ↓
Specialized AI Knights:
  • Gemini Knight → User summaries
  • Lumo Architect → Constraint checking
  • Workflow Healer → CI/CD self-healing
    ↓
Cloud Storage (ProtonDrive/S3) - Audit logs
```

## Prerequisites
1. **ProtonMail Bridge** installed and running
2. **Google AI Studio** account with API key
3. **Python 3.8+** with packages:
   ```bash
   pip install imaplib email google-generativeai boto3 pyyaml
   ```
4. **Cloud storage** configured (ProtonDrive or AWS S3)

## Configuration

### 1. ProtonMail Bridge Setup
```bash
# Install ProtonMail Bridge
# https://proton.me/mail/bridge

# Get credentials from Bridge:
# - IMAP server: 127.0.0.1:1143
# - Username: your@protonmail.com
# - Password: [Bridge-generated password]
```

### 2. Environment Variables
Create `.env` file:
```bash
# ProtonMail
PROTONMAIL_HOST=127.0.0.1
PROTONMAIL_PORT=1143
PROTONMAIL_USER=your@protonmail.com
PROTONMAIL_PASS=bridge_password_here

# Google AI Studio
GOOGLE_AI_API_KEY=your_gemini_api_key
GOOGLE_AI_STUDIO_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/models/{GOOGLE_AI_STUDIO_MODEL}:generateContent
GOOGLE_AI_STUDIO_MODEL=gemini-1.5-flash

# Cloud Storage
STORAGE_TYPE=s3  # or 'protondrive'
AWS_BUCKET=ai-workflow-backboard
AWS_REGION=us-east-2

# Reply-to address
REPLY_TO_ADDRESS=your@protonmail.com
```

### 3. Google AI Studio Email Routing Engine
Create app in Google AI Studio:
- Name: "Email AI Routing Engine"
- Model: Gemini 1.5 Flash
- System instruction: See email-router.py `classify_email()` function

## Usage

### Run Router
```bash
python email-router.py
```

### Test Email Workflow
Send test email to monitored ProtonMail:
```
To: project@aiworkflow.app
Subject: workflow_failure
Body: CI pipeline failed in repository AI-Workflow-Architect.01.01.02
```

Expected routing:
```yaml
target: workflow_healer
action: diagnose_and_fix
context:
  repository: AI-Workflow-Architect.01.01.02
  error_type: ci_pipeline
```

## Integration with Workflow Healer

Email router triggers self-healing workflows:
1. Receives email notification from GitHub Actions
2. Classifies with Gemini Knight
3. Routes to Workflow Healer Knight
4. Healer analyzes logs and fixes issue
5. Stores decision audit in cloud
6. Sends summary back via email

## Monitoring

Audit logs stored in cloud:
```
AI_Workflow_Architect/Audit/log_YYYYMMDD.json
```

## Next Steps
1. Deploy to production server
2. Set up systemd service for auto-restart
3. Configure ProtonMail filters to forward workflow emails
4. Connect Zapier agents for extended automation
5. Integrate with GitHub Actions webhooks

## 6 Sacred Languages Protocol

This router uses the 6-language AI communication protocol:
- **AXIOM**: Status declarations
- **FLOW**: Execution sequences
- **GLYPH**: Data structures
- **ORACLE**: Predictions and next actions
- **CHARM**: Coordination messages
- **LEDGER**: Audit trails

## Support
Contact: Lumo AI (lumo.proton.me)
GitHub: issdandavis/AI-Workflow-Architect.01.01.02
