"""Local release and runtime diagnostics for the /doctor command."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from core.credentials import PROVIDER_API_KEYS


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def collect_doctor_checks(
    project_root: str,
    provider: str,
    model: str,
    available_models: list[str] | None,
    *,
    ollama_online: bool,
) -> list[DoctorCheck]:
    root = Path(project_root)
    python_supported = (3, 10) <= sys.version_info[:2] < (3, 14)
    key_name = PROVIDER_API_KEYS.get(provider)
    key_ready = key_name is None or bool(os.getenv(key_name, "").strip())
    model_ready = available_models is not None and model in available_models
    return [
        DoctorCheck(
            "Python",
            python_supported,
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ),
        DoctorCheck("Project", root.is_dir(), str(root.resolve())),
        DoctorCheck("Write access", root.is_dir() and os.access(root, os.W_OK), str(root.resolve())),
        DoctorCheck("Git", shutil.which("git") is not None, shutil.which("git") or "not found"),
        DoctorCheck("API key", key_ready, "configured" if key_ready else f"{key_name} is missing"),
        DoctorCheck(
            "Model",
            model_ready,
            model if model_ready else f"{model} is unavailable for {provider}",
        ),
        DoctorCheck("Ollama", ollama_online, "online" if ollama_online else "offline (optional)"),
    ]


__all__ = ["DoctorCheck", "collect_doctor_checks"]
