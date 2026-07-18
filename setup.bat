@echo off
setlocal
cd /d "%~dp0"
python -m venv .venv || exit /b 1
call .venv\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
python -m pip install -e ".[dev]" || exit /b 1
if not exist .env copy .env.example .env >nul
echo.
echo Citadex installed. Edit .env, then run: citadex --help
