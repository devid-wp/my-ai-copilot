@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title NVIDIA AI Copilot — Setup

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║      NVIDIA AI Copilot — Easy Install        ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── 1. Проверка Python ──────────────────────────────────────────────────────
echo  [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python не найден. Установи Python 3.10+ с https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo         %%v найден
echo.

:: ── 2. Установка зависимостей ───────────────────────────────────────────────
echo  [2/4] Установка зависимостей...
python -m pip install -r requirements.txt --quiet --progress-bar off
if errorlevel 1 (
    echo  [ERROR] Ошибка при установке зависимостей
    pause
    exit /b 1
)
echo         openai, python-dotenv, prompt_toolkit, pytest — OK
echo.

:: ── 3. Настройка .env ───────────────────────────────────────────────────────
echo  [3/4] Настройка API-ключа...
if exist .env (
    echo         .env уже существует — пропускаем
) else (
    set /p API_KEY="  Введи NVIDIA API Key (nvapi-...): "
    (
        echo NVIDIA_API_KEY=!API_KEY!
        echo NVIDIA_MODEL_CHAT=meta/llama-3.1-8b-instruct
        echo NVIDIA_MODEL_CODE=meta/llama-3.3-70b-instruct
    ) > .env
    echo         .env создан успешно
)
echo.

:: ── 4. Создание папки logs ───────────────────────────────────────────────────
echo  [4/4] Создание рабочих папок...
if not exist logs mkdir logs
echo         logs/ — OK
echo.

:: ── Готово ──────────────────────────────────────────────────────────────────
echo  ╔══════════════════════════════════════════════╗
echo  ║          Установка завершена!                ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Запуск (агентный режим):
echo    python main.py --project %CD% --agent
echo.
echo  Запуск (чат):
echo    python main.py --project %CD%
echo.
echo  Тесты:
echo    python -m pytest tests/ -v
echo.
pause
