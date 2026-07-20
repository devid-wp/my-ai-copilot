"""Local API credential storage outside the active source project."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv, set_key

PROVIDER_API_KEYS = {
    "nvidia": "NVIDIA_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def credentials_path() -> Path:
    """Return the per-user Citadex environment file."""
    configured = os.getenv("CITADEX_CONFIG_DIR")
    if configured:
        directory = Path(configured).expanduser()
    elif os.name == "nt" and os.getenv("APPDATA"):
        directory = Path(os.environ["APPDATA"]) / "Citadex"
    else:
        directory = Path.home() / ".config" / "citadex"
    return directory / ".env"


def load_credentials(path: Path | None = None) -> None:
    """Load saved keys without replacing explicit process environment values."""
    credential_file = path or credentials_path()
    if credential_file.is_file():
        load_dotenv(credential_file, override=False)


def validate_api_key(provider: str, api_key: str) -> str:
    """Validate a provider key without exposing it in an error message."""
    normalized_provider = provider.casefold()
    if normalized_provider not in PROVIDER_API_KEYS:
        raise ValueError(f"Provider does not use an API key: {provider}")
    value = api_key.strip()
    if not value:
        raise ValueError("API-ключ не может быть пустым.")
    if normalized_provider == "nvidia" and not value.startswith("nvapi-"):
        raise ValueError("NVIDIA API-ключ должен начинаться с nvapi-.")
    return value


def save_api_key(provider: str, api_key: str, path: Path | None = None) -> Path:
    """Persist one provider key and expose it to the current process."""
    environment_name = PROVIDER_API_KEYS.get(provider.casefold())
    if environment_name is None:
        raise ValueError(f"Provider does not use an API key: {provider}")
    value = validate_api_key(provider, api_key)

    credential_file = path or credentials_path()
    credential_file.parent.mkdir(parents=True, exist_ok=True)
    credential_file.touch(exist_ok=True)
    set_key(str(credential_file), environment_name, value, quote_mode="always")
    if os.name != "nt":
        credential_file.chmod(0o600)
    os.environ[environment_name] = value
    return credential_file


__all__ = [
    "PROVIDER_API_KEYS",
    "credentials_path",
    "load_credentials",
    "save_api_key",
    "validate_api_key",
]
