# Installation

## Windows installer

Download `Citadex-Local-Web-Setup-<version>.exe` from the latest release.

The installer:

1. asks for an installation directory;
2. downloads the official Qwen2.5-Coder 1.5B Q4_K_M model;
3. verifies the model SHA-256 checksum;
4. installs Citadex and the bundled llama.cpp runtime;
5. creates optional desktop and Start menu shortcuts.

An internet connection is required only during installation. Citadex Local runs
offline afterwards.

Running the installer again offers three maintenance choices:

- reinstall Citadex;
- uninstall Citadex and the model;
- cancel without changing the installation.

## Python package

Citadex requires Python 3.10–3.13.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
citadex
```

For an editable development installation:

```powershell
python -m pip install -e ".[dev]"
```

## API edition

Copy `.env.example` to `.env` and add the key for the provider you use:

```dotenv
NVIDIA_API_KEY=nvapi-...
GEMINI_API_KEY=...
```

Keys can also be managed inside Citadex with `/keys`. Stored key values are
never printed.

