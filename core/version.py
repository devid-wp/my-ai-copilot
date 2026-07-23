"""Installed Citadex package version."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    try:
        return version("citadex")
    except PackageNotFoundError:
        return "0.1.0"


__version__ = get_version()

__all__ = ["__version__", "get_version"]
