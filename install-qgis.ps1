<#
.SYNOPSIS
1-Line Web Installer for AntigravityGIS (QGIS Desktop)
Usage in PowerShell:
irm https://raw.githubusercontent.com/sounny/antigravitygis/main/install-qgis.ps1 | iex
#>

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  AntigravityGIS by Sounny — QGIS Plugin Setup   " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Target Directory in QGIS plugins
$appdata = [Environment]::GetFolderPath('ApplicationData')
$targetDir = Join-Path $appdata "QGIS\QGIS3\profiles\default\python\plugins\AntigravityGIS"

Write-Host "Creating QGIS plugin directory: $targetDir" -ForegroundColor Yellow
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# 2. Download Core & Plugin Files from GitHub directly
$baseUrl = "https://raw.githubusercontent.com/sounny/antigravitygis/main"
$files = @(
    @{ Url = "$baseUrl/agent_core.py"; Dest = (Join-Path $targetDir "agent_core.py") },
    @{ Url = "$baseUrl/qgis/qgis_agent_core.py"; Dest = (Join-Path $targetDir "qgis_agent_core.py") },
    @{ Url = "$baseUrl/qgis/antigravitygis_plugin.py"; Dest = (Join-Path $targetDir "antigravitygis_plugin.py") },
    @{ Url = "$baseUrl/qgis/__init__.py"; Dest = (Join-Path $targetDir "__init__.py") },
    @{ Url = "$baseUrl/qgis/metadata.txt"; Dest = (Join-Path $targetDir "metadata.txt") }
)

foreach ($f in $files) {
    Write-Host "Downloading $($f.Dest | Split-Path -Leaf)..." -ForegroundColor Gray
    Invoke-RestMethod -Uri $f.Url -OutFile $f.Dest
}

# 3. Locate Python and Install google-antigravity
Write-Host "Configuring dependencies..." -ForegroundColor Cyan
try {
    Start-Process -FilePath "python.exe" -ArgumentList "-m pip install --upgrade google-antigravity protobuf" -Wait -NoNewWindow -ErrorAction SilentlyContinue
} catch {}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host " SUCCESS: QGIS Plugin Installed Successfully!    " -ForegroundColor Green
Write-Host " Next Steps:" -ForegroundColor White
Write-Host " 1. Launch QGIS Desktop" -ForegroundColor White
Write-Host " 2. Go to: Plugins -> Manage and Install Plugins" -ForegroundColor White
Write-Host " 3. Click 'Installed' tab -> check 'AntigravityGIS'" -ForegroundColor White
Write-Host " 4. Click the AntigravityGIS icon in your toolbar!" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Green
