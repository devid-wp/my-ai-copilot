"""tests/test_prompts.py — Unit tests for system prompt template and client integration"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.prompts import SYSTEM_PROMPT_TEMPLATE
from core.llm_client import NVIDIAClient

def test_system_prompt_template_placeholders():
    formatted = SYSTEM_PROMPT_TEMPLATE.format(
        project_root="/test/root",
        project_tree="file.py\nmain.py"
    )
    assert "/test/root" in formatted
    assert "file.py" in formatted
    assert "автономный агент-разработчик" in formatted
    assert "ЗАДАЧА ВЫПОЛНЕНА:" in formatted
    assert "read_file" in formatted
    assert "execute_cmd" in formatted

def test_client_receives_system_prompt():
    client = NVIDIAClient(
        api_key="nvapi-test",
        system_prompt="Custom System Prompt",
        model_chat="meta/llama-3.1-8b-instruct",
        model_code="meta/llama-3.3-70b-instruct"
    )
    assert client.system_prompt == "Custom System Prompt"

def test_client_message_structure(monkeypatch):
    client = NVIDIAClient(
        api_key="nvapi-test",
        system_prompt="My Test System Prompt",
        model_chat="meta/llama-3.1-8b-instruct",
        model_code="meta/llama-3.3-70b-instruct"
    )

    called_messages = []

    class MockCompletions:
        def create(self, **kwargs):
            called_messages.extend(kwargs.get("messages", []))
            return []

    class MockChat:
        completions = MockCompletions()

    monkeypatch.setattr(client.client, "chat", MockChat())

    # Consume the generator
    list(client.ask_stream("Hello model"))

    assert len(called_messages) == 2
    assert called_messages[0]["role"] == "system"
    assert called_messages[0]["content"] == "My Test System Prompt"
    assert called_messages[1]["role"] == "user"
    assert called_messages[1]["content"] == "Hello model"
