"""Keep tests isolated from real Citadex user configuration."""

import pytest


@pytest.fixture(autouse=True)
def isolated_citadex_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CITADEX_CONFIG_DIR", str(tmp_path / "citadex-config"))
