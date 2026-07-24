import json

from core.llm_client import NVIDIAClient
from core.local_client import LocalClient
from core.local_runtime import LOCAL_MODEL_ID


def test_local_client_uses_one_bundled_model():
    client = LocalClient("system")

    assert client.provider_name == "LOCAL QWEN"
    assert client.model_chat == LOCAL_MODEL_ID
    assert client.model_code == LOCAL_MODEL_ID
    assert str(client.client.base_url).startswith("http://127.0.0.1:11435/v1/")


def test_local_client_converts_strict_json_fallback_to_tool_call(monkeypatch):
    def fake_stream(self, prompt, context="", messages=None):
        self._last_tool_calls = []
        yield '{"name":"create_file","arguments":{"path":"hello.txt","content":"hello"}}'

    monkeypatch.setattr(NVIDIAClient, "ask_stream", fake_stream)
    client = LocalClient("system")

    response = "".join(client.ask_stream("", messages=[{"role": "user", "content": "create"}]))

    assert response.startswith('{"name"')
    call = client.get_last_tool_calls()[0]
    assert call["function"]["name"] == "create_file"
    assert json.loads(call["function"]["arguments"]) == {
        "path": "hello.txt",
        "content": "hello",
    }
