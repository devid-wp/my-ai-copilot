from types import SimpleNamespace

from core.provider_catalog import clear_model_cache, nvidia_models, select_nvidia_model


def test_nvidia_models_come_from_api_and_are_cached(monkeypatch):
    calls = []

    class Models:
        def list(self):
            calls.append(1)
            return SimpleNamespace(data=[SimpleNamespace(id="custom/instruct"), SimpleNamespace(id="other")])

    monkeypatch.setattr("core.provider_catalog.OpenAI", lambda **_kwargs: SimpleNamespace(models=Models()))
    clear_model_cache()
    assert nvidia_models("nvapi-test") == ["custom/instruct", "other"]
    assert nvidia_models("nvapi-test") == ["custom/instruct", "other"]
    assert calls == [1]
    assert select_nvidia_model("nvapi-test") == "custom/instruct"
    clear_model_cache()
