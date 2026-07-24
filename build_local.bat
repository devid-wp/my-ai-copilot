@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_local.ps1"
if errorlevel 1 (
    echo.
    echo Citadex Local build failed.
    pause
    exit /b 1
)

echo.
echo Citadex Local is ready.
pause
