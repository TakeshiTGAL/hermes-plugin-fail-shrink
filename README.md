When a pytest, Jest, Vitest, cargo, Go, tsc, Ruff, or ESLint command fails, the terminal output becomes a short block only when that tool's own summary line is in the text. The block names the place on that line and one rerun command. The exit code stays on the result, so Hermes still counts the command as a failure. llmslim compresses old tool output. tool-slimmer cuts tool schemas. This plugin keeps the summary place of a test or a build. When that summary line is missing, the result stays as Hermes returned it.

A process_manage result is shrunk when the output Hermes passed contains that summary line and the result has status exited with a non-zero exit code. The other fields on that result stay. Hermes 0.22.2 keeps the last 2000 characters of a finished process in `output`. A poll result has `output_preview` and no `output` field, so a poll stays whole. The pytest log in `fixtures/pytest.log` is 15058 characters. Its last 2000 characters contain no summary line, so that completion stays whole. A tail that contains the summary line is shrunk to the node id or the file written on that line. Pytest uses each `FAILED` or `ERROR` row in the last `short test summary info` section. The stats line closes the section and adds no line number. When pytest cuts the message off a wide summary row, the block uses the message on the E line in that test's failure section, and the offset points at that E line. A short summary row with no message stays without one. Jest uses a `FAIL` row and the bullet under it. Vitest uses a `FAIL` row. Cargo uses each name under the last `failures:` list before `test result: FAILED`. Go uses each column-0 `--- FAIL:` row before the `FAIL` package line. tsc, Ruff, and ESLint use a complete diagnostic row, and that row includes the file and the line. A printed path, a traceback frame, and a helper frame stay out of the block. A pytest node id that contains `..` keeps that path, and the rerun line is omitted. A citation counts only when its whole summary line is in the text. A tail that starts inside that line does not turn the remaining digits into a line number. When the short block shows 8 of a longer list, the other files are named on an `also` line and the rerun line covers every parsed name.

The full output is saved under this profile. The short block prints the path and the byte offset of the first failure. When pytest cut the message off a wide summary row, that offset is the E line in that test's failure section. `fail_full` reads that file from the offset you pass. fail_full does not open an approval card.

A passing command stays as Hermes returned it. A short result stays as Hermes returned it. A failure this plugin cannot classify stays as Hermes returned it. On a turn where you asked to see the whole log, the result stays as Hermes returned it. Phrases for that request include `show the full log` and `show me everything`. Fullwidth letters and an ideographic space still count as that request. The same request in Japanese, such as `全部見せて`, is accepted on that turn.

The rerun line is built by a rule from the command that ran and the names in the log. The runner name matches in any letter case, so `Pytest` still produces a rerun line. The plugin does not ask a model to write it. A shell pipeline, a redirect, a substitution, or a quote that does not close leaves the summary place in the block and omits the rerun line.

`json_shape` is off. Set it to the boolean `true` in this plugin's settings when you also want a large JSON tool result reduced to a type sketch, the first item, and a path to the saved text. The string `"true"` does not turn it on. Terminal results and process_manage results are never shaped that way. A result Hermes already marks as a failure keeps the fields that carry that mark, and the sketch goes in `output`. A list whose text carries that mark stays whole. A success becomes the plain sketch.

Hermes strips ANSI color and redacts secrets before this hook runs. A long terminal result may already be cut at the head and the tail. The saved file is that text. This plugin does not read a Hermes spill file. The short block is the failing part. It is not a claim that the rest of the suite passed.

## Measured on the captured logs

The files in `fixtures/` are failure logs from the real tools below. Machine paths in those logs were replaced with a short placeholder before the files were stored. The failure text and the counts are the text in those files. The short block cites the summary row in that text.

| log | tool | command | exit |
| --- | --- | --- | --- |
| pytest | pytest 9.1.1 | `python -m pytest -v tests/test_auth.py` | 1 |
| jest | jest | `npx jest --colors=false auth.test.js` | 1 |
| vitest | vitest 3.2.4 | `npx vitest run --reporter=verbose token.test.js` | 1 |
| cargo | cargo | `cargo test --offline -- --test-threads=1` | 101 |
| go | go | `go test -count=1 .` | 1 |
| tsc | tsc | `npx tsc --pretty false --noEmit -p tsconfig.json` | 2 |
| ruff | ruff | `ruff check --color never auth.py` | 1 |
| eslint | eslint | `npx eslint --no-color lint-me.js` | 1 |

