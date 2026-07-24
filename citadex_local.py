"""Windows entry point for the portable Qwen-powered Citadex build."""

from __future__ import annotations

import sys
from pathlib import Path

from core.local_runtime import (
    LOCAL_MODEL_ID,
    start_local_server,
    stop_local_server,
)
from main import main as citadex_main


def run() -> int:
    print("\nCITADEX LOCAL · Qwen2.5-Coder 3B\n")
    print("Starting the built-in model. The first launch can take up to two minutes...")
    process = None
    try:
        process = start_local_server()
        return citadex_main(
            [
                "--project",
                str(Path.cwd()),
                "--provider",
                "local",
                "--model",
                LOCAL_MODEL_ID,
                "--agent",
                "--skip-setup",
            ]
        )
    except (OSError, RuntimeError, TimeoutError) as exc:
        print(f"\nLocal model startup failed: {exc}", file=sys.stderr)
        return 2
    finally:
        stop_local_server(process)


if __name__ == "__main__":
    raise SystemExit(run())
