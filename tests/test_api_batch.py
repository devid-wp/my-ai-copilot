from pathlib import Path


def test_api_batch_uses_private_runtime_and_hidden_key_launcher():
    script = Path("START_CITADEX_API.bat").read_text(encoding="utf-8")
    assert "Python.Python.3.12" in script
    assert "%LocalAppData%\\Citadex\\runtime" in script
    assert "-m citadex_api" in script
    assert "set /p" not in script.casefold()
