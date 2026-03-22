# Money Flow Command Lanes

## Lane A: Browser-first Shopify session
```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
python scripts/system/browser_chain_dispatcher.py --domain admin.shopify.com --task navigate --engine playwriter
playwriter session new
python scripts/system/playwriter_lane_runner.py --session <SESSION_ID> --task navigate --url "https://admin.shopify.com"
python scripts/system/playwriter_lane_runner.py --session <SESSION_ID> --task title
python scripts/system/playwriter_lane_runner.py --session <SESSION_ID> --task snapshot
```

## Lane B: Store launch pack (no live publish)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\run_shopify_store_launch_pack.ps1 -Store "aethermore-code.myshopify.com" -RunBothSideTest
```

## Lane C: Live publish (explicit only)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\run_shopify_store_launch_pack.ps1 -Store "aethermore-code.myshopify.com" -RunBothSideTest -PublishLive
```

## Lane D: Monetization swarm
```powershell
python scripts/system/dispatch_monetization_swarm.py --sender "agent.codex" --codename "Revenue-Swarm-01"
python scripts/system/monetization_swarm_status.py --limit 500
```

## Lane E: Internet workflow synthesis tuning
```powershell
python C:/Users/issda/.codex/skills/scbe-internet-workflow-synthesis/scripts/synthesize_pipeline_profile.py --repo-root C:/Users/issda/SCBE-AETHERMOORE --output training/internet_workflow_profile.json --force
python C:/Users/issda/.codex/skills/scbe-internet-workflow-synthesis/scripts/run_e2e_pipeline.py --repo-root C:/Users/issda/SCBE-AETHERMOORE --profile training/internet_workflow_profile.json
```
