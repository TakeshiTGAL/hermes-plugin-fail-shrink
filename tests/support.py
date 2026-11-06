"""Load the plugin as a package so relative imports resolve."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _package():
    name = "fail_shrink_plugin"
    if name in sys.modules:
        return sys.modules[name]
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        name,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = name
    module.__path__ = [str(root)]
    sys.modules[name] = module
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


_PKG = _package()
command = sys.modules["fail_shrink_plugin.command"]
hooks = sys.modules["fail_shrink_plugin.hooks"]
parse = sys.modules["fail_shrink_plugin.parse"]
runtime = sys.modules["fail_shrink_plugin.runtime"]
shrink = sys.modules["fail_shrink_plugin.shrink"]
store = sys.modules["fail_shrink_plugin.store"]
tools = sys.modules["fail_shrink_plugin.tools"]
ROOT = Path(__file__).resolve().parents[1]
