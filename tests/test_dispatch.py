"""Drive the public dispatcher in a clean process so this repo does not shadow Hermes."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from support import ROOT

_CHILD = r"""
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
test_file = Path(sys.argv[2])
try:
    from hermes_cli.plugins import discover_plugins
    from model_tools import handle_function_call
except Exception as exc:
    print("IMPORT " + type(exc).__name__)
    raise

discover_plugins(force=True)
unchanged = handle_function_call(
    "terminal",
    {"command": "echo hello-unchanged"},
    skip_pre_tool_call_hook=True,
)
print("UNCHANGED " + str(unchanged).replace("\n", "\\n"))
failed = handle_function_call(
    "terminal",
    {"command": sys.executable + " -m pytest -q " + str(test_file)},
    skip_pre_tool_call_hook=True,
)
print("FAILED_START")
print(failed)
print("FAILED_END")
text = str(failed)
try:
    payload = json.loads(text)
except json.JSONDecodeError:
    payload = None
output = payload.get("output") if isinstance(payload, dict) else ""
if not isinstance(output, str) or not output.startswith("pytest failed."):
    raise SystemExit(2)
if not isinstance(payload, dict) or payload.get("exit_code") in (None, 0, False):
    raise SystemExit(4)
path = ""
for line in output.splitlines():
    if line.startswith("full log: "):
        parts = line.split()
        if len(parts) >= 3:
            path = parts[2]
if not path:
    raise SystemExit(5)
body = json.loads(handle_function_call("fail_full", {"path": path, "offset": 0, "limit": 400}))
print("BODY " + json.dumps({"ok": body.get("ok"), "has_text": bool(body.get("text")), "exit_code": payload.get("exit_code")}))
if body.get("ok") is not True:
    raise SystemExit(3)
"""


def _env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    kept = []
    for part in env.get("PYTHONPATH", "").split(os.pathsep):
        if not part:
            continue
        try:
            if Path(part).resolve() == ROOT:
                continue
        except OSError:
            continue
        kept.append(part)
    env["PYTHONPATH"] = os.pathsep.join(kept)
    env["HERMES_HOME"] = str(home)
    env.pop("HERMES_DATA_DIR_SUFFIX", None)
    return env


def test_handle_function_call_shrinks_a_real_pytest_and_reads_it_back(isolated):
    home = isolated.parent.parent
    probe = subprocess.run(
        [sys.executable, "-c", "import model_tools"],
        cwd="/tmp",
        env=_env(home),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if probe.returncode != 0:
        pytest.skip("model_tools is not importable")
    plug = home / "plugins" / "fail-shrink"
    if plug.exists():
        shutil.rmtree(plug)
    shutil.copytree(
        ROOT,
        plug,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"),
    )
    (home / "config.yaml").write_text(
        "_config_version: 50\n"
        "plugins:\n"
        "  enabled:\n"
        "    - fail-shrink\n"
        "approvals:\n"
        "  mode: off\n",
        encoding="utf-8",
    )
    work = home.parent / "work"
    work.mkdir(exist_ok=True)
    test_file = work / "test_token.py"
    test_file.write_text(
        "def test_token_expired():\n"
        "    print('\\n'.join(f'stale token line {i:03d}' for i in range(70)))\n"
        "    assert 1 == 0\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, str(home), str(test_file)],
        cwd=str(work),
        env=_env(home),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "UNCHANGED" in proc.stdout
    assert "hello-unchanged" in proc.stdout
    assert "pytest failed." in proc.stdout
    assert '"exit_code": 1' in proc.stdout or '"exit_code":1' in proc.stdout
    assert '"ok": true' in proc.stdout