pytest.log contains the text `pytest-9.1.1`. vitest.log contains the text `v3.2.4`. The jest, cargo, go, tsc, ruff, and eslint logs do not contain a version string, so those rows do not name a version.

Characters are Unicode code points in the decoded log. Tokens use the tiktoken encoding `o200k_base`. The same fixture bytes were passed to `rtk` 1.1.0 as `rtk pipe -f <filter>`. The rtk cells count that stdout. rtk's own byte-divided-by-four figure is not in this table. `rtk pipe` has filters named pytest, vitest, cargo-test, go-test, tsc, and ruff-check. It has no jest filter and no eslint filter, so those two rtk cells are unmeasured.

The fail-shrink character column counts the short block in the output field. The count includes the saved-log path and the trailing newline. The directory prefix in this count is 19 characters. The file name is 40 characters. Three runs kept the same character count. The fail-shrink token column would be the tiktoken `o200k_base` count of that same block. That count was not retaken, so the cells say unmeasured.

| log | raw characters | raw tokens | rtk characters | rtk tokens | fail-shrink characters | fail-shrink tokens |
| --- | --- | --- | --- | --- | --- | --- |
| pytest | 15058 | 4026 | 479 | 135 | 300 | unmeasured |
| jest | 4277 | 1217 | unmeasured | unmeasured | 176 | unmeasured |
| vitest | 4762 | 1510 | 72 | 25 | 326 | unmeasured |
| cargo | 4469 | 1236 | 483 | 156 | 186 | unmeasured |
| go | 1615 | 338 | 23 | 6 | 168 | unmeasured |
| tsc | 9184 | 2762 | 7476 | 2257 | 1142 | unmeasured |
| ruff | 28654 | 9164 | 2066 | 705 | 589 | unmeasured |
| eslint | 6292 | 2018 | unmeasured | unmeasured | 789 | unmeasured |

A passing pytest log in `fixtures/pytest-ok.log` is 98 characters. The hook leaves it unchanged.

## Thirty seconds

`hermes` on `PATH` is Hermes 0.22.2. The scene follows symlinks and uses the `python` beside the real `hermes` file. That interpreter has pytest. This scene does not call a model. It calls `handle_function_call` in `model_tools.py`, which is the dispatcher `hermes chat` uses after a tool call. If that python has no pytest module, the failing command's output stays whole.

The registered hooks are `pre_llm_call` and `transform_tool_result`. `pre_llm_call` records whether you asked to see the whole log on this turn and adds no text. `transform_tool_result` replaces the output field of a classified failure.

```bash
set -eu
SCENE="$(mktemp -d)"
export HERMES_HOME="$SCENE/hermes"
mkdir -p "$HERMES_HOME"
hermes plugins install --no-enable "file://$PWD"
hermes plugins enable fail-shrink
cat > "$HERMES_HOME/config.yaml" << 'EOF'
_config_version: 50
plugins:
  enabled:
    - fail-shrink
approvals:
  mode: off
EOF
HERMES_BIN="$(command -v hermes)"
while [ -L "$HERMES_BIN" ]; do
  _dest="$(readlink "$HERMES_BIN")"
  case "$_dest" in
    /*) HERMES_BIN="$_dest" ;;
    *) HERMES_BIN="$(dirname "$HERMES_BIN")/$_dest" ;;
  esac
done
PY="$(dirname "$HERMES_BIN")/python"
WORK="$SCENE/work"
mkdir -p "$WORK"
cat > "$WORK/test_token.py" << 'EOF'
def test_token_expired():
    print("\n".join(f"stale token line {i:03d}" for i in range(70)))
    assert 1 == 0
EOF
cd "$WORK"
"$PY" - "$PY" "$WORK/test_token.py" << 'PY'
import json
import sys
from hermes_cli.plugins import discover_plugins
from model_tools import handle_function_call

discover_plugins(force=True)
py, test_file = sys.argv[1], sys.argv[2]
unchanged = handle_function_call(
    "terminal",
    {"command": "echo hello-unchanged"},
    skip_pre_tool_call_hook=True,
)
print("UNCHANGED")
print(unchanged)
failed = handle_function_call(
    "terminal",
    {"command": py + " -m pytest -q " + test_file},
    skip_pre_tool_call_hook=True,
)
print("FAILED")
print(failed)
payload = None
if isinstance(failed, str):
    try:
        payload = json.loads(failed)
    except json.JSONDecodeError:
        payload = None
output = payload.get("output") if isinstance(payload, dict) else str(failed)
if not isinstance(output, str):
    output = ""
print("OUTPUT")
print(output)
if isinstance(payload, dict):
    print("EXIT", payload.get("exit_code"))
path = ""
for line in output.splitlines():
    if line.startswith("full log: "):
        parts = line.split()
        if len(parts) >= 3:
            path = parts[2]
if not path:
    print("FULL skipped")
else:
    body = json.loads(handle_function_call("fail_full", {"path": path, "offset": 0, "limit": 180}))
    print("FULL")
    print(json.dumps({"ok": body.get("ok"), "size": body.get("size")}, sort_keys=True))
    print((body.get("text") or "")[:180])
PY
```

