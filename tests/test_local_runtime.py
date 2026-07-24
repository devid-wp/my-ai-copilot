import pytest

from core.local_runtime import (
    LOCAL_MODEL_FILENAME,
    bundle_root,
    runtime_paths,
    start_local_server,
)


def test_bundle_root_honors_explicit_override(monkeypatch, tmp_path):
    monkeypatch.setenv("CITADEX_LOCAL_BUNDLE", str(tmp_path))

    assert bundle_root() == tmp_path.resolve()


def test_runtime_paths_are_portable(tmp_path):
    executable, model = runtime_paths(tmp_path)

    assert executable == tmp_path / "runtime" / "llama-server.exe"
    assert model == tmp_path / "models" / LOCAL_MODEL_FILENAME


def test_start_local_server_reports_missing_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr("core.local_runtime.local_server_online", lambda: False)

    with pytest.raises(FileNotFoundError, match="runtime"):
        start_local_server(tmp_path)


def test_start_local_server_reports_missing_model(monkeypatch, tmp_path):
    monkeypatch.setattr("core.local_runtime.local_server_online", lambda: False)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "llama-server.exe").write_bytes(b"runtime")

    with pytest.raises(FileNotFoundError, match="model"):
        start_local_server(tmp_path)


def test_source_bundle_root_is_repository():
    assert (bundle_root() / "main.py").is_file()
