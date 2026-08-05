# Citadex

Citadex is a safety-focused terminal coding agent for Windows and Python projects. It can inspect a workspace, edit files, run commands and tests, preview changes, and undo the latest file operation.

## Editions

- **Citadex Local** — an offline agent powered by Qwen2.5-Coder 1.5B Q4_K_M.
- **Citadex API** — supports NVIDIA, OpenAI, and Ollama-compatible endpoints.

## Installation

Windows users can download the lightweight installer from the latest release. The installer downloads and verifies the local model during setup.

To install the Python package from source:

```powershell
python -m pip install .
citadex
```

See the [installation guide](docs/INSTALLATION.md) for all available options.

## Essential commands

```text
/mode          Switch between chat and agent mode
/permissions   Configure tool approval
/project       Change the active workspace
/status        Show runtime diagnostics
/undo          Restore the latest changed file
/doctor        Check the environment
/help          Show all commands
```

API builds also provide `/provider`, `/model`, and `/keys`.

## Safety

Citadex restricts file tools to the selected workspace unless the user explicitly grants access. Agent mode limits tool calls, prevents identical failed retries, previews edits, creates undo backups, and verifies modified files before reporting completion.

Automatic approval removes an important safety boundary. Enable it only inside a trusted workspace.

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Local runtime](docs/LOCAL_RUNTIME.md)
- [Development](docs/DEVELOPMENT.md)
- [Releasing](docs/RELEASING.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## License

Citadex is released under the [MIT License](LICENSE). Third-party components and downloaded models retain their respective licenses.
