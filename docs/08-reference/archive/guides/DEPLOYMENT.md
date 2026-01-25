# SCBE-AETHERMOORE Deployment Guide

Complete guide for deploying SCBE-AETHERMOORE in production environments.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [NPM Package Deployment](#npm-package-deployment)
- [Docker Deployment](#docker-deployment)
- [AWS Lambda Deployment](#aws-lambda-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [GitHub Pages (Demo)](#github-pages-demo)
- [Environment Configuration](#environment-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Security Considerations](#security-considerations)

## 🔧 Prerequisites

- Node.js >= 18.0.0
- Python >= 3.9
- Docker (for containerized deployments)
- kubectl (for Kubernetes deployments)
- AWS CLI (for AWS deployments)

## 📦 NPM Package Deployment

### Publishing to NPM

1. **Build the package**

   ```bash
   npm run build
   ```

2. **Test the package locally**

   ```bash
   npm pack
   npm install ./scbe-aethermoore-3.0.0.tgz
   ```

3. **Login to NPM**

   ```bash
   npm login
   ```

4. **Publish**
   ```bash
   npm publish --access public
   ```

### Installing from NPM

```bash
npm install @scbe/aethermoore
```

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t scbe-aethermoore:3.0.0 .
```

### Run Container

```bash
docker run -d \
  --name scbe-app \
  -p 3000:3000 \
  -p 8000:8000 \
  -e NODE_ENV=production \
  -e SCBE_LOG_LEVEL=info \
  scbe-aethermoore:3.0.0
```

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Push to Container Registry

```bash
# Tag image
docker tag scbe-aethermoore:3.0.0 ghcr.io/isdandavis2/scbe-aethermoore:3.0.0

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Push
docker push ghcr.io/isdandavis2/scbe-aethermoore:3.0.0
```

## ☁️ AWS Lambda Deployment

### Package for Lambda

```bash
# Install production dependencies
npm ci --production

# Create deployment package
zip -r scbe-lambda.zip . -x "*.git*" "tests/*" "docs/*"
```

### Deploy with AWS CLI

```bash
# Create Lambda function
aws lambda create-function \
  --function-name scbe-aethermoore \
  --runtime nodejs20.x \
  --handler index.handler \
  --zip-file fileb://scbe-lambda.zip \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 512

# Update function code
aws lambda update-function-code \
  --function-name scbe-aethermoore \
  --zip-file fileb://scbe-lambda.zip
```

### Lambda Handler Example

```typescript
// lambda-handler.ts
import { encrypt, decrypt } from '@scbe/aethermoore/crypto';

export const handler = async (event: any) => {
  const { action, data, key } = JSON.parse(event.body);

  try {
    if (action === 'encrypt') {
      const ciphertext = encrypt(data, key);
      return {
        statusCode: 200,
        body: JSON.stringify({ ciphertext }),
      };
    } else if (action === 'decrypt') {
      const plaintext = decrypt(data, key);
      return {
        statusCode: 200,
        body: JSON.stringify({ plaintext }),
      };
    }
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};
```

## ☸️ Kubernetes Deployment

### Create Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scbe-aethermoore
  labels:
    app: scbe
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scbe
  template:
    metadata:
      labels:
        app: scbe
    spec:
      containers:
        - name: scbe
          image: ghcr.io/isdandavis2/scbe-aethermoore:3.0.0
          ports:
            - containerPort: 3000
            - containerPort: 8000
          env:
            - name: NODE_ENV
              value: 'production'
            - name: SCBE_LOG_LEVEL
              value: 'info'
          resources:
            requests:
              memory: '256Mi'
              cpu: '250m'
            limits:
              memory: '512Mi'
              cpu: '500m'
          livenessProbe:
            exec:
              command:
                - python
                - -c
                - 'import sys; sys.exit(0)'
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - python
                - -c
                - 'import sys; sys.exit(0)'
            initialDelaySeconds: 5
            periodSeconds: 5
```

### Create Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: scbe-service
spec:
  selector:
    app: scbe
  ports:
    - name: http
      port: 80
      targetPort: 3000
    - name: api
      port: 8000
      targetPort: 8000
  type: LoadBalancer
```

### Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/scbe-aethermoore

# Scale deployment
kubectl scale deployment scbe-aethermoore --replicas=5
```

## 🌐 GitHub Pages (Demo)

### Enable GitHub Pages

1. Go to repository Settings → Pages
2. Select source: GitHub Actions
3. Push to main branch triggers deployment

### Manual Deployment

```bash
# Build documentation
npx typedoc --out docs-build/api src/index.ts

# Copy demo files
cp scbe-aethermoore/*.html docs-build/

# Deploy to gh-pages branch
git checkout -b gh-pages
git add docs-build
git commit -m "Deploy documentation"
git push origin gh-pages
```

## ⚙️ Environment Configuration

### Environment Variables

```bash
# .env.production
NODE_ENV=production
SCBE_LOG_LEVEL=info
SCBE_MAX_LAYERS=14
SCBE_ENCRYPTION_STRENGTH=256
SCBE_ENABLE_TELEMETRY=true
SCBE_API_KEY=your-api-key-here
```

### Configuration File

```typescript
// config/production.ts
export const config = {
  layers: 14,
  encryptionStrength: 256,
  maxRequestsPerSecond: 10000,
  timeout: 50, // ms
  enableTelemetry: true,
  logLevel: 'info',
};
```

## 📊 Monitoring & Logging

### CloudWatch (AWS)

```typescript
import { CloudWatchClient, PutMetricDataCommand } from '@aws-sdk/client-cloudwatch';

const cloudwatch = new CloudWatchClient({ region: 'us-east-1' });

async function logMetric(metricName: string, value: number) {
  await cloudwatch.send(
    new PutMetricDataCommand({
      Namespace: 'SCBE',
      MetricData: [
        {
          MetricName: metricName,
          Value: value,
          Unit: 'Count',
          Timestamp: new Date(),
        },
      ],
    })
  );
}
```

### Prometheus Metrics

```typescript
import { register, Counter, Histogram } from 'prom-client';

const encryptionCounter = new Counter({
  name: 'scbe_encryptions_total',
  help: 'Total number of encryptions',
});

const latencyHistogram = new Histogram({
  name: 'scbe_latency_seconds',
  help: 'Encryption latency in seconds',
  buckets: [0.01, 0.05, 0.1, 0.5, 1],
});
```

### Logging Best Practices

```typescript
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.SCBE_LOG_LEVEL || 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
  ],
});

logger.info('Encryption started', { userId: 'user123', dataSize: 1024 });
```

## 🔒 Security Considerations

### Key Management

1. **Use AWS Secrets Manager or HashiCorp Vault**

   ```bash
   aws secretsmanager create-secret \
     --name scbe/encryption-key \
     --secret-string "your-secret-key"
   ```

2. **Rotate keys regularly**
   ```bash
   # Automated key rotation script
   aws secretsmanager rotate-secret \
     --secret-id scbe/encryption-key \
     --rotation-lambda-arn arn:aws:lambda:region:account:function:rotate-key
   ```

### Network Security

- Use HTTPS/TLS for all communications
- Implement rate limiting
- Use API gateways for authentication
- Enable CORS with strict origins

### Access Control

```typescript
// middleware/auth.ts
export function requireAuth(req, res, next) {
  const apiKey = req.headers['x-api-key'];

  if (!apiKey || !validateApiKey(apiKey)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  next();
}
```

## 🚀 Performance Optimization

### Caching

```typescript
import NodeCache from 'node-cache';

const cache = new NodeCache({ stdTTL: 600 });

function getCachedOrCompute(key: string, computeFn: () => any) {
  const cached = cache.get(key);
  if (cached) return cached;

  const result = computeFn();
  cache.set(key, result);
  return result;
}
```

### Load Balancing

Use NGINX or AWS ALB for load balancing:

```nginx
# nginx.conf
upstream scbe_backend {
  least_conn;
  server scbe1.example.com:3000;
  server scbe2.example.com:3000;
  server scbe3.example.com:3000;
}

server {
  listen 80;
  location / {
    proxy_pass http://scbe_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

## 📈 Scaling Strategies

### Horizontal Scaling

- Use Kubernetes HPA (Horizontal Pod Autoscaler)
- AWS Auto Scaling Groups
- Load balancers for traffic distribution

### Vertical Scaling

- Increase container resources
- Optimize memory usage
- Use faster CPUs

## 🔄 CI/CD Pipeline

GitHub Actions automatically handles:

- Testing on push
- Building on merge to main
- Publishing on tag creation
- Deploying documentation

See `.github/workflows/` for details.

## 📞 Support

For deployment issues:

- GitHub Issues: https://github.com/ISDanDavis2/scbe-aethermoore/issues
- Email: issdandavis@gmail.com

---

**Happy Deploying! 🚀**
