@echo off
setlocal EnableExtensions
title Citadex API Setup
cd /d "%~dp0"

echo.
echo ==========================================================
echo   CITADEX - EASY API SETUP
echo ==========================================================
echo.

set "PYTHON_EXE="
for /f "usebackq delims=" %%P in (`py -3.12 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYTHON_EXE=%%P"

if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
)

if not defined PYTHON_EXE (
    where winget >nul 2>nul
    if errorlevel 1 goto :no_python
    echo Python 3.12 was not found. Installing it with winget...
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :install_error
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
)

if not exist "%PYTHON_EXE%" goto :no_python

set "RUNTIME_DIR=%LocalAppData%\Citadex\runtime"
if not exist "%RUNTIME_DIR%\Scripts\python.exe" (
    echo Creating a private Citadex environment...
    "%PYTHON_EXE%" -m venv "%RUNTIME_DIR%"
    if errorlevel 1 goto :install_error
)

echo Installing or updating Citadex...
"%RUNTIME_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet --upgrade "%~dp0"
if errorlevel 1 goto :install_error

echo Starting Citadex...
echo Your API key will be hidden while you type or paste it.
echo.
"%RUNTIME_DIR%\Scripts\python.exe" -m citadex_api
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" exit /b 0

echo.
echo Citadex exited with error code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%

:no_python
echo.
echo Python 3.12 could not be found or installed.
echo Install it from https://www.python.org/downloads/windows/
pause
exit /b 2

:install_error
echo.
echo Installation failed. Check your internet connection and run this file again.
pause
exit /b 2
