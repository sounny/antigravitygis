<#
.SYNOPSIS
Uninstalls the AntigravityGIS plugin from QGIS.

.DESCRIPTION
This script deletes the installed AntigravityGIS plugin folder from the default QGIS profile.
#>

$ErrorActionPreference = 'Stop'

Write-Host "Starting Uninstallation of AntigravityGIS for QGIS..." -ForegroundColor Cyan

$targetDir = "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\antigravitygis"

if (Test-Path $targetDir) {
    Write-Host "Removing directory: $targetDir" -ForegroundColor Yellow
    Remove-Item -Path $targetDir -Recurse -Force
    Write-Host "AntigravityGIS has been successfully uninstalled from QGIS." -ForegroundColor Green
} else {
    Write-Host "AntigravityGIS does not appear to be installed in the expected directory ($targetDir)." -ForegroundColor Yellow
    Write-Host "No action taken." -ForegroundColor Green
}

Write-Host ""
Write-Host "Press any key to exit..."
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
