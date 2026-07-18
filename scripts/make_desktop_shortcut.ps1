# Create/update Desktop shortcut -> GUI launcher (launch_daw_mcp.bat -> launcher_gui.py)
param(
  [string]$PackRoot = (Split-Path $PSScriptRoot -Parent)
)

$launcher = Join-Path $PackRoot 'launch_daw_mcp.bat'
$gui = Join-Path $PackRoot 'launcher_gui.py'
if (-not (Test-Path -LiteralPath $launcher)) {
  Write-Error "Missing launcher: $launcher"
  exit 1
}
if (-not (Test-Path -LiteralPath $gui)) {
  Write-Error "Missing GUI: $gui"
  exit 1
}

function Get-DesktopPath {
  $candidates = @(
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path $env:USERPROFILE 'Desktop'),
    (Join-Path $env:USERPROFILE 'OneDrive\Desktop'),
    (Join-Path $env:USERPROFILE 'OneDrive - Personal\Desktop')
  )
  foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c)) { return $c }
  }
  return [Environment]::GetFolderPath('Desktop')
}

function Find-PythonW {
  $cands = @(
    (Get-Command pythonw -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    (Get-Command pyw -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
    "C:\Python311\pythonw.exe"
  ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
  if ($cands) { return $cands[0] }
  return $null
}

$desktop = Get-DesktopPath
$shell = New-Object -ComObject WScript.Shell

# Primary: GUI
$lnkPath = Join-Path $desktop 'DAW Horsemen.lnk'
$pyw = Find-PythonW
$sc = $shell.CreateShortcut($lnkPath)
if ($pyw) {
  $sc.TargetPath = $pyw
  $sc.Arguments = "`"$gui`""
  $sc.WorkingDirectory = $PackRoot
} else {
  $sc.TargetPath = $launcher
  $sc.WorkingDirectory = $PackRoot
}
$sc.WindowStyle = 1
$sc.Description = 'DAW Horsemen GUI — CARE/update, start DAWs+MCP, health + log'
$sc.IconLocation = 'C:\Windows\System32\shell32.dll,165'
$sc.Save()
Write-Host "Desktop shortcut OK: $lnkPath"
Write-Host "Target: $($sc.TargetPath) $($sc.Arguments)"

# Alias old name -> same GUI
$old = Join-Path $desktop 'DAW MCP Launchers.lnk'
$sc2 = $shell.CreateShortcut($old)
$sc2.TargetPath = $sc.TargetPath
$sc2.Arguments = $sc.Arguments
$sc2.WorkingDirectory = $PackRoot
$sc2.WindowStyle = 1
$sc2.Description = $sc.Description
$sc2.IconLocation = $sc.IconLocation
$sc2.Save()
Write-Host "Also updated: $old"

exit 0
