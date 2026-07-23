@echo off
setlocal
cd /d "%~dp0"

if exist "Citadex.exe" (
    Citadex.exe
    exit /b %errorlevel%
)

if exist "dist\Citadex.exe" (
    dist\Citadex.exe
    exit /b %errorlevel%
)

if exist ".venv\Scripts\citadex.exe" (
    .venv\Scripts\citadex.exe
    exit /b %errorlevel%
)

echo Citadex is not installed yet. Starting setup...
call setup.bat || exit /b 1
.venv\Scripts\citadex.exe
