from core.config_profiles import ConfigProfile
from main import create_client


def profile(tmp_path, provider, model):
    return ConfigProfile(
        name="Factory test",
        provider=provider,
        model=model,
        project_root=str(tmp_path),
    )


def test_openai_factory_uses_only_profile_model_and_explicit_key(tmp_path, monkeypatch):
    received = []
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    monkeypatch.setenv("OPENAI_MODEL", "environment-model")
    monkeypatch.setattr(
        "core.llm_client.OpenAIClient",
        lambda *args, **kwargs: received.append((args, kwargs)) or object(),
    )

    create_client(profile(tmp_path, "openai", "profile-model"), "profile-key", "system")

    assert received == [
        (
            ("profile-key", "system"),
            {"model_chat": "profile-model", "model_code": "profile-model"},
        )
    ]


def test_nvidia_factory_does_not_fall_back_to_environment_key(tmp_path, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "environment-key")

    try:
        create_client(profile(tmp_path, "nvidia", "profile-model"), "", "system")
    except ValueError as exc:
        assert "API_KEY" in str(exc)
    else:
        raise AssertionError("an explicit profile key must be required")


def test_ollama_factory_uses_profile_model_for_both_routes(tmp_path, monkeypatch):
    received = []
    monkeypatch.setenv("OLLAMA_MODEL_CHAT", "environment-chat")
    monkeypatch.setenv("OLLAMA_MODEL_CODE", "environment-code")
    monkeypatch.setattr(
        "core.ollama_client.OllamaClient",
        lambda *args, **kwargs: received.append((args, kwargs)) or object(),
    )

    create_client(profile(tmp_path, "ollama", "profile-model"), "", "system")

    assert received == [
        (
            ("system",),
            {
                "model_chat": "profile-model",
                "model_code": "profile-model",
                "base_url": "http://localhost:11434",
            },
        )
    ]
