from types import SimpleNamespace

from core.provider_catalog import (
    clear_model_cache,
    is_nvidia_chat_model,
    nvidia_models,
    recommended_nvidia_models,
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

    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(models=Models())

    monkeypatch.setattr("core.provider_catalog.OpenAI", fake_openai)
    clear_model_cache()
    assert nvidia_models("nvapi-test") == ["custom/instruct"]
    assert nvidia_models("nvapi-test") == ["custom/instruct"]
    assert calls == [1]
    assert captured["max_retries"] == 0
    assert captured["timeout"].read == 15
    assert select_nvidia_model("nvapi-test") == "custom/instruct"
    clear_model_cache()


def test_nvidia_catalog_excludes_non_chat_models():
    assert is_nvidia_chat_model("meta/llama-3.1-8b-instruct") is True
    assert is_nvidia_chat_model("qwen/qwen3-next-80b-a3b-instruct") is True
    assert is_nvidia_chat_model("nvidia/nv-embed-v1") is False
    assert is_nvidia_chat_model("nvidia/llama-guard-4-12b") is False
    assert is_nvidia_chat_model("meta/llama-3.2-90b-vision-instruct") is False
    assert is_nvidia_chat_model("nvidia/cosmos-reason2-8b") is False


def test_recommended_nvidia_menu_is_short_and_prioritized(monkeypatch):
    models = [
        "abacusai/dracarys-llama-3.1-70b-instruct",
        "deepseek-ai/deepseek-v4-flash",
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.3-70b-instruct",
        "mistralai/mistral-7b-instruct-v0.3",
        "nvidia/nemotron-mini-4b-instruct",
        "openai/gpt-oss-20b",
        "qwen/qwen3-next-80b-a3b-instruct",
        "stepfun-ai/step-3.5-flash",
        "z-ai/glm-5.2",
        "google/gemma-3-12b-it",
        "mistralai/codestral-22b-instruct-v0.1",
        "moonshotai/kimi-k2.6",
    ]
    monkeypatch.setattr("core.provider_catalog.nvidia_models", lambda _key: models)

    menu = recommended_nvidia_models("nvapi-test")

    assert len(menu) == 12
    assert menu[:4] == [
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.3-70b-instruct",
        "stepfun-ai/step-3.5-flash",
        "deepseek-ai/deepseek-v4-flash",
    ]
