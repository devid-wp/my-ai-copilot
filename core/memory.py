# core/memory.py
"""Persistent conversation memory for the agent."""
import os
import json
from typing import List, Dict, Any

class AgentMemory:
    """Stores conversation history on disk, preserving first system message during trimming."""

    def __init__(self, session_path: str = "logs/session.json"):
        self.session_path = session_path
        self.history: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load history from json file if it exists."""
        if os.path.isfile(self.session_path):
            try:
                with open(self.session_path, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def _save(self) -> None:
        """Save history to json file, creating directories if missing."""
        dir_name = os.path.dirname(self.session_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        try:
            with open(self.session_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the history and persist to disk."""
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self.history.append(msg)
        self._save()

    def get_history(self) -> List[Dict[str, Any]]:
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
            rest = self.history[-(max_messages - 1):]
            self.history = [first] + rest
        else:
            self.history = self.history[-max_messages:]
        self._save()
