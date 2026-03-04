PRODUCTION_CONSOLIDATION_PLAN.md# Production Infrastructure & Runners Setup

## 🎯 Objective
Set up production-ready infrastructure with:
- Self-hosted GitHub Actions runners for all apps
- Webhook endpoints for Notion & Proton Mail integrations
- Automated CI/CD pipelines
- Service orchestration

---

## 📦 Apps & Services Inventory

### Current Applications
1. **AI Workflow Architect** (Main Platform)
   - Location: GitHub repo + Replit
   - Stack: React + Express + PostgreSQL
   - Status: Active, needs production deployment

2. **ForgeMind AI Agent** (Google AI Studio)
   - Agents: Research, CodeGen, Test, Deploy
   - Location: AI Studio
   - Status: Active, needs webhook integration

3. **Email AI Backboard** (Proton Mail Router)
   - Location: Script folder
   - Purpose: Route emails to AI agents
   - Status: Documented, needs implementation

4. **Shopify Integration**
   - Location: shopify.app.toml
   - Purpose: AI product descriptions
   - Status: Configured, needs testing

### External Services to Integrate
- Zapier (automation)
- Notion (project management/webhooks)
- Linear (issue tracking)
- NotebookLM (documentation)
- Firebase (database/hosting)
- Vercel (deployment)

---

## 🏃 GitHub Actions Runners Setup

### 1. Self-Hosted Runner Installation

```bash
# Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download latest runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure (use your repo token)
./config.sh --url https://github.com/issdandavis/AI-Workflow-Architect.01.01.02 --token YOUR_TOKEN

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2. Runner Configuration Per Service

#### Main App Runner
```yaml
# .github/workflows/main-app-runner.yml
name: Main App CI/CD

on:
  push:
    branches: [main, develop]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test
      - name: Build
        run: npm run build
      - name: Deploy to production
        run: npm run deploy:prod
```

#### AI Agent Runner
```yaml
# .github/workflows/ai-agent-runner.yml  
name: AI Agent Operations

on:
  repository_dispatch:
    types: [ai-agent-trigger]
  webhook:

jobs:
  run-agent:
    runs-on: self-hosted
    steps:
      - name: Trigger ForgeMind Agent
        run: |
          curl -X POST ${{ secrets.AI_STUDIO_WEBHOOK }} \
            -H "Authorization: Bearer ${{ secrets.AI_STUDIO_TOKEN }}" \
            -d '{"agent": "${{ github.event.client_payload.agent }}", "task": "${{ github.event.client_payload.task }}"}'
```

#### Email Router Runner  
```yaml
# .github/workflows/email-router-runner.yml
name: Email AI Router

on:
  repository_dispatch:
    types: [email-received]

jobs:
  route-email:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Process Email
        run: node script/email-router.js
        env:
          PROTON_API_KEY: ${{ secrets.PROTON_API_KEY }}
          EMAIL_PAYLOAD: ${{ github.event.client_payload.email }}
```

---

## 🪝 Webhook Infrastructure

### 1. Notion Webhook Gateway

#### Create Notion Integration
1. Go to https://www.notion.so/my-integrations
2. Create new integration: "AI Workflow Webhooks"
3. Copy Internal Integration Token
4. Add to GitHub Secrets as `NOTION_TOKEN`

#### Notion Database Setup
```markdown
**Database: Workflow Triggers**
Properties:
- Trigger Name (Title)
- Service (Select): Main App, AI Agent, Email Router, Shopify
- Action (Select): Deploy, Test, Build, Run Agent, Route Email
- Status (Status): Pending, Running, Complete, Failed  
- Webhook URL (URL)
- Last Triggered (Date)
```

#### Notion Automation (via Zapier)
```
Trigger: New database item OR Status changed to "Pending"
Action: Webhook POST to GitHub Actions
URL: https://api.github.com/repos/issdandavis/AI-Workflow-Architect.01.01.02/dispatches
Payload:
{
  "event_type": "notion-trigger",
  "client_payload": {
    "service": "{{Service}}",
    "action": "{{Action}}",
    "trigger_name": "{{Trigger Name}}"
  }
}
```

### 2. Proton Mail Webhook Gateway

#### ProtonMail Bridge Setup
```bash
# Install Proton Bridge (for IMAP access)
wget https://proton.me/download/bridge/protonmail-bridge_latest_amd64.deb
sudo dpkg -i protonmail-bridge_latest_amd64.deb

# Configure bridge
protonmail-bridge --cli
# Login and get IMAP credentials
```

#### Email Webhook Server
```javascript
// script/email-webhook-server.js
const express = require('express');
const Imap = require('imap');
const {simpleParser} = require('mailparser');

const app = express();

const imap = new Imap({
  user: process.env.PROTON_EMAIL,
  password: process.env.PROTON_BRIDGE_PASSWORD,
  host: '127.0.0.1',
  port: 1143,
  tls: true
});

