"""Lifecycle management for the portable llama.cpp runtime."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LOCAL_MODEL_ID = "qwen2.5-coder-3b-instruct-q4_k_m"
LOCAL_MODEL_FILENAME = "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
LOCAL_PORT = 11435
LOCAL_BASE_URL = f"http://127.0.0.1:{LOCAL_PORT}"


def bundle_root() -> Path:
    override = os.getenv("CITADEX_LOCAL_BUNDLE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def runtime_paths(root: Path | None = None) -> tuple[Path, Path]:
    base = (root or bundle_root()).resolve()
    return base / "runtime" / "llama-server.exe", base / "models" / LOCAL_MODEL_FILENAME


def local_server_online(base_url: str = LOCAL_BASE_URL) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=2) as response:
            payload = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return False
    return payload.get("status") == "ok"


def start_local_server(
    root: Path | None = None,
    *,
    timeout: float = 180,
) -> subprocess.Popen[bytes] | None:
    """Start the bundled server and wait until the model is ready."""
    if local_server_online():
        return None
    executable, model = runtime_paths(root)
    if not executable.is_file():
        raise FileNotFoundError(f"Local runtime is missing: {executable}")
    if not model.is_file():
        raise FileNotFoundError(f"Local model is missing: {model}")

    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW
    process = subprocess.Popen(
        [
            str(executable),
            "--model",
            str(model),
            "--host",
            "127.0.0.1",
            "--port",
            str(LOCAL_PORT),
            "--ctx-size",
            "8192",
            "--jinja",
        ],
        cwd=str(executable.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server stopped with exit code {process.returncode}.")
        if local_server_online():
            return process
        time.sleep(0.5)
    process.terminate()
    raise TimeoutError("Qwen model did not become ready within 180 seconds.")


def stop_local_server(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


__all__ = [
    "LOCAL_BASE_URL",
    "LOCAL_MODEL_FILENAME",
    "LOCAL_MODEL_ID",
    "LOCAL_PORT",
    "bundle_root",
    "local_server_online",
    "runtime_paths",
    "start_local_server",
    "stop_local_server",
]
