# PowerShell Automated Add-on Installer: AntigravityGIS -> ArcGIS Pro

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  AntigravityGIS Add-on Installer for ArcGIS Pro" -ForegroundColor Cyan
Write-Host "  Runs off your Google Antigravity Account & SDK" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Locate ArcGIS Pro installation directory & Python environment
$ArcGISProDefaultPath = "C:\Program Files\ArcGIS\Pro\bin\Python"
$PythonExec = "$ArcGISProDefaultPath\envs\arcgispro-py3\python.exe"

if (-not (Test-Path $PythonExec)) {
    Write-Host "Searching system for ArcGIS Pro Python environments..." -ForegroundColor Yellow
    $FoundPython = Get-ChildItem -Path "C:\Program Files\ArcGIS\Pro", "$env:LOCALAPPDATA\Programs\ArcGIS\Pro" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($FoundPython) {
        $PythonExec = $FoundPython.FullName
    } else {
        Write-Host "[NOTICE] Could not auto-detect standard ArcGIS Pro Python at default path." -ForegroundColor Yellow
        Write-Host "Defaulting to system Python or active environment..." -ForegroundColor Yellow
        $PythonExec = (Get-Command python -ErrorAction SilentlyContinue).Source
    }
}

if ($PythonExec) {
    Write-Host "[OK] Target ArcGIS Pro Python: $PythonExec" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Could not locate a valid Python environment. Please ensure ArcGIS Pro 3.x is installed." -ForegroundColor Red
    Exit 1
}

# 2. Install google-antigravity SDK into ArcGIS Pro environment
Write-Host "`nInstalling google-antigravity SDK into target Python environment..." -ForegroundColor Yellow
& $PythonExec -m pip install --upgrade google-antigravity protobuf

if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] Pip install returned exit code $LASTEXITCODE. If the default arcgispro-py3 environment is read-only, clone the environment in ArcGIS Pro Package Manager first." -ForegroundColor Yellow
}

# 3. Deploy Toolbox Add-on into ArcGIS Pro User Toolboxes folder
$UserToolboxesDir = "$env:APPDATA\Esri\ArcGISPro\ArcToolbox\MyToolboxes\AntigravityGIS"
Write-Host "`nDeploying AntigravityGIS Add-on to User Toolboxes: $UserToolboxesDir" -ForegroundColor Yellow

if (-not (Test-Path $UserToolboxesDir)) {
    New-Item -ItemType Directory -Path $UserToolboxesDir -Force | Out-Null
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }

# Copy core files to User Toolboxes folder
Copy-Item -Path "$ScriptDir\agent_core.py" -Destination "$UserToolboxesDir\agent_core.py" -Force
Copy-Item -Path "$ScriptDir\arcgis\AntigravityGIS.pyt" -Destination "$UserToolboxesDir\AntigravityGIS.pyt" -Force

Write-Host "[OK] Toolbox and agent core copied to $UserToolboxesDir" -ForegroundColor Green

# 4. Verify Google Antigravity Account Login
Write-Host "`nChecking Google Antigravity account authentication..." -ForegroundColor Yellow
$AntigravityDir = "$env:USERPROFILE\.gemini\antigravity"
if (Test-Path $AntigravityDir) {
    Write-Host "[OK] Google Antigravity account session detected." -ForegroundColor Green
} else {
    $AgyCmd = Get-Command agy -ErrorAction SilentlyContinue
    if ($AgyCmd) {
        Write-Host "Launching 1-click Antigravity login..." -ForegroundColor Yellow
        & agy auth login
    } else {
        Write-Host "[NOTICE] Antigravity CLI not found in PATH. Please log into the Antigravity Desktop App or run 'agy auth login'." -ForegroundColor Yellow
    }
}

Write-Host "`n=================================================" -ForegroundColor Cyan
Write-Host "  AntigravityGIS Add-on Successfully Installed!  " -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "`nHow to access inside ArcGIS Pro:" -ForegroundColor White
Write-Host " 1. Open ArcGIS Pro" -ForegroundColor Gray
Write-Host " 2. In the Catalog Pane (View -> Catalog Pane), expand 'Toolboxes'" -ForegroundColor Gray
Write-Host " 3. Right-click 'Toolboxes' -> Add Toolbox" -ForegroundColor Gray
Write-Host " 4. Select: $UserToolboxesDir\AntigravityGIS.pyt" -ForegroundColor Gray
Write-Host " 5. Open 'Antigravity AI Assistant' to run prompts off your Antigravity account!`n" -ForegroundColor White