// Watch for new emails
imap.once('ready', () => {
  imap.openBox('INBOX', false, () => {
    imap.on('mail', async (numNewMsgs) => {
      const fetch = imap.seq.fetch(`${numNewMsgs}:*`, {
        bodies: ''
      });
      
      fetch.on('message', (msg) => {
        msg.on('body', async (stream) => {
          const parsed = await simpleParser(stream);
          
          // Trigger GitHub Action based on email subject
          if (parsed.subject.includes('[DEPLOY]')) {
            await triggerGitHubAction('deploy-trigger', {
              from: parsed.from.text,
              body: parsed.text
            });
          } else if (parsed.subject.includes('[AI-AGENT]')) {
            await triggerGitHubAction('ai-agent-trigger', {
              task: parsed.text,
              requester: parsed.from.text
            });
          }
        });
      });
    });
  });
});

imap.connect();

app.listen(3001, () => {
  console.log('Email webhook server running on port 3001');
});
```

### 3. Unified Webhook Receiver

```javascript
// server/webhooks/receiver.js
const express = require('express');
const router = express.Router();
const { Octokit } = require('@octokit/rest');

const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });

// Notion webhook
router.post('/notion', async (req, res) => {
  const { service, action, params } = req.body;
  
  await octokit.repos.createDispatchEvent({
    owner: 'issdandavis',
    repo: 'AI-Workflow-Architect.01.01.02',
    event_type: `notion-${service}-${action}`,
    client_payload: params
  });
  
  res.json({ success: true });
});

// Proton webhook  
router.post('/proton', async (req, res) => {
  const { from, subject, body } = req.body;
  
  // Parse email commands
  const command = parseEmailCommand(subject);
  
  await octokit.repos.createDispatchEvent({
    owner: 'issdandavis',
    repo: 'AI-Workflow-Architect.01.01.02',
    event_type: `email-${command.type}`,
    client_payload: { from, body, ...command.params }
  });
  
  res.json({ success: true });
});

// AI Studio callback
router.post('/ai-studio', async (req, res) => {
  const { agent, status, result } = req.body;
  
  // Store result in database
  await db.agentRuns.create({
    agent,
    status,
    result,
    completedAt: new Date()
  });
  
  res.json({ success: true });
});

module.exports = router;
```

---

## 🔧 Infrastructure Services

### Service Manager Script
```bash
#!/bin/bash
# script/service-manager.sh

case "$1" in
  start-all)
    echo "Starting all services..."
    pm2 start server/index.js --name "main-app"
    pm2 start script/email-webhook-server.js --name "email-router"
    sudo systemctl start actions.runner.*
    ;;
  stop-all)
    echo "Stopping all services..."
    pm2 stop all
    sudo systemctl stop actions.runner.*
    ;;
  status)
    echo "Service Status:"
    pm2 status
    systemctl status actions.runner.* --no-pager
    ;;
  restart)
    $0 stop-all
    sleep 2
    $0 start-all
    ;;
  *)
    echo "Usage: $0 {start-all|stop-all|status|restart}"
    exit 1
    ;;
esac
```

---

## 📋 Setup Checklist

### Phase 1: Runner Infrastructure
- [ ] Install self-hosted GitHub Actions runner
- [ ] Configure runner for main repository  
- [ ] Create workflow files for each service
- [ ] Test runner with simple workflow
- [ ] Set up runner monitoring

### Phase 2: Notion Integration
- [ ] Create Notion integration & get token
- [ ] Set up Workflow Triggers database
- [ ] Configure Zapier automation
- [ ] Create webhook receiver endpoint
- [ ] Test Notion → GitHub Actions trigger

### Phase 3: Proton Mail Integration  
- [ ] Install Proton Bridge
- [ ] Get IMAP credentials
- [ ] Create email webhook server
- [ ] Set up email parsing rules
- [ ] Test email → GitHub Actions trigger

### Phase 4: Service Orchestration
- [ ] Install PM2 for process management
- [ ] Create service manager script
- [ ] Configure auto-restart on failure
- [ ] Set up health check endpoints
- [ ] Configure logging & monitoring

### Phase 5: Security & Secrets
- [ ] Add all API keys to GitHub Secrets
- [ ] Configure webhook authentication
- [ ] Set up IP whitelist for webhooks
- [ ] Enable 2FA on all services
- [ ] Create backup of all credentials

---

## 🚀 Deployment Commands

```bash
# Install dependencies
npm install pm2 -g

# Set up runners
./script/setup-runner.sh

# Start all services
./script/service-manager.sh start-all

# Check status
./script/service-manager.sh status

# View logs
pm2 logs
journalctl -u actions.runner.* -f
```

---

## 📊 Monitoring Dashboard

### Key Metrics to Track
1. Runner availability & queue length
2. Webhook success/failure rates  
3. Service uptime
4. Email processing latency
5. AI agent completion times

### Monitoring Tools
- PM2 web dashboard: `pm2 web`
- GitHub Actions insights
- Custom health check dashboard

---

## 🔄 Next Steps

1. **Immediate**: Set up self-hosted runner
2. **Today**: Create Notion webhook database  
3. **This Week**: Implement email router
4. **Ongoing**: Monitor and optimize

---

*Last Updated: December 27, 2025*
