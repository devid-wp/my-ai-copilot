"""tests/test_memory.py — Unit tests for core/memory.py"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.memory import AgentMemory


@pytest.fixture
def temp_session_file(tmp_path):
    """Creates a temporary path for session.json."""
    return os.path.join(str(tmp_path), "session.json")


def test_add_message(temp_session_file):
    memory = AgentMemory(temp_session_file)
    assert len(memory.get_history()) == 0

    memory.add("user", "Hello agent")
    assert len(memory.get_history()) == 1
    assert memory.get_history()[0]["role"] == "user"
    assert memory.get_history()[0]["content"] == "Hello agent"

    # Reload and check persistence
    new_memory = AgentMemory(temp_session_file)
    assert len(new_memory.get_history()) == 1
    assert new_memory.get_history()[0]["content"] == "Hello agent"


def test_clear_memory(temp_session_file):
    memory = AgentMemory(temp_session_file)
    memory.add("user", "To be cleared")
    assert len(memory.get_history()) == 1
    assert os.path.isfile(temp_session_file)

    memory.clear()
    assert len(memory.get_history()) == 0
    # The file should be deleted or empty list
    if os.path.isfile(temp_session_file):
        with open(temp_session_file) as f:
            data = json.load(f)
            assert len(data) == 0


def test_trim_memory(temp_session_file):
    memory = AgentMemory(temp_session_file)
    # Add system message
    memory.add("system", "You are an agent")

    # Add 10 other messages
    for i in range(10):
        memory.add("user", f"msg {i}")

    assert len(memory.get_history()) == 11

    # Trim to 5 messages
    memory.trim(5)

    history = memory.get_history()
    assert len(history) == 5

    # First must still be the system message
    assert history[0]["role"] == "system"
    assert history[0]["content"] == "You are an agent"

    # Rest should be the last 4 messages (msg 6, 7, 8, 9)
    assert history[1]["content"] == "msg 6"
    assert history[4]["content"] == "msg 9"
