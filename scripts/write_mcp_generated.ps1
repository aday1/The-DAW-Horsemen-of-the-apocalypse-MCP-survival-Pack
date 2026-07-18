# Write mcp.generated.json with absolute paths for THIS clone.
param(
  [string]$PackRoot = (Split-Path $PSScriptRoot -Parent)
)

$pyCmd = 'python'
if (Get-Command py -ErrorAction SilentlyContinue) { $pyCmd = 'py' }
elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $pyCmd = (Get-Command python).Source
}

$reaperPy = Join-Path $PackRoot 'packages\reaper-mcp\reaper_mcp_server.py'
$renoiseJs = Join-Path $PackRoot 'packages\renoise-mcp-bridge\bridge.js'
$renoiseCwd = Join-Path $PackRoot 'packages\renoise-mcp-bridge'

$doc = [ordered]@{
  mcpServers = [ordered]@{
    bitwig = [ordered]@{
      url = 'http://127.0.0.1:8080/sse'
    }
    reaper = [ordered]@{
      command = $pyCmd
      args    = @($reaperPy)
    }
    renoise = [ordered]@{
      command = 'node'
      args    = @($renoiseJs)
      cwd     = $renoiseCwd
      env     = [ordered]@{
        RENOISE_MCP_URL = 'http://127.0.0.1:19714/mcp'
      }
    }
  }
}

$out = Join-Path $PackRoot 'mcp.generated.json'
($doc | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "Wrote $out"
Write-Host "Paste into Cursor / Claude / VS Code MCP config. See IDE_SETUP.txt"
