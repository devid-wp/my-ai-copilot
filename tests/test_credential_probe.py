from types import SimpleNamespace

from core.credential_probe import probe_provider_key


def test_nvidia_key_probe_is_small_bounded_and_does_not_list_models(monkeypatch):
    captured = {}

    class Completions:
        def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace()

    def fake_openai(**kwargs):
        captured["client"] = kwargs
        return SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    monkeypatch.setattr("core.credential_probe.OpenAI", fake_openai)

    probe_provider_key("nvidia", "nvapi-test")

    assert captured["client"]["max_retries"] == 0
    assert captured["client"]["timeout"].read == 15
    assert captured["request"]["model"] == "meta/llama-3.1-8b-instruct"
    assert captured["request"]["max_tokens"] == 2
    assert captured["request"]["stream"] is False
