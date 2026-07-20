import json

import httpx
import pytest

from core.ollama_client import OllamaClient


class FakeStreamResponse:
    def __init__(self, chunks):
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def raise_for_status(self):
        return None

    def iter_lines(self):
        return (json.dumps(chunk) for chunk in self.chunks)


def test_agent_request_sends_tools_and_normalizes_tool_calls(monkeypatch):
    captured = {}
    response = FakeStreamResponse(
        [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "create_file",
                                "arguments": {"path": "page.html", "content": "<h1>Hello</h1>"},
                            }
                        }
                    ],
                },
                "done": True,
            }
        ]
    )

    def fake_stream(_method, _url, **kwargs):
        captured.update(kwargs["json"])
        return response

    monkeypatch.setattr("core.ollama_client.httpx.stream", fake_stream)
    client = OllamaClient("system", model_chat="qwen2.5-coder:1.5b")

    output = list(
        client.ask_stream(
            "",
            messages=[
                {"role": "system", "content": "Use tools."},
                {"role": "user", "content": "Create page.html"},
            ],
        )
    )

    assert output == []
    assert captured["tools"]
    assert captured["messages"][0] == {"role": "system", "content": "Use tools."}
    tool_call = client.get_last_tool_calls()[0]
    assert tool_call["function"]["name"] == "create_file"
    assert json.loads(tool_call["function"]["arguments"])["path"] == "page.html"


def test_chat_request_does_not_enable_tools(monkeypatch):
    captured = {}

    def fake_stream(_method, _url, **kwargs):
        captured.update(kwargs["json"])
        return FakeStreamResponse([{"message": {"content": "hello"}, "done": True}])

    monkeypatch.setattr("core.ollama_client.httpx.stream", fake_stream)
    client = OllamaClient("system", model_chat="qwen2.5:3b")

    assert "".join(client.ask_stream("hello")) == "hello"
    assert "tools" not in captured
    assert captured["messages"][0] == {"role": "system", "content": "system"}


def test_tool_history_is_converted_to_ollama_format():
    messages = OllamaClient._clean_messages(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": '{"path":"a.py"}'},
                    }
                ],
            },
            {"role": "tool", "name": "read_file", "content": '{"content":"x"}'},
        ]
    )

    assert messages[0]["tool_calls"][0]["function"]["arguments"] == {"path": "a.py"}
    assert messages[1]["role"] == "tool"
    assert messages[1]["tool_name"] == "read_file"


def test_http_error_is_not_silently_swallowed(monkeypatch):
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    failed_response = httpx.Response(
        404,
        request=request,
        headers={"content-type": "application/json"},
        stream=httpx.ByteStream(b'{"error":"model not found"}'),
    )

    class FailedStreamContext:
        def __enter__(self):
            return failed_response

        def __exit__(self, *_args):
            failed_response.close()

    monkeypatch.setattr(
        "core.ollama_client.httpx.stream",
        lambda *_args, **_kwargs: FailedStreamContext(),
    )
    client = OllamaClient("system", model_chat="missing")

    with pytest.raises(RuntimeError, match="Ollama HTTP 404: model not found"):
        list(client.ask_stream("hello"))
