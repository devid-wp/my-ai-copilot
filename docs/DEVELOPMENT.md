# Development

## Setup

```powershell
.\setup.bat
```

Or install manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Quality checks

```powershell
python -m pytest -q
python -m ruff check citadex_local.py citadex_api.py citadex_smoke.py citadex_windows.py main.py core tests
python -m mypy citadex_local.py citadex_api.py citadex_smoke.py citadex_windows.py main.py core
```

## Repository layout

```text
core/                  Agent runtime, providers, tools, safety, and UI
tests/                 Regression and integration tests
assets/                Application icons
docs/                  User and maintainer documentation
main.py                Main CLI entry point
citadex_local.py       Offline Windows entry point
citadex_api.py         API-oriented Windows launcher
CitadexLocalSetup.iss  Windows web-installer definition
```

Keep generated builds, virtual environments, credentials, caches, and model
files out of Git.
