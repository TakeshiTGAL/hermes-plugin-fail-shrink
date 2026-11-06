import pytest

from support import runtime


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    root = home / "plugin-data" / "fail-shrink"
    root.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("HERMES_DATA_DIR_SUFFIX", raising=False)
    runtime.ROOT_OVERRIDE = root
    runtime.SHOW_FULL.clear()
    yield root
    runtime.SHOW_FULL.clear()
    runtime.ROOT_OVERRIDE = None
