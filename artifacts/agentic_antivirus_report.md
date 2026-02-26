# Agentic Antivirus / GeoSeal Triage Report
Generated: 2026-02-16T07:45:13.980267+00:00
Repo: C:\Users\issda\SCBE-AETHERMOORE-working
Risk: HIGH (score 0.5184)
Findings: 277

## Severity Counts
- critical: 0
- high: 124
- medium: 48
- low: 105

## GeoSeal Ringing Summary
- Total chunks assessed: 276
- Quarantine count: 0
- Core rings: 177
- Outer rings: 95
- Blocked rings: 4
- Top phase tags:
  - AV: 105
  - CA: 26
  - DR: 41
  - KO: 0
  - RU: 48
  - UM: 57

## Top Findings

- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\DEMOS.md:321
  - phase=AV, confidence=0.84
  - # http://localhost:8080/demo/index.html
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\DEMOS.md:330
  - phase=AV, confidence=0.84
  - # http://localhost:8080/demo/mars-communication.html
- HIGH [unsafe_shell_pattern] C:\Users\issda\SCBE-AETHERMOORE-working\demo_complete_system.py:813
  - phase=DR, confidence=0.84
  - ("execute", "rm -rf /", 0.95),
- HIGH [unsafe_shell_pattern] C:\Users\issda\SCBE-AETHERMOORE-working\demo_complete_system.py:1012
  - phase=DR, confidence=0.84
  - "target": "rm -rf /important/data",
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docker-compose.api.yml:3
  - phase=AV, confidence=0.84
  - # Test: curl http://localhost:8080/v1/health
- HIGH [hardcoded_api_key] C:\Users\issda\SCBE-AETHERMOORE-working\docker-compose.api.yml:15
  - phase=UM, confidence=0.84
  - - SCBE_API_KEY=${SCBE_API_KEY:-sk_test_demo_key_12345}
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docker-compose.api.yml:18
  - phase=AV, confidence=0.84
  - test: ["CMD", "curl", "-f", "http://localhost:8080/v1/health"]
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docker-compose.unified.yml:37
  - phase=AV, confidence=0.84
  - test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docker-compose.unified.yml:59
  - phase=AV, confidence=0.84
  - - SCBE_CORE_URL=http://scbe-core:8000
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docker-compose.unified.yml:66
  - phase=AV, confidence=0.84
  - test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docker-compose.unified.yml:147
  - phase=AV, confidence=0.84
  - - SCBE_CORE_URL=http://scbe-core:8000
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\INSTRUCTIONS.md:26
  - phase=AV, confidence=0.84
  - # Open http://localhost:8000/docs
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\INSTRUCTIONS.md:100
  - phase=AV, confidence=0.84
  - curl -X POST http://localhost:8000/seal-memory \
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\INSTRUCTIONS.md:109
  - phase=AV, confidence=0.84
  - curl -X POST http://localhost:8000/retrieve-memory \
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\INSTRUCTIONS.md:183
  - phase=AV, confidence=0.84
  - curl http://localhost:8000/health
- HIGH [unsafe_shell_pattern] C:\Users\issda\SCBE-AETHERMOORE-working\INSTRUCTIONS.md:217
  - phase=DR, confidence=0.84
  - rm -rf node_modules
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\run_demo.py:11
  - phase=CA, confidence=0.84
  - exec(open('demo_complete_system.py', encoding='utf-8').read())
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\scbe-agent.py:367
  - phase=CA, confidence=0.84
  - if "eval(" in line_lower:
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\scbe-agent.py:371
  - phase=CA, confidence=0.84
  - "title": "Dangerous eval() usage",
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\scbe-agent.py:373
  - phase=CA, confidence=0.84
  - "description": "eval() can execute arbitrary code",
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\scbe-agent.py:378
  - phase=CA, confidence=0.84
  - if "exec(" in line_lower:
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\scbe-agent.py:382
  - phase=CA, confidence=0.84
  - "title": "Dangerous exec() usage",
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\scbe-agent.py:384
  - phase=CA, confidence=0.84
  - "description": "exec() can execute arbitrary code",
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\scbe-agent.py:431
  - phase=CA, confidence=0.84
  - if "os.system(" in line_lower or "subprocess." in line_lower:
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\agents\browser_agent.py:16
  - phase=AV, confidence=0.84
  - - SCBE API running at http://127.0.0.1:8080
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\agents\browser_agent.py:36
  - phase=AV, confidence=0.84
  - SCBE_API_URL = os.getenv("SCBE_API_URL", "http://127.0.0.1:8080")
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\agents\swarm_browser.py:520
  - phase=AV, confidence=0.84
  - scbe_url: str = "http://127.0.0.1:8080"
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\api\governance-schema.yaml:13
  - phase=AV, confidence=0.84
  - - url: http://localhost:8080/v1
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\app\server.js:247
  - phase=AV, confidence=0.84
  - const url = new URL(req.url || '/', `http://${req.headers.host}`);
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\app\server.js:384
  - phase=AV, confidence=0.84
  - Server listening on http://localhost:${PORT}
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\app\server.ts:323
  - phase=AV, confidence=0.84
  - const url = new URL(req.url || '/', `http://${req.headers.host}`);
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\app\server.ts:478
  - phase=AV, confidence=0.84
  - Server listening on http://localhost:${PORT}
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\demo\README.md:25
  - phase=AV, confidence=0.84
  - Then visit: http://localhost:8080
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\demo\swarm_demo.py:355
  - phase=AV, confidence=0.84
  - "http://localhost:8080/v1/govern",
- HIGH [command_injection_risk] C:\Users\issda\SCBE-AETHERMOORE-working\demos\demo_product_showcase.py:580
  - phase=CA, confidence=0.84
  - os.system("color")
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docs\AGENT_ARCHITECTURE.md:474
  - phase=AV, confidence=0.84
  - curl http://vault-proxy:8200/v1/scbe/master-key \
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docs\INTEGRATION_ROADMAP.md:274
  - phase=AV, confidence=0.84
  - scbe_core: http://localhost:8000
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docs\INTEGRATION_ROADMAP.md:275
  - phase=AV, confidence=0.84
  - quantum_service: http://localhost:8001
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docs\INTEGRATION_ROADMAP.md:276
  - phase=AV, confidence=0.84
  - spiralverse: http://localhost:8002
- LOW [insecure_http] C:\Users\issda\SCBE-AETHERMOORE-working\docs\local-run.md:38
  - phase=AV, confidence=0.84
  - - http://localhost:8000/docs

## Quarantine Candidates
No quarantine candidates.

## Recommended Actions
- command_injection_risk
- hardcoded_api_key
- insecure_http
- password_in_source
- unsafe_shell_pattern
- Remove or isolate all blocked chunks and rerun GeoSeal quarantine.
- Move quarantined files to review lanes and reduce execution permissions until fixed.