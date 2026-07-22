from pathlib import Path


def test_package_metadata_does_not_publish_creator_identity():
    metadata = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "authors =" not in metadata
