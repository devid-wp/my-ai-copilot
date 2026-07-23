from core.doctor import collect_doctor_checks


def test_doctor_reports_provider_model_and_project(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "configured")

    checks = collect_doctor_checks(
        str(tmp_path),
        "gemini",
        "gemini-2.0-flash",
        ["gemini-2.0-flash"],
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
        "gemini-2.0-flash",
        ["meta/llama-3.1-8b-instruct"],
        ollama_online=True,
    )

    model = next(check for check in checks if check.name == "Model")
    assert model.ok is False
