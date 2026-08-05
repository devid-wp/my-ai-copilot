from types import SimpleNamespace

from core.credential_probe import probe_provider_key


def test_nvidia_key_probe_is_bounded_and_lists_models(monkeypatch):
    captured = {}

    class Models:
        def list(self):
            captured["listed"] = True
            return SimpleNamespace()

    def fake_openai(**kwargs):
        captured["client"] = kwargs
        return SimpleNamespace(models=Models())

    monkeypatch.setattr("core.credential_probe.OpenAI", fake_openai)

    probe_provider_key("nvidia", "nvapi-test")

    assert captured["client"]["max_retries"] == 0
    assert captured["client"]["timeout"].read == 15
    assert captured["listed"] is True
