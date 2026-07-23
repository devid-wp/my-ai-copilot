@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "CITADEX_PYTHON=py -3"
) else (
    where python >nul 2>nul || (
        echo Python 3.10-3.13 is required.
        echo Download it from https://www.python.org/downloads/windows/
        pause
        exit /b 1
    )
    set "CITADEX_PYTHON=python"
)

%CITADEX_PYTHON% -m venv .venv || exit /b 1
call .venv\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
python -m pip install -e ".[dev]" || exit /b 1
if not exist .env copy .env.example .env >nul
echo.
echo Citadex is ready.
echo Run: .venv\Scripts\citadex.exe
pause
