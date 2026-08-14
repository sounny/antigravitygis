<#
.SYNOPSIS
Installs the AntigravityGIS add-on for ArcGIS Pro.

.DESCRIPTION
This script locates the active ArcGIS Pro Python environment and uses it to launch the Python-based installer GUI.
#>

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "Locating ArcGIS Pro Python environment..." -ForegroundColor Cyan

$pythonExe = $null

# Common installation paths for ArcGIS Pro Python
$paths = @(
    "$env:ProgramFiles\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe",
    "$env:LOCALAPPDATA\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe"
)

foreach ($p in $paths) {
    if (Test-Path $p) {
        $pythonExe = $p
        break
    }
}

if (-not $pythonExe) {
    Write-Host "Could not find ArcGIS Pro Python environment. Attempting to use system Python..." -ForegroundColor Yellow
    $pythonExe = "pythonw.exe"
}

$installerScript = Join-Path $ScriptDir "installer_gui.py"

if (-not (Test-Path $installerScript)) {
    Write-Error "Could not find installer_gui.py in the same directory as this script."
}

Write-Host "Launching AntigravityGIS Installer GUI..." -ForegroundColor Green
Start-Process -FilePath $pythonExe -ArgumentList "`"$installerScript`"" -NoNewWindow
