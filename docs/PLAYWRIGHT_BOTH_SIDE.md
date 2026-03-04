# Playwright Both-Side Runner

Use one Playwright session to handle two browser sides (left and right) at the same time.

## Install
```powershell
python -m pip install playwright
playwright install chromium
```

## LinkedIn + Telegraph
```powershell
python scripts/playwright_both_side.py --left-url "https://www.linkedin.com/" --right-url "https://telegra.ph/" --left-name linkedin --right-name telegraph
```

## Keep Browser Open For Manual Steps
```powershell
python scripts/playwright_both_side.py --left-url "https://www.linkedin.com/" --right-url "https://telegra.ph/" --keep-open
```

## Outputs
- Screenshots in `artifacts/playwright-both-side/`
- JSON report in `artifacts/playwright-both-side/*-report.json`
  - URL/title for each side
  - bot-check hint (`true/false`)

## Notes
- Script uses a persistent profile (`~/.scbe-playwright-both-side`) so login sessions survive.
- If LinkedIn shows anti-bot challenge, run non-headless and complete challenge manually.
