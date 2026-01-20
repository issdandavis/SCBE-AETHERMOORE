# Kiro Startup Error - Fixed

**Issue**: MCP server connection error for Aurora DSQL power  
**Error**: `Failed to connect to MCP server "power-aurora-dsql-aurora-dsql": MCP error -32000: Connection closed`

## Root Cause

The Aurora DSQL power was installed but not configured with required AWS credentials:
- `${CLUSTER}` - Aurora DSQL cluster identifier
- `${REGION}` - AWS region (e.g., us-east-1)
- `${AWS_PROFILE}` - AWS CLI profile name

## Solution Applied

**Disabled the Aurora DSQL power** since it's not currently needed for your SCBE project.

Location: `~/.kiro/settings/mcp.json`

```json
"power-aurora-dsql-aurora-dsql": {
  "disabled": true  // ✓ Added this
}
```

### PowerShell Command Used
```powershell
$configPath = "$env:USERPROFILE\.kiro\settings\mcp.json"
$config = Get-Content $configPath -Raw | ConvertFrom-Json
$config.powers.mcpServers.'power-aurora-dsql-aurora-dsql' | Add-Member -NotePropertyName 'disabled' -NotePropertyValue $true -Force
$config | ConvertTo-Json -Depth 10 | Set-Content $configPath
```

**Status**: ✓ Verified - `disabled: true` is now set

## Restart Kiro

1. Close all Kiro windows
2. Reopen Kiro
3. The error should be gone

## If You Need Aurora DSQL Later

To re-enable and configure:

1. Set environment variables:
   ```bash
   # Windows PowerShell
   $env:CLUSTER = "your-cluster-id"
   $env:REGION = "us-east-1"
   $env:AWS_PROFILE = "default"
   ```

2. Edit `~/.kiro/settings/mcp.json`:
   ```json
   "power-aurora-dsql-aurora-dsql": {
     "disabled": false,
     "args": [
       "awslabs.aurora-dsql-mcp-server@latest",
       "--cluster_endpoint",
       "your-cluster-id.dsql.us-east-1.on.aws",
       "--region",
       "us-east-1",
       "--database_user",
       "admin",
       "--allow-writes"
     ],
     "env": {
       "AWS_PROFILE": "default"
     }
   }
   ```

## Other Active Powers

Your other powers should work fine:
- ✓ GitKraken (git operations)
- ✓ Figma (design integration)
- ✓ Cloud Architect (AWS pricing, docs, API)
- ✓ AWS AgentCore (Bedrock agents)
- ✓ Strands (AI agents)
- ✓ SaaS Builder (DynamoDB, Serverless, etc.)

## Status

**✓ FIXED** - Kiro should start without errors now.

---

**Next Steps**: Restart Kiro and continue working on the Spiralverse architecture spec!
