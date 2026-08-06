"""Windows entry point for the portable Qwen-powered Citadex build."""

from __future__ import annotations

import sys
from pathlib import Path

from core.config_profiles import ConfigProfile, save_active_profile
from core.local_runtime import (
    LOCAL_MODEL_ID,
    start_local_server,
    stop_local_server,
)
from main import main as citadex_main


def run(argv: list[str] | None = None) -> int:
    print("\nCITADEX LOCAL · Qwen2.5-Coder 1.5B\n")
    print("Starting the built-in model. The first launch can take up to two minutes...")
    process = None
    try:
        process = start_local_server()
        save_active_profile(
            "bundled-local",
            ConfigProfile(
                name="Bundled Local",
                provider="local",
                model=LOCAL_MODEL_ID,
                mode="agent",
                permissions="ask",
                project_root=str(Path.cwd().resolve()),
            ),
        )
        return citadex_main(
            [
                *(sys.argv[1:] if argv is None else argv),
                "--project",
                str(Path.cwd()),
                "--agent",
                "--local-only",
            ]
        )
    except (OSError, RuntimeError, TimeoutError) as exc:
        print(f"\nLocal model startup failed: {exc}", file=sys.stderr)
        return 2
    finally:
        stop_local_server(process)


if __name__ == "__main__":
    raise SystemExit(run())
