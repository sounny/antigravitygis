<#
.SYNOPSIS
1-Line Web Installer for AntigravityGIS (ArcGIS Pro)
Usage in PowerShell:
irm https://raw.githubusercontent.com/sounny/antigravitygis/main/install-arcgis.ps1 | iex
#>

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  AntigravityGIS by Sounny — ArcGIS Pro Setup    " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Target Directory in AppData
$appdata = [Environment]::GetFolderPath('ApplicationData')
$targetDir = Join-Path $appdata "Esri\ArcGISPro\ArcToolbox\MyToolboxes\AntigravityGIS"

Write-Host "Creating deployment directory: $targetDir" -ForegroundColor Yellow
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# 2. Download Core Files from GitHub directly
$baseUrl = "https://raw.githubusercontent.com/sounny/antigravitygis/main"
$files = @(
    @{ Url = "$baseUrl/agent_core.py"; Dest = (Join-Path $targetDir "agent_core.py") },
    @{ Url = "$baseUrl/arcgis/AntigravityGIS.pyt"; Dest = (Join-Path $targetDir "AntigravityGIS.pyt") }
)

foreach ($f in $files) {
    Write-Host "Downloading $($f.Dest | Split-Path -Leaf)..." -ForegroundColor Gray
    Invoke-RestMethod -Uri $f.Url -OutFile $f.Dest
}

# 3. Locate ArcGIS Pro Python and Install google-antigravity
Write-Host "Locating ArcGIS Pro Python environment..." -ForegroundColor Cyan
$pythonPaths = @(
    "$env:ProgramFiles\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
    "$env:LOCALAPPDATA\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
)

$targetPython = $null
foreach ($p in $pythonPaths) {
    if (Test-Path $p) {
        $targetPython = $p
        break
    }
}

if ($targetPython) {
    Write-Host "Configuring dependencies with ArcGIS Pro Python ($targetPython)..." -ForegroundColor Yellow
    Start-Process -FilePath $targetPython -ArgumentList "-m pip install --upgrade google-antigravity protobuf" -Wait -NoNewWindow
} else {
    Write-Host "Notice: ArcGIS Pro standard python path not found. If needed, pip install google-antigravity in your active ArcGIS Pro Python env." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host " SUCCESS: AntigravityGIS Installed Successfully! " -ForegroundColor Green
Write-Host " Next Steps:" -ForegroundColor White
Write-Host " 1. Launch ArcGIS Pro" -ForegroundColor White
Write-Host " 2. Open Catalog Pane (View -> Catalog Pane)" -ForegroundColor White
Write-Host " 3. Right-Click 'Toolboxes' -> 'Add Toolbox'" -ForegroundColor White
Write-Host " 4. Select: $targetDir\AntigravityGIS.pyt" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Green
