# Firebase Setup Guide

Connect SCBE to Firebase Firestore for persistent audit logs, trust history, and alerts.

---

## Quick Setup (5 minutes)

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Create a project"
3. Name it `scbe-governance` (or your preference)
4. Disable Google Analytics (optional for this use case)
5. Click "Create project"

### Step 2: Enable Firestore

1. In Firebase Console, click "Build" → "Firestore Database"
2. Click "Create database"
3. Choose "Start in production mode"
4. Select your region (e.g., `us-central1`)
5. Click "Enable"

### Step 3: Get Service Account Key

1. Click the gear icon → "Project settings"
2. Go to "Service accounts" tab
3. Click "Generate new private key"
4. Download the JSON file
5. **Keep this file secure** - it grants full database access

### Step 4: Configure SCBE

**Option A: Environment Variable (Recommended)**

```bash
# Point to your downloaded JSON file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-firebase-key.json"

# Start the API
python -m uvicorn api.main:app --port 8080
```

**Option B: Inline JSON (for Docker/Serverless)**

```bash
# Paste the entire JSON content
export FIREBASE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"..."}'

# Start the API
python -m uvicorn api.main:app --port 8080
```

---

## Verify Connection

```bash
# Check health endpoint
curl http://localhost:8080/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "api": "ok",
    "pipeline": "ok",
    "firebase": "connected"
  }
}
```

---

## Firestore Collections

SCBE creates these collections automatically:

| Collection | Purpose | Retention |
|------------|---------|-----------|
| `scbe_audit_logs` | Immutable decision records | Configure in Firebase |
| `scbe_trust_history` | Agent trust scores over time | 90 days recommended |
| `scbe_agents` | Registered agent registry | Permanent |
| `scbe_alerts` | Alerts for webhooks/Zapier | 30 days recommended |

---

## Security Rules (Production)

Update Firestore security rules for production:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only allow server-side access (service account)
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

This blocks client-side access - only your API server can read/write.

---

## Cost Estimation

Firebase free tier includes:
- 50K reads/day
- 20K writes/day
- 1 GB storage

For a pilot with ~1000 decisions/day:
- Reads: ~3000/day (well under limit)
- Writes: ~2000/day (well under limit)
- **Cost: $0/month** on free tier

---

## Troubleshooting

### "Firebase credentials not configured"

```bash
# Check if environment variable is set
echo $GOOGLE_APPLICATION_CREDENTIALS

# Or check inline config
echo $FIREBASE_SERVICE_ACCOUNT_KEY | head -c 50
```

### "Permission denied"

1. Check Firestore is enabled in Firebase Console
2. Verify service account has "Cloud Datastore User" role
3. Check the JSON key file is valid

### "firebase_admin not found"

```bash
pip install firebase-admin google-cloud-firestore
```

---

## Next Steps

- [Zapier Integration](zapier-setup.md) - Connect alerts to Slack/Email
- [Monitoring Setup](monitoring-setup.md) - Grafana dashboards
