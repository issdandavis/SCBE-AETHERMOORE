# 🔌 Spiralverse Protocol - Service Integrations

## Overview

This guide demonstrates how to integrate the Spiralverse Protocol with modern cloud services and developer tools to build production-ready AI agent systems.

---

## 🤖 Asker Bot - AI Caretaker Feature

### Concept
The **Asker Bot** is an AI caretaker that monitors other AI agents like a parent checking on their kids:
- "Have you done your tasks?"
- "Do you need to charge (resources)?"
- "Are you experiencing any errors?"
- "Do you need help with anything?"

This implements the **Status Tongue** and **Query Tongue** for autonomous fleet health monitoring.

### Architecture
```
Slack Workspace
    ↓
Asker Bot (Slack App)
    ↓
AWS Lambda Function
    ↓
Spiralverse Protocol Router
    ↓
AI Agent Fleet (robots, satellites, drones)
```

---

## 1️⃣ Slack Integration

### Setup Slack Bot with Webhooks

#### Step 1: Create Slack App
1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `Spiralverse Asker Bot`
4. Select your workspace

#### Step 2: Enable Incoming Webhooks
1. Navigate to **"Incoming Webhooks"** in sidebar
2. Toggle **"Activate Incoming Webhooks"** to **On**
3. Click **"Add New Webhook to Workspace"**
4. Select channel (e.g., `#robot-fleet-status`)
5. Copy the Webhook URL: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`

#### Step 3: Configure Bot Permissions
Go to **"OAuth & Permissions"** and add scopes:
- `chat:write` - Send messages
- `channels:read` - View channel info
- `users:read` - Read user information
- `app_mentions:read` - Respond to mentions

#### Step 4: Event Subscriptions
1. Enable **Events** in sidebar
2. Subscribe to bot events:
   - `app_mention` - When bot is @mentioned
   - `message.channels` - Channel messages
3. Set Request URL to your Lambda endpoint (next section)

---

## 2️⃣ AWS Lambda - Serverless AI Agent Backend

### Deploy Asker Bot Lambda Function

#### Lambda Function Code
```javascript
// asker-bot-lambda.js
import { SpiralverseProtocol } from '@spiralverse/core';

const protocol = new SpiralverseProtocol({
  nodeId: 'asker-bot-001',
  tongues: ['query', 'status']
});

export const handler = async (event) => {
  const body = JSON.parse(event.body);
  
  // Slack URL verification challenge
  if (body.type === 'url_verification') {
    return {
      statusCode: 200,
      body: JSON.stringify({ challenge: body.challenge })
    };
  }
  
  // Handle Slack event
  if (body.event && body.event.type === 'app_mention') {
    const userId = body.event.user;
    const channel = body.event.channel;
    const text = body.event.text;
    
    // Check if asking for fleet status
    if (text.includes('status') || text.includes('health')) {
      const fleetStatus = await checkFleetHealth();
      await sendSlackMessage(channel, formatFleetStatus(fleetStatus));
    }
    
    // Check if asking about specific robot
    if (text.includes('robot-')) {
      const robotId = text.match(/robot-\d+/)[0];
      const robotStatus = await checkRobotStatus(robotId);
      await sendSlackMessage(channel, formatRobotStatus(robotStatus));
    }
  }
  
  return { statusCode: 200, body: 'OK' };
};

async function checkFleetHealth() {
  // Use Spiralverse Query Tongue
  const response = await protocol.query({
    targets: 'fleet:all',
    queries: ['battery_level', 'task_status', 'error_count', 'last_checkin']
  });
  
  return response;
}

async function sendSlackMessage(channel, text) {
  await fetch(process.env.SLACK_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel, text })
  });
}

function formatFleetStatus(status) {
  return `🤖 *Fleet Status Report*\n\n` +
    `✅ Healthy: ${status.healthy}\n` +
    `⚠️ Low Battery: ${status.lowBattery}\n` +
    `❌ Errors: ${status.errors}\n` +
    `📊 Total Agents: ${status.total}`;
}
```

#### Deploy to AWS Lambda
```bash
# Install AWS CLI
aws configure

# Create deployment package
zip -r asker-bot.zip asker-bot-lambda.js node_modules/

# Create Lambda function
aws lambda create-function \
  --function-name spiralverse-asker-bot \
  --runtime nodejs20.x \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-exec-role \
  --handler asker-bot-lambda.handler \
  --zip-file fileb://asker-bot.zip \
  --environment Variables="{SLACK_WEBHOOK_URL=https://hooks.slack.com/...}"

# Create API Gateway trigger
aws apigatewayv2 create-api \
  --name spiralverse-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:spiralverse-asker-bot
```

---

## 3️⃣ GitHub Actions - Automated Deployment

### CI/CD Pipeline for Spiralverse Protocol

#### `.github/workflows/deploy-asker-bot.yml`
```yaml
name: Deploy Asker Bot

