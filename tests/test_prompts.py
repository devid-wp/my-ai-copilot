"""tests/test_prompts.py — Unit tests for system prompt template and client integration"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.gemini_client import GeminiClient
from core.llm_client import NVIDIAClient
from core.prompts import SYSTEM_PROMPT_TEMPLATE


def test_system_prompt_template_placeholders():
    formatted = SYSTEM_PROMPT_TEMPLATE.format(
        project_root="/test/root",
        project_tree="file.py\nmain.py",
        current_user="testdev",
        team_activity="— нет данных —",
        git_log="abc1234 Initial commit",
        project_instructions="- Run tests",
    )
    assert "/test/root" in formatted
    assert "file.py" in formatted
    assert "Citadex" in formatted
    assert "read_file" in formatted
    assert "execute_cmd" in formatted
    assert "обычным пользователям" in formatted
    assert "Объясняй новые термины" in formatted
    assert "Если запрос только учебный" in formatted
    assert "определи намерение пользователя по смыслу всей фразы" in formatted
    assert "move_file/copy_file" in formatted
    assert "Не заявляй, что выполнил действие" in formatted
    assert "testdev" not in formatted
    assert "Пользователь:" not in formatted
    assert "abc1234" in formatted


def test_client_receives_system_prompt():
    client = NVIDIAClient(
        api_key="nvapi-test",
        system_prompt="Custom System Prompt",
        model_chat="meta/llama-3.1-8b-instruct",
        model_code="meta/llama-3.3-70b-instruct",
    )
    assert client.system_prompt == "Custom System Prompt"


def test_client_message_structure(monkeypatch):
    client = NVIDIAClient(
        api_key="nvapi-test",
        system_prompt="My Test System Prompt",
        model_chat="meta/llama-3.1-8b-instruct",
        model_code="meta/llama-3.3-70b-instruct",
    )

    called_messages = []
    called_requests = []

    class MockCompletions:
        def create(self, **kwargs):
            called_requests.append(kwargs)
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
    assert "tools" not in called_requests[0]


def test_client_enables_tools_for_agent_messages_without_keyword_routing(monkeypatch):
    client = NVIDIAClient(
        api_key="nvapi-test",
        system_prompt="system",
        model_chat="chat-model",
        model_code="tool-model",
    )
    called_requests = []

    class MockCompletions:
        def create(self, **kwargs):
            called_requests.append(kwargs)
            return []

    class MockChat:
        completions = MockCompletions()

    monkeypatch.setattr(client.client, "chat", MockChat())

    list(client.ask_stream("", messages=[{"role": "user", "content": "можешь перенетсти это?"}]))

    assert called_requests[0]["tools"]
    assert called_requests[0]["tool_choice"] == "auto"
    assert called_requests[0]["model"] == "tool-model"


def test_gemini_chat_omits_tools_but_agent_enables_them(monkeypatch):
    client = GeminiClient(api_key="test", system_prompt="system")
    called_requests = []

    class MockCompletions:
        def create(self, **kwargs):
            called_requests.append(kwargs)
            return []

    class MockChat:
        completions = MockCompletions()

    monkeypatch.setattr(client._client, "chat", MockChat())

    list(client.ask_stream("hello"))
    list(client.ask_stream("", messages=[{"role": "user", "content": "create a file"}]))

    assert "tools" not in called_requests[0]
    assert called_requests[1]["tools"]
