<#
.SYNOPSIS
Unified 1-Line Web Installer for AntigravityGIS
Usage in PowerShell:
irm https://raw.githubusercontent.com/sounny/antigravitygis/main/install.ps1 | iex
#>

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Clear-Host
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      AntigravityGIS by Moulay Anwar Sounny-Slitine, PhD   " -ForegroundColor Cyan
Write-Host "          1-Click PowerShell Enterprise Installer         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Choose an installation option:" -ForegroundColor Yellow
Write-Host "  [1] Install for Esri ArcGIS Pro" -ForegroundColor White
Write-Host "  [2] Install for QGIS Desktop" -ForegroundColor White
Write-Host "  [3] Install for Both (ArcGIS Pro + QGIS)" -ForegroundColor Green
Write-Host "  [Q] Quit" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Enter your selection (1/2/3/Q)"

if ($choice -eq '1' -or $choice -eq '3') {
    irm https://raw.githubusercontent.com/sounny/antigravitygis/main/install-arcgis.ps1 | iex
}

if ($choice -eq '2' -or $choice -eq '3') {
    irm https://raw.githubusercontent.com/sounny/antigravitygis/main/install-qgis.ps1 | iex
}
