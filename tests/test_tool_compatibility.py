from types import SimpleNamespace

from core.tool_compatibility import (
    ToolCompatibility,
    clear_cloud_tool_cache,
    probe_cloud_tool_support,
)


def _response(tool_name=None):
    calls = (
        [SimpleNamespace(function=SimpleNamespace(name=tool_name))]
        if tool_name is not None
        else []
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=calls))]
    )


def test_cloud_tool_probe_accepts_native_call_and_caches(monkeypatch):
    requests = []

    class Completions:
        def create(self, **kwargs):
            requests.append(kwargs)
            return _response("compatibility_probe")

    monkeypatch.setattr(
        "core.tool_compatibility.OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=Completions())
        ),
    )
    clear_cloud_tool_cache()

    assert (
        probe_cloud_tool_support("nvidia", "good-model", "nvapi-key")
        is ToolCompatibility.SUPPORTED
    )
    assert (
        probe_cloud_tool_support("nvidia", "good-model", "nvapi-key")
        is ToolCompatibility.SUPPORTED
    )
    assert len(requests) == 1
    assert requests[0]["tools"][0]["function"]["name"] == "compatibility_probe"


def test_cloud_tool_probe_rejects_text_only_response(monkeypatch):
    monkeypatch.setattr(
        "core.tool_compatibility.OpenAI",
        lambda **_kwargs: SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_request: _response())
            )
        ),
    )
    clear_cloud_tool_cache()
    assert (
        probe_cloud_tool_support("openai", "weak-model", "openai-key")
        is ToolCompatibility.UNRELIABLE
    )
