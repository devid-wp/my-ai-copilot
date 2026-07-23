from types import SimpleNamespace

from core.provider_catalog import (
    clear_model_cache,
    is_nvidia_chat_model,
    nvidia_models,
    select_nvidia_model,
)


def test_nvidia_models_come_from_api_and_are_cached(monkeypatch):
    calls = []

    class Models:
        def list(self):
            calls.append(1)
            return SimpleNamespace(
                data=[
                    SimpleNamespace(id="custom/instruct"),
                    SimpleNamespace(id="nvidia/nv-embed-v1"),
                    SimpleNamespace(id="nvidia/llama-guard-4-12b"),
                ]
            )

    monkeypatch.setattr("core.provider_catalog.OpenAI", lambda **_kwargs: SimpleNamespace(models=Models()))
    clear_model_cache()
    assert nvidia_models("nvapi-test") == ["custom/instruct"]
    assert nvidia_models("nvapi-test") == ["custom/instruct"]
    assert calls == [1]
    assert select_nvidia_model("nvapi-test") == "custom/instruct"
    clear_model_cache()


def test_nvidia_catalog_excludes_non_chat_models():
    assert is_nvidia_chat_model("meta/llama-3.1-8b-instruct") is True
    assert is_nvidia_chat_model("qwen/qwen3-next-80b-a3b-instruct") is True
    assert is_nvidia_chat_model("nvidia/nv-embed-v1") is False
    assert is_nvidia_chat_model("nvidia/llama-guard-4-12b") is False
    assert is_nvidia_chat_model("meta/llama-3.2-90b-vision-instruct") is False
    assert is_nvidia_chat_model("nvidia/cosmos-reason2-8b") is False
