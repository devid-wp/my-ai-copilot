import pytest

from core.version import get_version
from main import parse_args


def test_cli_prints_installed_version(capsys):
    with pytest.raises(SystemExit) as stopped:
        parse_args(["--version"])
    assert stopped.value.code == 0
    assert capsys.readouterr().out.strip().endswith(get_version())