The second scene clears `HERMES_HOME` and uses a fresh `HOME`. Hermes then uses `$HOME/.hermes`.

```bash
set -eu
SCENE="$(mktemp -d)"
export HOME="$SCENE/user"
mkdir -p "$HOME"
env -u HERMES_HOME HOME="$HOME" hermes plugins install --no-enable "file://$PWD"
env -u HERMES_HOME HOME="$HOME" hermes plugins enable fail-shrink
HERMES_DIR="$HOME/.hermes"
cat > "$HERMES_DIR/config.yaml" << 'EOF'
_config_version: 50
plugins:
  enabled:
    - fail-shrink
approvals:
  mode: off
EOF
HERMES_BIN="$(command -v hermes)"
while [ -L "$HERMES_BIN" ]; do
  _dest="$(readlink "$HERMES_BIN")"
  case "$_dest" in
    /*) HERMES_BIN="$_dest" ;;
    *) HERMES_BIN="$(dirname "$HERMES_BIN")/$_dest" ;;
  esac
done
PY="$(dirname "$HERMES_BIN")/python"
WORK="$SCENE/work"
mkdir -p "$WORK"
cat > "$WORK/test_token.py" << 'EOF'
def test_token_expired():
    print("\n".join(f"stale token line {i:03d}" for i in range(70)))
    assert 1 == 0
EOF
cd "$WORK"
env -u HERMES_HOME HOME="$HOME" "$PY" - "$PY" "$WORK/test_token.py" << 'PY'
import json
import sys
from hermes_cli.plugins import discover_plugins
from model_tools import handle_function_call

discover_plugins(force=True)
py, test_file = sys.argv[1], sys.argv[2]
failed = handle_function_call(
    "terminal",
    {"command": py + " -m pytest -q " + test_file},
    skip_pre_tool_call_hook=True,
)
print("FAILED")
print(failed)
payload = None
if isinstance(failed, str):
    try:
        payload = json.loads(failed)
    except json.JSONDecodeError:
        payload = None
output = payload.get("output") if isinstance(payload, dict) else str(failed)
if not isinstance(output, str):
    output = ""
print("OUTPUT")
print(output)
if isinstance(payload, dict):
    print("EXIT", payload.get("exit_code"))
path = ""
for line in output.splitlines():
    if line.startswith("full log: "):
        parts = line.split()
        if len(parts) >= 3:
            path = parts[2]
if not path:
    print("FULL skipped")
else:
    body = json.loads(handle_function_call("fail_full", {"path": path, "offset": 0, "limit": 80}))
    print("FULL")
    print(json.dumps({"ok": body.get("ok"), "size": body.get("size")}, sort_keys=True))
PY
```

Do not point `HERMES_HOME` at a profile you already use. The saved logs remain after you disable the plugin. `hermes plugins remove fail-shrink` deletes the installed plugin directory and leaves that same log directory. Delete `<HERMES_HOME>/plugin-data/fail-shrink` to remove the logs. In the second scene that directory is `$HOME/.hermes/plugin-data/fail-shrink`.

## Turning it off

Enabling the plugin turns `fail_full` on for every platform. `hermes tools disable fail-shrink --platform cli` hides `fail_full` on the cli platform. The same command with `--platform telegram` hides it there. The shrink hook still rewrites a classified failure after the tool is hidden. `hermes plugins disable fail-shrink` stops the hook and the tool.

## What stays on disk

Each saved log is one file. The directory holds at most 40 files, 8 MiB each, and 32 MiB together. Saving takes a POSIX directory fd. Linux and macOS provide that fd. `flock` locks the directory when the module is present, and an exclusive lock file does it when `flock` is absent. A host without a directory fd leaves the failure whole and saves nothing. A file over 20,000 lines is not saved, and that result stays whole. When a new file does not fit, the oldest file is removed. `fail_full` reads one of those files. The default limit is 8000 bytes and the maximum is 32000. An offset past the end is an error. An offset equal to the size returns empty text.

The plugin starts without reading the sample logs in `fixtures/`.
