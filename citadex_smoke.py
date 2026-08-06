"""Opt-in live provider smoke test; never runs as part of pytest."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from core.config_profiles import ConfigProfile
from core.credentials import PROVIDER_API_KEYS
from core.provider_runtime import explain_provider_error
from core.tool_smoke import run_live_tool_smoke
from main import create_client


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an isolated live native-tool smoke test")
    parser.add_argument("--provider", choices=("nvidia", "openai"), required=True)
    parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)
    try:
        defaults = {"nvidia": "meta/llama-3.1-8b-instruct", "openai": "gpt-5.6"}
        profile = ConfigProfile(
            name="Live smoke test",
            provider=args.provider,
            model=args.model or defaults[args.provider],
            project_root=str(Path.cwd()),
        )
        client = create_client(
            profile,
            os.getenv(PROVIDER_API_KEYS[args.provider], ""),
            "Native tool smoke test.",
        )
        print(f"Testing {args.provider.upper()} native tool calling...")
        completed = run_live_tool_smoke(client)
    except Exception as exc:
        print(explain_provider_error(exc, args.provider.upper()), file=sys.stderr)
        return 2
    print("PASS: " + " -> ".join(completed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
