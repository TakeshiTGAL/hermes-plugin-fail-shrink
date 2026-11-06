"""pytest plugin loaded with -p. The plugin package is not imported here.

The repo root is the plugin package. Its directory name has hyphens, so pytest
would import ``__init__.py`` as a standalone module and fail. Collect the root
as a plain directory.
"""

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.hookimpl(tryfirst=True)
def pytest_collect_directory(path, parent):
    if Path(path).resolve() == _REPO_ROOT:
        return pytest.Dir.from_parent(parent, path=Path(path))
    return None
