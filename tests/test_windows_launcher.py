import citadex_windows


def test_windows_launcher_bootstraps_and_starts_agent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(citadex_windows, "bootstrap_local_model", lambda _confirm: "model:1.5b")
    received = []
    monkeypatch.setattr(citadex_windows, "citadex_main", lambda args: received.extend(args) or 0)
    assert citadex_windows.run() == 0
    assert received[received.index("--model") + 1] == "model:1.5b"
    assert "--agent" in received
    assert "--skip-setup" in received
