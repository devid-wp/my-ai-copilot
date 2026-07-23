@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Citadex environment is missing. Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat || exit /b 1
python -m PyInstaller --noconfirm --clean Citadex.spec || exit /b 1

echo.
echo Build complete: dist\Citadex.exe
pause
