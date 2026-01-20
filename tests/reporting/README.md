# Test Reporting

Compliance dashboards, security scorecards, and executive summaries.

## Components

- `compliance_dashboard.ts` - Real-time compliance status dashboard
- `security_scorecard.ts` - Security metrics and vulnerability tracking
- `executive_summary.ts` - High-level executive reports
- `html_reporter.ts` - HTML report generation with Tailwind CSS

## Dashboard Features

- **Executive Summary**: Overall compliance score, standards status
- **Quantum Security Metrics**: Security bits, PQC status, attack resistance
- **AI Safety Dashboard**: Intent verification accuracy, governance violations
- **Performance Metrics**: Throughput, latency, resource utilization
- **Security Scorecard**: Vulnerability count, fuzzing coverage, penetration test status
- **Test Execution Status**: Pass/fail rates, coverage, recent failures

## Design System

All dashboards follow the SCBE design system:

- Dark gradient background (`#1a1a2e` → `#16213e` → `#0f3460`)
- Glass effect cards with Tailwind CSS
- Semantic colors: Green=safe, Red=danger, Yellow=warning, Blue=info
- Responsive design with `md:` breakpoints
