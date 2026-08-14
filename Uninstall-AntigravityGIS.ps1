<#
.SYNOPSIS
Uninstalls the AntigravityGIS add-on from ArcGIS Pro.

.DESCRIPTION
This script deletes the installed AntigravityGIS folder and its contents from the ArcGIS Pro MyToolboxes directory.
#>

$ErrorActionPreference = 'Stop'

Write-Host "Starting Uninstallation of AntigravityGIS for ArcGIS Pro..." -ForegroundColor Cyan

$targetDir = "$env:APPDATA\Esri\ArcGISPro\ArcToolbox\MyToolboxes\AntigravityGIS"

if (Test-Path $targetDir) {
    Write-Host "Removing directory: $targetDir" -ForegroundColor Yellow
    Remove-Item -Path $targetDir -Recurse -Force
    Write-Host "AntigravityGIS has been successfully uninstalled from ArcGIS Pro." -ForegroundColor Green
} else {
    Write-Host "AntigravityGIS does not appear to be installed in the expected directory ($targetDir)." -ForegroundColor Yellow
    Write-Host "No action taken." -ForegroundColor Green
}

Write-Host ""
Write-Host "Press any key to exit..."
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
