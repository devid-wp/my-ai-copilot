# core/memory.py
"""Persistent conversation memory for the agent with team/multi-user support."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AgentMemory:
    """Stores conversation history on disk, preserving first system message during trimming.

    Each message entry includes optional ``user`` and ``timestamp`` fields
    for collaborative/team mode.
    """

    def __init__(self, session_path: str = "logs/session.json", username: str = "dev"):
        self.session_path = session_path
        self.username = username
        self.history: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load history from json file if it exists."""
        if os.path.isfile(self.session_path):
            try:
                with open(self.session_path, encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def _save(self) -> None:
        """Persist history atomically so an interrupted write cannot corrupt it."""
        path = Path(self.session_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)

    def save(self) -> None:
        """Public persistence hook used after replacing the system prompt."""
        self._save()

    def add(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the history and persist to disk.

        Automatically stamps each message with the current UTC timestamp
        and the current username for team-mode traceability.
        """
        msg: dict[str, Any] = {
            "role": role,
            "content": content,
            "user": self.username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        msg.update(kwargs)
        self.history.append(msg)
        self._save()

    def get_history(self) -> list[dict[str, Any]]:
        """Return the current list of messages."""
        return self.history

    def clear(self) -> None:
        """Clear all history and delete/empty the session file."""
        self.history = []
        if os.path.isfile(self.session_path):
            try:
                os.remove(self.session_path)
            except Exception:
                self._save()
        else:
            self._save()

    def trim(self, max_messages: int = 50) -> None:
        """Keep the last max_messages but always preserve the first (system) message."""
        if len(self.history) <= max_messages:
            return
        if not self.history:
            return

        first = self.history[0]
        if first.get("role") == "system":
            # Keep the system message, and take the last (max_messages - 1) messages from the rest
            rest = self.history[-(max_messages - 1) :]
            self.history = [first] + rest
        else:
            self.history = self.history[-max_messages:]
        self._save()

    def get_summary(self) -> str:
        """Return the last 5 non-system actions as a short human-readable string.

        Used to inject recent team activity into the system prompt.
        """
        non_system = [m for m in self.history if m.get("role") != "system"]
        recent = non_system[-5:]
        if not recent:
            return ""

        lines = []
        for m in recent:
            role = m.get("role", "?")
            user = m.get("user", "dev")
            ts = m.get("timestamp", "")[:16].replace("T", " ")  # "YYYY-MM-DD HH:MM"
            content_preview = str(m.get("content", ""))[:80].replace("\n", " ")
            lines.append(f"[{ts}] {user} ({role}): {content_preview}")
        return "\n".join(lines)
