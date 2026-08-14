<#
.SYNOPSIS
Installs the AntigravityGIS plugin for QGIS.

.DESCRIPTION
This script attempts to locate a Python environment and uses it to launch the QGIS installer GUI.
#>

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "Locating Python environment for QGIS Installer..." -ForegroundColor Cyan

$pythonExe = $null

# QGIS is usually installed in Program Files and has a variable version number.
# We will check common locations or default to system Python.
$qgisPaths = Get-ChildItem -Path "$env:ProgramFiles\QGIS*" -Directory -ErrorAction SilentlyContinue | 
             Select-Object -ExpandProperty FullName

foreach ($path in $qgisPaths) {
    # Check common python directories inside QGIS
    $pyDirs = Get-ChildItem -Path "$path\apps\Python*" -Directory -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    foreach ($pyDir in $pyDirs) {
        $testPath = Join-Path $pyDir "pythonw.exe"
        if (Test-Path $testPath) {
            $pythonExe = $testPath
            break
        }
    }
    if ($pythonExe) { break }
}

if (-not $pythonExe) {
    Write-Host "Could not find a QGIS-bundled Python. Using system Python instead..." -ForegroundColor Yellow
    $pythonExe = "pythonw.exe"
}

$installerScript = Join-Path $ScriptDir "qgis\qgis_installer_gui.py"

if (-not (Test-Path $installerScript)) {
    Write-Error "Could not find qgis\qgis_installer_gui.py relative to this script."
}

Write-Host "Launching AntigravityGIS QGIS Installer GUI..." -ForegroundColor Green
Start-Process -FilePath $pythonExe -ArgumentList "`"$installerScript`"" -NoNewWindow
