from types import SimpleNamespace

from core.credential_probe import probe_provider_key, validate_provider_model_access


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


def test_nvidia_model_validation_rejects_removed_model(monkeypatch):
    class Models:
        def list(self):
            return SimpleNamespace(
                data=[SimpleNamespace(id="z-ai/glm-5.2"), SimpleNamespace(id="meta/llama-3.3-70b-instruct")]
            )

    monkeypatch.setattr(
        "core.credential_probe.OpenAI",
        lambda **_kwargs: SimpleNamespace(models=Models()),
    )

    validate_provider_model_access("nvidia", "z-ai/glm-5.2", "nvapi-test")

    try:
        validate_provider_model_access(
            "nvidia",
            "abacusai/dracarys-llama-3.1-70b-instruct",
            "nvapi-test",
        )
    except ValueError as exc:
        assert "недоступна" in str(exc)
    else:
        raise AssertionError("removed NVIDIA model must be rejected")
