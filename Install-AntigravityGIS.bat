@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-AntigravityGIS.ps1"
if %errorlevel% neq 0 (
    pause
)
