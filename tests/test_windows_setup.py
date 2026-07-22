from core.windows_setup import DEFAULT_LOCAL_MODEL, bootstrap_local_model, ollama_models


def test_ollama_models_returns_names(monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"models":[{"name":"qwen2.5-coder:1.5b"}]}'

    monkeypatch.setattr("core.windows_setup.urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    assert ollama_models() == {DEFAULT_LOCAL_MODEL}


def test_bootstrap_reuses_installed_model(monkeypatch):
    monkeypatch.setattr("core.windows_setup.find_ollama", lambda: "ollama.exe")
    monkeypatch.setattr("core.windows_setup.start_ollama", lambda _executable: None)
    monkeypatch.setattr("core.windows_setup.ollama_models", lambda: {DEFAULT_LOCAL_MODEL})
    configured = []
    monkeypatch.setattr("core.windows_setup.configure_local_defaults", configured.append)
    model = bootstrap_local_model(lambda _question: False)
    assert model == DEFAULT_LOCAL_MODEL
    assert configured == [DEFAULT_LOCAL_MODEL]
