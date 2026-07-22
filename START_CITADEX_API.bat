@echo off
setlocal EnableExtensions
title Citadex API Setup
cd /d "%~dp0"

echo.
echo ==========================================================
echo   CITADEX - prostaya ustanovka API-versii
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
    echo Python 3.12 ne nayden. Ustanavlivayu cherez winget...
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :install_error
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
)

if not exist "%PYTHON_EXE%" goto :no_python

set "RUNTIME_DIR=%LocalAppData%\Citadex\runtime"
if not exist "%RUNTIME_DIR%\Scripts\python.exe" (
    echo Sozdayu bezopasnoe okruzhenie Citadex...
    "%PYTHON_EXE%" -m venv "%RUNTIME_DIR%"
    if errorlevel 1 goto :install_error
)

echo Ustanavlivayu ili obnovlyayu Citadex...
"%RUNTIME_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet --upgrade "%~dp0"
if errorlevel 1 goto :install_error

echo Zapuskayu Citadex...
echo API-klyuch pri vvode ne budet pokazan na ekrane.
echo.
"%RUNTIME_DIR%\Scripts\python.exe" -m citadex_api
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" exit /b 0

echo.
echo Citadex zavershilsya s oshibkoy %EXIT_CODE%.
pause
exit /b %EXIT_CODE%

:no_python
echo.
echo Ne udalos nayti ili ustanovit Python 3.12.
echo Ustanovite ego s https://www.python.org/downloads/windows/
pause
exit /b 2

:install_error
echo.
echo Oshibka ustanovki. Proverte internet i povtorite zapusk.
pause
exit /b 2