on:
  push:
    branches: [main]
    paths:
      - 'src/asker-bot/**'
      - '.github/workflows/deploy-asker-bot.yml'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Run tests
        run: npm test
        
      - name: Run Spiralverse Protocol validation
        run: npm run validate:protocol

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
          
      - name: Build deployment package
        run: |
          npm ci --production
          zip -r asker-bot.zip .
          
      - name: Deploy to Lambda
        run: |
          aws lambda update-function-code \
            --function-name spiralverse-asker-bot \
            --zip-file fileb://asker-bot.zip
            
      - name: Send Slack notification
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"✅ Asker Bot deployed successfully!"}'

  integration-test:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - name: Test Asker Bot endpoint
        run: |
          curl -X POST ${{ secrets.LAMBDA_API_URL }}/test \
            -H 'Content-Type: application/json' \
            -d '{"test":true}'
```

---

## 4️⃣ Scheduled Health Checks

### Automated "Mom Check-ins"

Use GitHub Actions or AWS EventBridge to schedule regular check-ins:

#### `.github/workflows/fleet-health-check.yml`
```yaml
name: Fleet Health Check

on:
  schedule:
    - cron: '0 */2 * * *'  # Every 2 hours
  workflow_dispatch:  # Manual trigger

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Query Fleet Status
        run: |
          curl -X POST ${{ secrets.LAMBDA_API_URL }}/health-check \
            -H 'Content-Type: application/json' \
            -d '{
              "action": "check_all",
              "questions": [
                "battery_level",
                "task_completion",
                "error_status",
                "resource_usage"
              ]
            }'
```

---

## 5️⃣ Integration Patterns

### Pattern 1: Slack → Lambda → Robot Fleet
```typescript
// User types in Slack: @asker-bot check robot-42
// ↓
// Slack sends webhook to Lambda
// ↓
const event = await protocol.query({
  tongue: 'query',
  target: 'robot-42',
  questions: [
    'What is your battery level?',
    'Have you completed your tasks?',
    'Do you need maintenance?'
  ]
});
// ↓
// Lambda formats response and sends to Slack
await sendSlackMessage(channel, `
  🤖 Robot-42 Status:
  🔋 Battery: 78%
  ✅ Tasks: 5/7 completed
  🔧 Maintenance: Not needed
`);
```

### Pattern 2: Automated Reminders
```typescript
// Every 2 hours via scheduled Lambda
const lowBatteryBots = await protocol.query({
  tongue: 'status',
  filter: { battery: { $lt: 20 } }
});

if (lowBatteryBots.length > 0) {
  await sendSlackAlert({
    text: `⚠️ ${lowBatteryBots.length} robots need charging!`,
    attachments: lowBatteryBots.map(bot => ({
      text: `${bot.id}: ${bot.battery}% battery`
    }))
  });
}
```

### Pattern 3: Multi-AI Coordination
```typescript
// Asker Bot coordinates multiple AIs
const taskDistribution = await protocol.negotiate({
  tongue: 'negotiation',
  participants: ['robot-fleet', 'satellite-swarm', 'drone-network'],
  task: 'space_debris_cleanup',
  resources: { time: '4h', budget: 10000 }
});

await sendSlackMessage(channel, `
  📋 Task Distribution:
  🤖 Robots: Cleanup zones 1-5
  🛰️ Satellites: Tracking and guidance  
  🚁 Drones: Transport debris to collection
`);
```

---

## 6️⃣ Production Deployment Checklist

### Security
- [ ] Store Slack webhook URL in AWS Secrets Manager
- [ ] Use JWT authentication for Lambda endpoints
- [ ] Implement rate limiting on Slack bot
- [ ] Enable CloudWatch logging
- [ ] Set up multi-signature verification

### Monitoring
- [ ] CloudWatch dashboards for Lambda metrics
- [ ] Slack alerts for critical errors
- [ ] DynamoDB table for conversation history
- [ ] X-Ray tracing for distributed debugging

### Scaling
- [ ] Lambda concurrency limits configured
- [ ] API Gateway throttling rules
- [ ] DLQ (Dead Letter Queue) for failed events
- [ ] Auto-scaling for ECS containers (if used)

---

## 7️⃣ Example Asker Bot Commands

### In Slack:
```
@asker-bot status
→ Shows overall fleet health

@asker-bot check robot-42
→ Individual robot status

@asker-bot remind low-battery
→ List all bots with <20% battery

@asker-bot help robot-99
→ Send maintenance request

@asker-bot distribute-task cleanup-zone-3
→ Coordinate multi-agent task
```

---

## 🚀 Next Steps

1. **Deploy Asker Bot** to AWS Lambda
2. **Connect to Slack** workspace
3. **Test with simulated** robot fleet
4. **Add monitoring** dashboards
5. **Scale to production** workloads

---

## 📚 Resources

- [Slack API Documentation](https://api.slack.com/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions)
- [Spiralverse Protocol Spec](./TECHNICAL_SPEC.md)

---

**Spiralverse Protocol™ | Making AI agents care for each other** 🤖💙
