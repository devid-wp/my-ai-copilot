from core.doctor import collect_doctor_checks


def test_doctor_reports_provider_model_and_project(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    checks = collect_doctor_checks(
        str(tmp_path),
        "openai",
        "gpt-5.6",
        ["gpt-5.6"],
        ollama_online=False,
    )
    states = {check.name: check.ok for check in checks}

    assert states["Python"]
    assert states["Project"]
    assert states["Write access"]
    assert states["API key"]
    assert states["Model"]
    assert states["Ollama"] is False


def test_doctor_rejects_cross_provider_model(monkeypatch, tmp_path):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")

    checks = collect_doctor_checks(
        str(tmp_path),
        "nvidia",
        "openai-model",
        ["meta/llama-3.1-8b-instruct"],
        ollama_online=True,
    )

    model = next(check for check in checks if check.name == "Model")
    assert model.ok is False
