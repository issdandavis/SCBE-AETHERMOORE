# AI Workflow Architect - Deployment Guide

## 🚀 Quick Launch Checklist

### ✅ Pre-Deployment Setup
- [x] Removed all Replit dependencies
- [x] Updated to standard environment variables
- [x] Fixed TypeScript compilation errors
- [x] Tested build process successfully
- [x] Database schema ready (18 tables)

### 🔧 Required Environment Variables

#### Core Requirements
```bash
DATABASE_URL=postgresql://username:password@host:port/database
SESSION_SECRET=your-32-char-random-string-here
APP_ORIGIN=https://your-domain.com
```

#### AI Providers (add at least one)
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...
PERPLEXITY_API_KEY=pplx-...
GROQ_API_KEY=gsk_...
```

#### Stripe Integration (for your account)
```bash
STRIPE_PUBLISHABLE_KEY=pk_test_... # or pk_live_...
STRIPE_SECRET_KEY=sk_test_... # or sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_... # from Stripe dashboard
```

#### Google Services (for your account)
```bash
GOOGLE_DRIVE_CLIENT_ID=your-oauth-client-id
GOOGLE_DRIVE_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_DRIVE_REFRESH_TOKEN=your-refresh-token
```

#### Optional Integrations
```bash
GITHUB_TOKEN=ghp_...
NOTION_TOKEN=secret_...
DROPBOX_ACCESS_TOKEN=sl.B...
ONEDRIVE_ACCESS_TOKEN=your-graph-token
```

## 🌐 Deployment Platforms

### Vercel (Recommended)
1. **Connect Repository**: Import from GitHub
2. **Framework**: Vite (auto-detected)
3. **Build Command**: `npm run build`
4. **Output Directory**: `dist/public`
5. **Install Command**: `npm install`
6. **Environment Variables**: Add all required vars above

### Railway
1. **Connect Repository**: Link GitHub repo
2. **Environment Variables**: Add via Railway dashboard
3. **Auto-deploy**: Enabled by default

### Render
1. **Web Service**: Connect GitHub repo
2. **Build Command**: `npm run build`
3. **Start Command**: `npm run start`
4. **Environment Variables**: Add via Render dashboard

## 📊 Database Setup

### Using Neon (PostgreSQL)
1. Create account at neon.tech
2. Create new project
3. Copy connection string to `DATABASE_URL`
4. Run migrations: `npm run db:push`

### Using Supabase
1. Create project at supabase.com
2. Go to Settings > Database
3. Copy connection string to `DATABASE_URL`
4. Run migrations: `npm run db:push`

## 🔐 Security Configuration

### Session Secret Generation
```bash
# Generate secure session secret
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### Stripe Webhook Setup
1. Go to Stripe Dashboard > Webhooks
2. Add endpoint: `https://your-domain.com/api/stripe/webhook`
3. Select events: `customer.*`, `invoice.*`, `subscription.*`
4. Copy webhook secret to `STRIPE_WEBHOOK_SECRET`

### Google OAuth Setup
1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials
3. Add authorized redirect URI: `https://your-domain.com/auth/google/callback`
4. Copy client ID and secret

## 🧪 Testing Deployment

### Health Check
```bash
curl https://your-domain.com/api/health
# Should return: {"status":"ok","time":"...","version":"1.0.0"}
```

### Database Connection
```bash
curl https://your-domain.com/api/auth/me
# Should return 401 (auth required) - confirms DB connection
```

### AI Provider Test
1. Login to app
2. Go to Settings > Integrations
3. Test AI provider connections
4. Run a simple agent task

## 🚨 Troubleshooting

### Build Failures
- **Missing dependencies**: Run `npm install`
- **TypeScript errors**: Run `npm run check`
- **Memory issues**: Increase build memory limit

### Runtime Errors
- **Database connection**: Check `DATABASE_URL` format
- **Session issues**: Verify `SESSION_SECRET` is set
- **CORS errors**: Ensure `APP_ORIGIN` matches your domain

### Integration Issues
- **Stripe**: Verify webhook endpoint and secret
- **Google**: Check OAuth redirect URI configuration
- **AI Providers**: Validate API key formats

## 📈 Performance Optimization

### Build Optimization
- Bundle size: 1.4MB (server) + 1.4MB (client)
- Cold start: ~2-3 seconds
- Memory usage: ~150MB base

### Database Optimization
- Connection pooling enabled
- Prepared statements via Drizzle ORM
- Audit logging for compliance

### Caching Strategy
- Static assets: CDN cached
- API responses: No caching (real-time data)
- Session storage: PostgreSQL

## 🔄 CI/CD Pipeline

### GitHub Actions (Optional)
```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npm run check
      - run: npm run build
      # Deploy to your platform
```

## 📋 Post-Deployment Checklist

### Immediate Tasks
- [ ] Verify health endpoint responds
- [ ] Test user registration/login
- [ ] Confirm database tables created
- [ ] Test at least one AI provider
- [ ] Verify Stripe webhook receives events

### Security Audit
- [ ] HTTPS enabled and enforced
- [ ] Security headers configured (Helmet.js)
- [ ] Rate limiting active
- [ ] Session security validated
- [ ] Environment variables secured

### Monitoring Setup
- [ ] Error tracking (Sentry recommended)
- [ ] Performance monitoring
- [ ] Database monitoring
- [ ] Cost tracking for AI usage

## 🎯 Success Metrics

### Technical KPIs
- **Uptime**: >99.9%
- **Response time**: <500ms (95th percentile)
- **Error rate**: <0.1%
- **Build time**: <2 minutes

### Business KPIs
- **User registration**: Track signups
- **AI usage**: Monitor token consumption
- **Revenue**: Stripe integration working
- **Integrations**: Connection success rates

## 🆘 Support Resources

### Documentation
- [Full Feature List](docs/FULL_FEATURE_LIST.md)
- [API Documentation](docs/PROJECT_DOCUMENTATION.md)
- [Environment Variables](.env.example)

### Community
- GitHub Issues for bug reports
- Discussions for feature requests
- Wiki for community guides

---

## 🎉 Launch Ready!

Your AI Workflow Architect is now production-ready with:
- ✅ Multi-provider AI orchestration
- ✅ Secure credential storage (AES-256-GCM)
- ✅ Real-time budget tracking
- ✅ Stripe payment integration
- ✅ Google services integration
- ✅ Enterprise security features
- ✅ Comprehensive audit logging
- ✅ Rate limiting and cost governance

**Next Steps**: Deploy, test, and start building your AI automation business!