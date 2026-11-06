"""Behavior pinned to captured logs and to the public hook contract."""

import hashlib
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from input_kinds import CRASH_LINE_ROWS, LIVE_ROWS, PHRASE_ROWS, ROWS
from support import ROOT, command, hooks, parse, runtime, shrink, store, tools
FIXTURES = ROOT / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
DIALECTS = ("pytest", "jest", "vitest", "cargo", "go", "tsc", "ruff", "eslint")


def _log(name: str) -> str:
    return (FIXTURES / f"{name}.log").read_text(encoding="utf-8")


def _envelope(output: str, exit_code: int, command: str) -> str:
    return json.dumps({"output": output, "exit_code": exit_code, "error": None, "command": command})


def _shrink(name: str, root: Path) -> str | None:
    row = MANIFEST[name]
    return shrink.transform(
        "terminal",
        {"command": row["command"]},
        _envelope(_log(name), row["exit"], row["command"]),
        root=root,
        json_shape=False,
    )


def _block(result: str | None) -> str:
    assert isinstance(result, str)
    payload = json.loads(result)
    output = payload["output"]
    assert isinstance(output, str)
    return output


def _fingerprint(root: Path) -> list[tuple]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            info = path.lstat()
            rows.append((str(path.relative_to(root)), "link", info.st_mode))
            continue
        if not path.is_file():
            continue
        info = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append((str(path.relative_to(root)), info.st_ino, info.st_mtime_ns, info.st_size, digest))
    return rows


def test_each_captured_log_shrinks_to_file_line_and_a_rule_rerun(isolated):
    first = {
        "pytest": "tests/test_auth.py test_token_expired",
        "jest": "auth.test.js token expired",
        "vitest": "token.test.js token expired",
        "cargo": "auth::token_expired",
        "go": "TestTokenExpired",
        "tsc": "auth.ts:1 TS2322",
        "ruff": "auth.py:1 F401",
        "eslint": "lint-me.js:1 no-unused-vars",
    }
    for name in DIALECTS:
        raw = _shrink(name, isolated)
        assert raw is not None, name
        payload = json.loads(raw)
        assert payload["exit_code"] == MANIFEST[name]["exit"]
        assert payload["error"] is None
        block = payload["output"]
        assert block.startswith(f"{name} failed.")
        assert first[name] in block
        assert "full log:" in block
        assert "offset=" in block
        assert "passed" not in block.lower()
        original = _envelope(_log(name), MANIFEST[name]["exit"], MANIFEST[name]["command"])
        assert len(raw) < len(original)
        assert len(block) < len(original)
        parsed = parse.classify(_log(name))
        assert parsed is not None
        assert parsed[0] == name
        item = parsed[1][0]
        if name in {"tsc", "ruff", "eslint"}:
            assert item.file
            assert item.line > 0
        elif name in {"cargo", "go"}:
            assert item.file == ""
            assert item.line == 0
            assert item.name
        else:
            assert item.file
            assert item.line == 0


def test_pytest_rerun_uses_the_real_runner_prefix(isolated):
    block = _block(_shrink("pytest", isolated))
    assert "rerun: python -m pytest tests/test_auth.py -k test_token_expired\n" in block
    assert "tests/test_auth.py test_token_expired" in block
    assert "tests/test_auth.py:" not in block


def test_printed_offset_starts_at_the_summary_row(isolated):
    """The printed offset is the summary row. Earlier text stays in the saved file."""
    heads = {
        "pytest": "FAILED tests/test_auth.py::test_token_expired",
        "jest": "FAIL ./auth.test.js",
        "vitest": "FAIL  token.test.js > token expired",
        "cargo": "auth::token_expired",
        "go": "--- FAIL: TestTokenExpired",
        "tsc": "auth.ts(1,14): error TS2322:",
        "ruff": "--> auth.py:1:8",
        "eslint": "1:7  error",
    }
    also = {
        "pytest": b"- fresh token line",
        "jest": b"- Expected",
        "vitest": b"- Expected",
        "cargo": b"assertion `left == right` failed",
        "go": b"token mismatch",
        "tsc": b"error TS2322",
        "ruff": b"import unused_mod_0",
        "eslint": b"no-unused-vars",
    }
    for name in DIALECTS:
        block = _block(_shrink(name, isolated))
        header = [row for row in block.splitlines() if row.startswith("full log: ")][0]
        offset = int(header.split("offset=", 1)[1])
        path = header.split()[2]
        data = Path(path).read_bytes()
        anchor = parse.classify(_log(name))[1][0].anchor
        assert data[offset:offset + len(anchor.encode())].decode() == anchor, name
        assert anchor.lstrip().startswith(heads[name]), (name, anchor[:80])
        assert also[name] in data, name


def test_rerun_round_trips_for_every_dialect(isolated):
    for name in DIALECTS:
        block = _block(_shrink(name, isolated))
        line = [row for row in block.splitlines() if row.startswith("rerun: ")]
        assert len(line) == 1, name
        rerun = line[0][len("rerun: "):]
        assert command.shell_join(command.simple_argv(rerun)) == rerun


def test_success_log_is_unchanged(isolated):
    output = _log("pytest-ok")
    result = _envelope(output, 0, "python -m pytest -q tests/test_ok_only.py")
    assert shrink.transform("terminal", {"command": "python -m pytest -q tests/test_ok_only.py"}, result, root=isolated, json_shape=False) is None


def test_exit_zero_with_failure_text_is_unchanged(isolated):
    output = _log("pytest")
    result = _envelope(output, 0, "python -m pytest -v tests/test_auth.py")
    assert shrink.transform("terminal", {"command": "python -m pytest -v tests/test_auth.py"}, result, root=isolated, json_shape=False) is None


def test_unclassified_failure_is_unchanged(isolated):
    output = "boom\n" * 80
    result = _envelope(output, 1, "python3 -c 'raise SystemExit(1)'")
    assert shrink.transform("terminal", {"command": "python3 -c 'raise SystemExit(1)'"}, result, root=isolated, json_shape=False) is None


def test_short_failure_is_unchanged(isolated):
    output = "FAILED tests/test_auth.py::test_token_expired - AssertionError: no\n"
    output += "short test summary info\n"
    result = _envelope(output, 1, "python -m pytest tests/test_auth.py")
    assert shrink.transform("terminal", {"command": "python -m pytest tests/test_auth.py"}, result, root=isolated, json_shape=False) is None


def test_two_dialects_are_unchanged(isolated):
    output = _log("pytest") + "\n" + _log("cargo")
    result = _envelope(output, 1, "make test")
    assert shrink.transform("terminal", {"command": "make test"}, result, root=isolated, json_shape=False) is None


def test_wrong_runner_is_unchanged(isolated):
    result = _envelope(_log("pytest"), 1, "cargo test")
    assert shrink.transform("terminal", {"command": "cargo test"}, result, root=isolated, json_shape=False) is None


def test_pasted_url_keeps_file_line_without_a_rerun(isolated):
    command_line = "https://example.com/pytest -q tests/test_auth.py"
    block = shrink.transform(
        "terminal",
        {"command": command_line},
        _envelope(_log("pytest"), 1, command_line),
        root=isolated,
        json_shape=False,
    )
    block = _block(block)
    assert "tests/test_auth.py test_token_expired" in block
    assert "tests/test_auth.py:" not in block
    assert "rerun:" not in block
    assert "https://" not in block
    assert command.runner_kind(["https://example.com/python", "-m", "pytest"]) is None
    assert command.runner_kind(["npx", "https://example.com/jest"]) is None
    assert command.runner_kind(["https://example.com/cargo", "test"]) is None
    assert command.runner_kind(["/usr/bin/pytest", "-q", "tests/test_auth.py"]) == "pytest"
    assert command.runner_kind(["python3", "-m", "pytest", "tests/test_auth.py"]) == "pytest"


def test_unknown_runner_keeps_file_line_without_a_rerun(isolated):
    block = shrink.transform(
        "terminal",
        {"command": "make test"},
        _envelope(_log("pytest"), 1, "make test"),
        root=isolated,
        json_shape=False,
    )
    block = _block(block)
    assert "tests/test_auth.py test_token_expired" in block
    assert "tests/test_auth.py:" not in block
    assert "rerun:" not in block


def test_shell_composition_omits_the_rerun(isolated):
    command_line = "python -m pytest tests/test_auth.py && python -m pytest tests/other.py"
    block = shrink.transform(
        "terminal",
        {"command": command_line},
        _envelope(_log("pytest"), 1, command_line),
        root=isolated,
        json_shape=False,
    )
    block = _block(block)
    assert "rerun:" not in block
    assert "tests/test_auth.py test_token_expired" in block
    assert "tests/test_auth.py:" not in block


def test_broken_quotes_omit_the_rerun(isolated):
    command_line = "python -m pytest tests/test_auth.py 'unterminated"
    block = shrink.transform(
        "terminal",
        {"command": command_line},
        _envelope(_log("pytest"), 1, command_line),
        root=isolated,
        json_shape=False,
    )
    block = _block(block)
    assert "rerun:" not in block


def test_show_full_turn_is_unchanged(isolated):
    hooks.on_pre_llm_call(user_message="please show me everything", session_id="s", turn_id="t")
    result = _envelope(_log("pytest"), 1, MANIFEST["pytest"]["command"])
    assert hooks.on_transform(
        None, tool_name="terminal", args={"command": MANIFEST["pytest"]["command"]},
        result=result, session_id="s", turn_id="t",
    ) is None
    assert hooks.on_pre_llm_call(user_message="please show me everything", session_id="s", turn_id="t") is None


def test_show_full_phrases_cover_every_row(isolated):
    result = _envelope(_log("go"), 1, MANIFEST["go"]["command"])
    args = {"command": MANIFEST["go"]["command"]}
    for index, (phrase, keep) in enumerate(PHRASE_ROWS):
        turn = f"phrase-{index}"
        hooks.on_pre_llm_call(user_message=phrase, session_id="s", turn_id=turn)
        got = hooks.on_transform(
            None, tool_name="terminal", args=args, result=result, session_id="s", turn_id=turn,
        )
        if keep:
            assert got is None, phrase
        else:
            assert _block(got).startswith("go failed."), phrase
    assert len(PHRASE_ROWS) == len({row[0] for row in PHRASE_ROWS})


def test_japanese_show_full_phrase_and_html_comment(isolated):
    phrase = "\u5168\u90e8\u898b\u305b\u3066"
    hooks.on_pre_llm_call(user_message=[{"type": "text", "text": phrase}], session_id="s", turn_id="1")
    result = _envelope(_log("go"), 1, MANIFEST["go"]["command"])
    assert hooks.on_transform(None, tool_name="terminal", args={"command": MANIFEST["go"]["command"]}, result=result, session_id="s", turn_id="1") is None
    hooks.on_pre_llm_call(user_message=f"<!-- {phrase} --> run the tests", session_id="s", turn_id="2")
    block = hooks.on_transform(None, tool_name="terminal", args={"command": MANIFEST["go"]["command"]}, result=result, session_id="s", turn_id="2")
    assert _block(block).startswith("go failed.")
    hooks.on_pre_llm_call(user_message="", session_id="s", turn_id="3")
    assert hooks.on_transform(None, tool_name="terminal", args={"command": MANIFEST["go"]["command"]}, result=result, session_id="s", turn_id="3") is not None


def test_other_turn_still_shrinks(isolated):
    hooks.on_pre_llm_call(user_message="show the full log", session_id="s", turn_id="1")
    result = _envelope(_log("tsc"), 2, MANIFEST["tsc"]["command"])
    block = hooks.on_transform(None, tool_name="terminal", args={"command": MANIFEST["tsc"]["command"]}, result=result, session_id="s", turn_id="2")
    assert _block(block).startswith("tsc failed.")


def test_unrelated_tool_is_unchanged_when_json_shape_is_off(isolated):
    payload = json.dumps([{"id": index, "name": "n" * 40} for index in range(80)])
    assert shrink.transform("web_search", {}, payload, root=isolated, json_shape=False) is None
    assert hooks.on_transform(None, tool_name="web_search", args={}, result=payload, session_id="s", turn_id="t") is None


def test_json_shape_is_on_only_for_a_real_true(isolated):
    payload = json.dumps([{"id": index, "name": "n" * 80} for index in range(40)])
    assert len(payload) > 4000

    class Ctx:
        def __init__(self, value):
            self.value = value

        def get_config(self, key, default=None):
            assert key == "json_shape"
            return self.value

    assert hooks.on_transform(Ctx(False), tool_name="read_file", args={}, result=payload) is None
    assert hooks.on_transform(Ctx("true"), tool_name="read_file", args={}, result=payload) is None
    block = hooks.on_transform(Ctx(True), tool_name="read_file", args={}, result=payload)
    assert block is not None
    assert block.startswith("json array[40] of object{")
    assert "first:" in block
    assert "full log:" in block
    terminal = _envelope(_log("pytest-ok"), 0, "python -m pytest -q x")
    assert hooks.on_transform(Ctx(True), tool_name="terminal", args={"command": "python -m pytest -q x"}, result=terminal) is None


def test_process_manage_shrinks_only_a_full_exited_failure(isolated):
    output = _log("pytest")
    command_line = MANIFEST["pytest"]["command"]
    exited = {
        "status": "exited",
        "command": command_line,
        "output": output,
        "exit_code": 1,
    }
    raw = shrink.transform("process_manage", {"action": "wait"}, exited, root=isolated, json_shape=False)
    body = json.loads(raw)
    assert body["status"] == "exited"
    assert body["exit_code"] == 1
    assert body["command"] == command_line
    assert "rerun:" in body["output"]
    poll = {"status": "running", "command": command_line, "output_preview": output, "exit_code": None}
    assert shrink.transform("process_manage", {"action": "poll"}, poll, root=isolated, json_shape=False) is None
    timed = {"status": "timeout", "command": command_line, "output": output, "exit_code": None}
    assert shrink.transform("process_manage", {"action": "wait"}, timed, root=isolated, json_shape=False) is None


def test_terminal_result_keeps_exit_code_and_neighbor_fields(isolated):
    command_line = MANIFEST["pytest"]["command"]
    payload = json.loads(_envelope(_log("pytest"), 1, command_line))
    payload["hint"] = "read the assert"
    payload["cwd"] = "/work"
    raw = shrink.transform("terminal", {"command": command_line}, payload, root=isolated, json_shape=False)
    body = json.loads(raw)
    assert body["exit_code"] == 1
    assert body["error"] is None
    assert body["hint"] == "read the assert"
    assert body["cwd"] == "/work"
    assert body["command"] == command_line
    assert body["output"].startswith("pytest failed. exit 1.\n")
    plain = body["output"]
    try:
        from agent.display import _detect_tool_failure
        from agent.tool_guardrails import classify_tool_failure
    except ImportError:
        return
    assert _detect_tool_failure("terminal", raw)[0] is True
    assert classify_tool_failure("terminal", raw)[0] is True
    assert _detect_tool_failure("terminal", plain)[0] is False
    assert classify_tool_failure("terminal", plain)[0] is False


def test_process_manage_keeps_a_null_error_key_and_a_long_preview(isolated):
    output = _log("go")
    command_line = MANIFEST["go"]["command"]
    exited = {
        "status": "exited",
        "command": command_line,
        "output": output,
        "output_preview": output,
        "exit_code": 1,
        "error": None,
        "note": "kept",
    }
    raw = shrink.transform("process_manage", {"action": "wait"}, exited, root=isolated, json_shape=False)
    body = json.loads(raw)
    assert body["error"] is None
    assert body["exit_code"] == 1
    assert body["note"] == "kept"
    assert body["output"].startswith("go failed.")
    assert body["output_preview"] == body["output"]
    assert len(body["output_preview"]) < len(output)
    short = dict(exited)
    short["output_preview"] = "tail"
    raw_short = shrink.transform("process_manage", {"action": "wait"}, short, root=isolated, json_shape=False)
    assert json.loads(raw_short)["output_preview"] == "tail"


def test_json_shape_keeps_failure_fields(isolated):
    rows = [{"id": index, "name": "n" * 80} for index in range(40)]
    payload = json.dumps({"success": False, "error": "nope", "rows": rows}, ensure_ascii=False)
    assert len(payload) > 4000
    block = shrink.transform("read_file", {}, payload, root=isolated, json_shape=True)
    body = json.loads(block)
    assert body["success"] is False
    assert body["error"] == "nope"
    assert body["output"].startswith("json object{")
    assert "full log:" in body["output"]
    marked = json.dumps({"error": None, "rows": rows}, ensure_ascii=False)
    kept = shrink.transform("read_file", {}, marked, root=isolated, json_shape=True)
    assert json.loads(kept)["error"] is None
    listed = json.dumps([{"error": "x" * 80, "name": "n" * 40} for _ in range(30)], ensure_ascii=False)
    assert len(listed) > 4000
    before = set(isolated.glob("*.log"))
    assert shrink.transform("read_file", {}, listed, root=isolated, json_shape=True) is None
    assert set(isolated.glob("*.log")) == before


def test_line_numbers_come_from_each_failure_section():
    pytest_log = """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________

    def test_one():
        helper()
>       assert ("stale one") == ("fresh one")
E       AssertionError: assert 'stale one' == 'fresh one'

test_auth.py:8: in helper
test_auth.py:2: AssertionError
----------------------------- Captured stdout call -----------------------------
see test_auth.py:2: again
__________________________________ test_two ___________________________________

    def test_two():
>       assert ("stale two") == ("fresh two")
E       AssertionError: assert 'stale two' == 'fresh two'

test_auth.py:5: AssertionError
=========================== short test summary info ============================
FAILED test_auth.py::test_one - AssertionError: assert 'stale one' == 'fresh one'
FAILED test_auth.py::test_two - AssertionError: assert 'stale two' == 'fresh two'
"""
    parsed = parse.classify(pytest_log)
    assert parsed is not None and parsed[0] == "pytest"
    assert [(item.name, item.line, item.point) for item in parsed[1]] == [
        ("test_one", 0, "AssertionError: assert 'stale one' == 'fresh one'"),
        ("test_two", 0, "AssertionError: assert 'stale two' == 'fresh two'"),
    ]

    vitest_log = """
 FAIL  token.test.js > one
AssertionError: first assert
 ❯ token.test.js:10:4

 FAIL  token.test.js > two
AssertionError: second assert
 ❯ token.test.js:24:4

 Test Files  1 failed
"""
    parsed = parse.classify(vitest_log)
    assert parsed is not None and parsed[0] == "vitest"
    assert [(item.name, item.line, item.point) for item in parsed[1]] == [
        ("one", 0, "AssertionError: first assert"),
        ("two", 0, "AssertionError: second assert"),
    ]

    jest_log = """
FAIL ./auth.test.js
  ● one
      > 10 | expect(a).toBe(b);
      at helper (auth.test.js:2:1)
      at Object.toBe (auth.test.js:10:1)
  ● two
      > 24 | expect(c).toBe(d);
      at helper (auth.test.js:2:1)
      at Object.toBe (auth.test.js:24:1)
Test Suites: 1 failed, 1 total
"""
    parsed = parse.classify(jest_log)
    assert parsed is not None and parsed[0] == "jest"
    assert [(item.name, item.line, item.file) for item in parsed[1]] == [
        ("one", 0, "auth.test.js"),
        ("two", 0, "auth.test.js"),
    ]

    cargo_panic = """
thread 'one' panicked at src/lib.rs:10:1:
first boom
thread 'two' panicked at src/lib.rs:40:1:
second boom
test result: FAILED
"""
    assert parse.classify(cargo_panic) is None
    cargo_log = """
thread 'one' panicked at src/lib.rs:10:1:
first boom
thread 'two' panicked at src/lib.rs:40:1:
second boom

failures:

    one
    two

test result: FAILED
"""
    parsed = parse.classify(cargo_log)
    assert parsed is not None and parsed[0] == "cargo"
    assert [(item.file, item.name, item.line) for item in parsed[1]] == [
        ("", "one", 0),
        ("", "two", 0),
    ]

    go_bare = """
--- FAIL: TestOne (0.00s)
    a_test.go:3: one mismatch
FAIL
"""
    assert parse.classify(go_bare) is None
    go_log = """
--- FAIL: TestOne (0.00s)
    a_test.go:3: one mismatch
--- FAIL: TestTwo (0.00s)
    a_test.go:9: two mismatch
FAIL\texample.com/mod\t0.01s
"""
    parsed = parse.classify(go_log)
    assert parsed is not None and parsed[0] == "go"
    assert [(item.file, item.name, item.line) for item in parsed[1]] == [
        ("", "TestOne", 0),
        ("", "TestTwo", 0),
    ]

    eslint_log = """
a.js
  1:1  error  first message here                 no-unused-vars
b.js
  4:1  error  second message here                no-unused-vars
2 problems
"""
    parsed = parse.classify(eslint_log)
    assert [(item.file, item.line) for item in parsed[1]] == [("a.js", 1), ("b.js", 4)]


def _long(text: str) -> str:
    return ("context line\n" * 80) + text


def test_pytest_dotdot_node_keeps_the_traceback_line_and_assert(isolated):
    log = _long(
        """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________

    def test_token_expired():
>       assert 1 == 0
E       assert 1 == 0

/var/work/test_token.py:3: AssertionError
_____________________________ test_other_file _________________________________
    def test_other_file():
>       assert 2 == 0
E       assert 2 == 0

/var/work/test_other.py:8: AssertionError
=========================== short test summary info ============================
FAILED ../../../../var/work/test_token.py::test_token_expired - assert 1 == 0
FAILED ../../../../var/work/test_other.py::test_other_file
"""
    )
    parsed = parse.classify(log)
    assert parsed is not None
    assert [(item.file, item.line, item.point) for item in parsed[1]] == [
        ("../../../../var/work/test_token.py", 0, "assert 1 == 0"),
        ("../../../../var/work/test_other.py", 0, ""),
    ]
    assert parsed[1][0].block_rerun is True
    assert parsed[1][1].block_rerun is True
    assert parsed[1][0].anchor.startswith("FAILED ../../../../var/work/test_token.py::test_token_expired")
    result = shrink.transform(
        "terminal",
        {"command": "python -m pytest -q /var/work/test_token.py /var/work/test_other.py"},
        _envelope(log, 1, "python -m pytest -q /var/work/test_token.py /var/work/test_other.py"),
        root=isolated,
        json_shape=False,
    )
    block = _block(result)
    assert "../../../../var/work/test_token.py test_token_expired" in block
    assert "../../../../var/work/test_other.py test_other_file" in block
    assert "  assert 1 == 0" in block
    assert "rerun:" not in block
    header = [row for row in block.splitlines() if row.startswith("full log: ")][0]
    offset = int(header.split("offset=", 1)[1])
    path = header.split()[2]
    saved = Path(path).read_bytes()
    assert saved[offset:].decode().startswith("FAILED ../../../../var/work/test_token.py::test_token_expired")


def test_pytest_basename_collision_does_not_take_the_other_file():
    log = """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________

>       assert 1 == 0
E       assert 1 == 0

/var/other/test_token.py:9: AssertionError
/var/work/test_token.py:3: AssertionError
=========================== short test summary info ============================
FAILED ../test_token.py::test_one - assert 1 == 0
"""
    parsed = parse.classify(log)
    assert parsed is not None
    assert [(item.line, item.point) for item in parsed[1]] == [(0, "assert 1 == 0")]
    single = """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________

E       RuntimeError: boom

/var/work/test_token.py:4: RuntimeError
=========================== short test summary info ============================
FAILED ../test_token.py::test_one
"""
    parsed = parse.classify(single)
    assert parsed is not None
    assert [(item.file, item.line, item.point) for item in parsed[1]] == [
        ("../test_token.py", 0, ""),
    ]
    assert parsed[1][0].block_rerun is True
    assert parsed[1][0].anchor.startswith("FAILED ../test_token.py::test_one")


def test_parent_walk_location_from_another_directory(tmp_path):
    """cwd /tmp and a test file under the temp directory.

    Pytest 9 writes a ``..`` location when that relative path is shorter
    than the absolute path. The short block keeps that node id and omits
    the rerun. The line number stays off the block.
    """
    import tempfile

    work = Path(tempfile.mkdtemp(prefix="fs12-dot-"))
    target = work / "test_token.py"
    target.write_text(
        "def test_token_expired():\n"
        + "".join(f"    print({n})\n" for n in range(40))
        + "    assert 1 == 0\n",
        encoding="utf-8",
    )
    env = _pytest_env()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--color=no", "-p", "no:cacheprovider", "-q", str(target)],
        cwd="/tmp",
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
        env=env,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    text = proc.stdout
    parsed = parse.classify(text, command=f"python -m pytest -q {target}")
    assert parsed is not None and parsed[0] == "pytest"
    item = parsed[1][0]
    assert item.line == 0, (item.file, item.line, text[-500:])
    assert item.name == "test_token_expired"
    assert item.file.endswith("test_token.py")
    assert item.point == "assert 1 == 0"
    root = tmp_path / "logs"
    root.mkdir()
    raw = shrink.transform(
        "terminal",
        {"command": f"python -m pytest -q {target}"},
        {"output": text, "exit_code": 1, "error": None},
        root=root,
        json_shape=False,
    )
    assert raw is not None
    output = json.loads(raw)["output"]
    assert "test_token.py test_token_expired" in output
    assert "test_token.py:" not in output
    assert "outside this tail" not in output
    if ".." in item.file:
        assert item.block_rerun is True
        assert "rerun:" not in output


def _saved_from(block: str) -> tuple[int, str]:
    header = [row for row in block.splitlines() if row.startswith("full log: ")][0]
    offset = int(header.split("offset=", 1)[1])
    path = header.split()[2]
    return offset, Path(path).read_text(encoding="utf-8")


def test_width_cut_rows_come_from_pytest(tmp_path):
    """Pytest 9.1.1 with CI unset. Every width row is a real run."""
    def invoke(work: Path, body: str, args: list[str], command: str, cwd: Path | None = None):
        work.mkdir(parents=True, exist_ok=True)
        (work / "test_token.py").write_text(body, encoding="utf-8")
        code, text = _run_pytest(cwd or work, args)
        assert code == 1, text
        parsed = parse.classify(text, command=command)
        assert parsed is not None and parsed[0] == "pytest", text[-400:]
        root = tmp_path / "logs" / work.name
        root.mkdir(parents=True)
        raw = shrink.transform(
            "terminal",
            {"command": command},
            {"output": text, "exit_code": code, "error": None},
            root=root,
            json_shape=False,
        )
        assert raw is not None
        block = json.loads(raw)["output"]
        return text, parsed[1], block

    # The summary row is wider than 80 columns, so pytest drops the message.
    wide = tmp_path / "wide"
    text, items, block = invoke(
        wide,
        "def test_token_expired():\n"
        "    print('stale\\n' * 70)\n"
        "    assert 1 == 0\n",
        ["-q", str(tmp_path / "wide" / "test_token.py")],
        f"python -m pytest -q {tmp_path / 'wide' / 'test_token.py'}",
        cwd=Path("/tmp"),
    )
    summary = [line for line in text.splitlines() if line.startswith("FAILED ")][-1]
    assert " - " not in summary
    assert parse._cols(summary) >= 75
    assert items[0].line == 0
    assert items[0].name == "test_token_expired"
    assert items[0].point == "assert 1 == 0"
    assert items[0].file.endswith("test_token.py")
    assert ".." in items[0].file
    assert items[0].anchor.startswith("E")
    offset, saved = _saved_from(block)
    assert "assert 1 == 0" in saved[offset:]
    assert offset < saved.rfind("short test summary")
    assert "  assert 1 == 0" in block
    assert "rerun:" not in block

    # A short node id keeps the summary message and the summary offset.
    short = tmp_path / "short"
    text, items, block = invoke(
        short,
        "def test_token_expired():\n    print('pad\\n' * 50)\n    assert 1 == 0\n",
        ["-q", "test_token.py"],
        "python -m pytest -q test_token.py",
    )
    assert items[0].point == "assert 1 == 0"
    assert items[0].line == 0
    assert items[0].anchor.startswith("FAILED test_token.py::test_token_expired - ")
    offset, saved = _saved_from(block)
    assert saved[offset:].startswith(items[0].anchor)

    # Pytest trims a long message with "..." and the E line is the fuller text.
    longm = tmp_path / "longm"
    text, items, block = invoke(
        longm,
        "def test_token_expired():\n    print('pad\\n' * 50)\n    assert " + repr("abcdefghij" * 12) + " == 'no'\n",
        ["-q", "test_token.py"],
        "python -m pytest -q test_token.py",
    )
    summary = [line for line in text.splitlines() if line.startswith("FAILED ")][-1]
    message = summary.split(" - ", 1)[1]
    assert message.endswith("...")
    assert len(items[0].point) > len(message)
    assert items[0].point.startswith(message[:-3])
    assert items[0].anchor.startswith("E")
    offset, saved = _saved_from(block)
    assert items[0].point.split(" == ", 1)[0] in saved[offset:]

    # A printed E line in captured stdout is not the message.
    fake = tmp_path / "fake"
    _text, items, block = invoke(
        fake,
        "def test_token_expired():\n"
        "    print('E       assert 9 == 8')\n"
        "    print('stale\\n' * 40)\n"
        "    assert 1 == 0\n",
        ["-q", str(tmp_path / "fake" / "test_token.py")],
        f"python -m pytest -q {tmp_path / 'fake' / 'test_token.py'}",
        cwd=Path("/tmp"),
    )
    assert items[0].point == "assert 1 == 0"
    assert "assert 9 == 8" not in block

    # Two wide rows keep two messages, in order.
    two = tmp_path / "two"
    _text, items, block = invoke(
        two,
        "def test_one():\n    print('x\\n' * 30)\n    assert 1 == 0\n\n"
        "def test_two():\n    assert 'left' == 'right'\n",
        ["-q", str(tmp_path / "two" / "test_token.py")],
        f"python -m pytest -q {tmp_path / 'two' / 'test_token.py'}",
        cwd=Path("/tmp"),
    )
    assert [(item.name, item.line, item.point) for item in items] == [
        ("test_one", 0, "assert 1 == 0"),
        ("test_two", 0, "AssertionError: assert 'left' == 'right'"),
    ]

    # --tb=line has no heading. The E line is still before the captured fake.
    line = tmp_path / "tbline"
    _text, items, block = invoke(
        line,
        "def test_token_expired():\n"
        "    print('E       assert 9 == 8\\n' * 5)\n"
        "    print('pad\\n' * 45)\n"
        "    assert 1 == 0\n",
        ["-q", "--tb=line", str(tmp_path / "tbline" / "test_token.py")],
        f"python -m pytest -q --tb=line {tmp_path / 'tbline' / 'test_token.py'}",
        cwd=Path("/tmp"),
    )
    assert items[0].point == "assert 1 == 0"
    assert items[0].line == 0
    assert items[0].file.endswith("test_token.py")
    assert ":" not in items[0].file.split("/")[-1]
    assert "assert 9 == 8" not in items[0].point

    # A class heading is TestBox.test_token_expired, not the function alone.
    klass = tmp_path / "klass"
    klass.mkdir()
    (klass / "test_token.py").write_text(
        "class TestBox:\n"
        "    def test_token_expired(self):\n"
        "        assert 1 == 0\n",
        encoding="utf-8",
    )
    code, text = _run_pytest(Path("/tmp"), ["-q", str(klass / "test_token.py")])
    assert code == 1, text
    parsed = parse.classify(text, command=f"python -m pytest -q {klass / 'test_token.py'}")
    assert parsed is not None
    summary = [line for line in text.splitlines() if line.startswith("FAILED ")][-1]
    assert " - " not in summary
    assert parsed[1][0].name == "test_token_expired"
    assert parsed[1][0].line == 0
    assert parsed[1][0].point == "assert 1 == 0"


def test_absolute_summary_rows_keep_the_place_on_that_row():
    jest = """
FAIL /var/work/auth.test.js
  ● token expired
      > 47 | expect(a).toBe(b);
      at Object.toBe (/var/work/auth.test.js:47:1)
Test Suites: 1 failed, 1 total
"""
    vitest = """
 FAIL  /var/work/token.test.js > token expired
AssertionError: assert stale
 ❯ /var/work/token.test.js:47:4
 Test Files  1 failed
"""
    cargo_panic = """
thread 'auth::token_expired' panicked at /var/work/src/lib.rs:208:5:
assertion failed
test result: FAILED
"""
    go_bare = """
--- FAIL: TestTokenExpired (0.00s)
    /var/work/auth_test.go:173: mismatch
FAIL
"""
    assert parse.classify(cargo_panic) is None
    assert parse.classify(go_bare) is None
    cargo = cargo_panic.replace(
        "test result: FAILED",
        "failures:\n\n    auth::token_expired\n\ntest result: FAILED",
    )
    parsed = parse.classify(cargo)
    assert parsed is not None and parsed[0] == "cargo"
    assert parsed[1][0].file == ""
    assert parsed[1][0].line == 0
    assert parsed[1][0].name == "auth::token_expired"
    go = """
--- FAIL: TestTokenExpired (0.00s)
    /var/work/auth_test.go:173: mismatch
FAIL\texample.com/tokenbox\t0.01s
"""
    parsed = parse.classify(go)
    assert parsed is not None and parsed[0] == "go"
    assert parsed[1][0].file == ""
    assert parsed[1][0].line == 0
    assert parsed[1][0].name == "TestTokenExpired"
    for name, text in (("jest", jest), ("vitest", vitest)):
        parsed = parse.classify(text)
        assert parsed is not None and parsed[0] == name, name
        assert parsed[1][0].line == 0, name
        assert parsed[1][0].file.startswith("/var/work/"), name
    diagnostics = {
        "tsc": "/var/work/auth.ts(1,1): error TS2322: bad\n",
        "ruff": "F401 [*] unused\n --> /var/work/auth.py:1:8\nFound 1 error.\n",
        "eslint": (
            "/var/work/lint-a.js\n"
            "  1:1  error  first message here                 no-unused-vars\n"
            "/var/work/lint-b.js\n"
            "  4:1  error  second message here                no-unused-vars\n"
            "2 problems\n"
        ),
    }
    for name, text in diagnostics.items():
        parsed = parse.classify(text)
        assert parsed is not None and parsed[0] == name, name
        assert parsed[1][0].line > 0, name
        assert parsed[1][0].file.startswith("/var/work/"), name


def test_cargo_rerun_keeps_offline(isolated):
    block = _block(_shrink("cargo", isolated))
    assert "rerun: cargo test --offline auth::token_expired -- --exact\n" in block


def test_missing_exit_code_is_unchanged(isolated):
    payload = {"output": _log("go"), "error": None}
    assert shrink.transform("terminal", {"command": MANIFEST["go"]["command"]}, payload, root=isolated, json_shape=False) is None


def test_tool_error_string_is_unchanged(isolated):
    payload = {"output": _log("go"), "exit_code": 1, "error": "Command timed out after 1 seconds"}
    assert shrink.transform("terminal", {"command": MANIFEST["go"]["command"]}, payload, root=isolated, json_shape=False) is None


def test_fail_full_reads_the_saved_slice_and_does_not_write(isolated):
    block = _block(_shrink("eslint", isolated))
    path = [line for line in block.splitlines() if line.startswith("full log: ")][0].split()[2]
    before = _fingerprint(isolated)
    body = json.loads(tools.handle_fail_full({"path": path, "offset": 0, "limit": 120}))
    after = _fingerprint(isolated)
    assert before == after
    assert body["ok"] is True
    assert body["text"]
    assert body["size"] == (isolated / Path(path).name).stat().st_size
    empty = json.loads(tools.handle_fail_full({"path": path, "offset": body["size"], "limit": 10}))
    assert empty["ok"] is True
    assert empty["text"] == ""


def test_fail_full_errors_are_typed(isolated):
    cases = [
        ({}, "bad_argument"),
        ({"path": 1}, "bad_argument"),
        ({"path": "nope.log", "extra": 1}, "bad_argument"),
        ({"path": "nope.log", "offset": "0"}, "bad_offset"),
        ({"path": "nope.log", "offset": -1}, "bad_offset"),
        ({"path": "nope.log", "limit": 0}, "bad_limit"),
        ({"path": "nope.log", "limit": 32001}, "bad_limit"),
        ({"path": "../secret.log"}, "path_refused"),
        ({"path": "0000000000000001-abcdefabcdefabcd.log"}, "not_found"),
    ]
    for args, kind in cases:
        body = json.loads(tools.handle_fail_full(args))
        assert body["ok"] is False
        assert body["error_type"] == kind
        assert body["next_step"]
    assert json.loads(tools.handle_fail_full(None))["error_type"] == "bad_argument"


def test_fail_full_refuses_a_symlink_and_a_path_outside(isolated):
    target = isolated / "note.txt"
    target.write_text("secret", encoding="utf-8")
    link_name = "1234567890123456-abcdefabcdefabcd.log"
    link = isolated / link_name
    link.symlink_to(target)
    body = json.loads(tools.handle_fail_full({"path": str(link)}))
    assert body["error_type"] == "path_refused"
    outside = isolated.parent / link_name
    outside.write_text("x", encoding="utf-8")
    body = json.loads(tools.handle_fail_full({"path": str(outside)}))
    assert body["error_type"] == "path_refused"


def test_store_drops_the_oldest_file_at_the_cap(isolated):
    first = None
    for index in range(store.MAX_FILES):
        saved = store.save_text(isolated, f"log {index}\n")
        assert saved is not None
        if first is None:
            first = saved
    assert first is not None and first.exists()
    extra = store.save_text(isolated, "one more\n")
    assert extra is not None
    assert not first.exists()
    logs = [path for path in isolated.glob("*.log")]
    assert len(logs) == store.MAX_FILES


def test_store_refuses_a_file_past_the_byte_cap_and_the_line_cap(isolated):
    assert store.save_text(isolated, "x" * (store.MAX_FILE_BYTES + 1)) is None
    assert store.save_text(isolated, "\n" * (store.MAX_LINES + 1)) is None
    assert list(isolated.glob("*.log")) == []


def test_missing_fcntl_still_saves_with_an_exclusive_lock(isolated, monkeypatch):
    monkeypatch.setattr(store, "fcntl", None)
    saved = _shrink("go", isolated)
    assert saved is not None
    assert list(isolated.glob("*.log"))
    assert list(isolated.glob(store._EXCL_LOCK)) == []


def test_missing_directory_fd_leaves_the_result_whole(isolated, monkeypatch):
    monkeypatch.setattr(store, "_DIR_FLAGS", None)
    assert _shrink("go", isolated) is None
    assert list(isolated.glob("*.log")) == []


def test_store_accepts_a_real_directory_under_a_symlink_parent(isolated, tmp_path):
    link = tmp_path / "link-parent"
    link.symlink_to(isolated.parent, target_is_directory=True)
    via = link / isolated.name
    saved = store.save_text(via, "kept\n")
    assert saved is not None
    assert saved.parent == isolated.resolve()
    body = json.loads(tools.handle_fail_full({"path": str(saved), "offset": 0, "limit": 20}))
    assert body["ok"] is True
    assert body["text"] == "kept\n"


def test_store_refuses_a_symlink_root(isolated, tmp_path):
    link = tmp_path / "linked"
    link.symlink_to(isolated, target_is_directory=True)
    assert store.save_text(link, "hello\n" * 5) is None


def test_write_refuses_dotdot_and_a_hardlink(isolated):
    from safe_write import WriteRefused, write_bytes
    with pytest.raises(WriteRefused):
        write_bytes(isolated, "../escape.log", b"no", create=True, exclusive=True)
    name = "1234567890123456-abcdefabcdefabcd.log"
    write_bytes(isolated, name, b"body", create=True, exclusive=True)
    other = isolated / "other-name.log"
    os.link(isolated / name, other)
    with pytest.raises(WriteRefused):
        write_bytes(isolated, name, b"next", create=True, exclusive=True)


def test_proxy_env_and_metadata_addresses_do_not_change_the_block(isolated, monkeypatch):
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy",
        "NO_PROXY", "no_proxy", "all_proxy", "ftp_proxy",
    ):
        monkeypatch.setenv(key, "http://169.254.169.254:80")
    monkeypatch.setenv("ALL_PROXY", "http://192.0.2.1:9")
    first = _shrink("go", isolated)
    second = _shrink("go", isolated)
    assert _block(first).split("\n", 1)[0] == _block(second).split("\n", 1)[0]
    assert "169.254.169.254" not in first
    assert "0.0.0.0" not in first


def test_source_starts_no_child_and_reads_no_dotenv():
    banned = ("subprocess", "dotenv", "urllib", "socket", "requests", "httpx")
    # A runner may drop a socket blocker beside the tree. Scan the plugin files only.
    names = (
        "__init__.py", "command.py", "errors.py", "hooks.py", "parse.py",
        "runtime.py", "schemas.py", "shrink.py", "store.py", "tools.py", "safe_write.py",
    )
    for name in names:
        text = (ROOT / name).read_text(encoding="utf-8")
        for word in banned:
            assert word not in text, name


def test_saved_log_text_is_not_opened_as_a_path(isolated):
    block = _block(_shrink("tsc", isolated))
    assert "auth.ts:1" in block
    assert not (isolated / "auth.ts").exists()


def test_query_timed_out_text_is_not_a_connection_claim(isolated):
    output = "Query timed out after 30s\n" * 50
    result = _envelope(output, 1, "curl https://192.0.2.1/slow")
    assert shrink.transform("terminal", {"command": "curl https://192.0.2.1/slow"}, result, root=isolated, json_shape=False) is None


def test_empty_session_still_shrinks(isolated):
    result = _envelope(_log("cargo"), 101, MANIFEST["cargo"]["command"])
    block = hooks.on_transform(None, tool_name="terminal", args={"command": MANIFEST["cargo"]["command"]}, result=result, session_id="", turn_id="")
    body = json.loads(block)
    assert body["exit_code"] == 101
    assert "auth::token_expired" in body["output"]
    assert "src/lib.rs" not in body["output"]


def test_unicode_log_name_is_refused(isolated):
    body = json.loads(tools.handle_fail_full({"path": "\u00e9.log"}))
    assert body["error_type"] == "path_refused"


def test_manifest_and_skill_match_the_tool():
    text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    assert "provides_tools:\n  - fail_full\n" in text
    assert "transform_tool_result" in text
    assert "pre_llm_call" in text
    assert 'requires_hermes: ">=0.21.4"' in text
    assert "platforms: [linux, macos]" in text
    schema = (ROOT / "schemas.py").read_text(encoding="utf-8")
    first = "Show one slice of a saved failure log."
    assert first in schema
    assert len(first) <= 60
    assert not first.lower().startswith("read-only")
    skill = (ROOT / "skills" / "read-a-failure" / "SKILL.md").read_text(encoding="utf-8")
    desc = [line for line in skill.splitlines() if line.startswith("description:")][0]
    assert len(desc.split(": ", 1)[1]) <= 223
    assert "requires_" not in skill.split("---", 2)[1]
    assert "Before you call fail_full" in skill
    for kind in ("bad_argument", "path_refused", "not_found", "bad_offset", "bad_limit", "internal"):
        assert kind in skill
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "fail_full does not open an approval card" in readme
    assert "_config_version: 50" in readme
    raw = {
        "pytest": 15058,
        "jest": 4277,
        "vitest": 4762,
        "cargo": 4469,
        "go": 1615,
        "tsc": 9184,
        "ruff": 28654,
        "eslint": 6292,
    }
    shrunk = {
        "pytest": 300,
        "jest": 176,
        "vitest": 326,
        "cargo": 186,
        "go": 168,
        "tsc": 1142,
        "ruff": 589,
        "eslint": 789,
    }
    for name, count in raw.items():
        assert len(_log(name)) == count
        assert f"| {name} | {count} |" in readme
        assert f"| {shrunk[name]} |" in readme
    assert "19 characters" in readme
    assert "trailing newline" in readme
    assert "o200k_base" in readme
    assert "unmeasured" in readme
    assert "ja-alias" not in readme
    assert "such as `全部見せて`" in readme
    assert "the product" not in readme.lower()


def test_input_kinds_cover_every_row():
    seen = []
    for row in ROWS:
        seen.append(row["id"])
        parsed = parse.classify(row["log"], command=" ".join(row.get("argv", [])))
        if row["dialect"] is None:
            assert parsed is None, row["id"]
            continue
        assert parsed is not None and parsed[0] == row["dialect"], row["id"]
        got = [(item.file, item.line, item.name, item.point) for item in parsed[1]]
        assert got == row["expect"], (row["id"], got)
        names = [item.name for item in parsed[1]]
        for absent in row.get("absent_names", []):
            assert absent not in names, row["id"]
        for absent in row.get("absent_files", []):
            assert all(item.file != absent for item in parsed[1]), row["id"]
        for absent in row.get("absent_points", []):
            assert all(absent not in item.point for item in parsed[1]), row["id"]
        if row.get("summary_cols") is not None:
            measured = parsed[1][0].anchor
            if not measured.startswith(("FAILED", "ERROR")):
                summary_lines = [
                    ln.strip() for ln in row["log"].splitlines()
                    if ln.startswith(("FAILED ", "ERROR "))
                ]
                measured = summary_lines[-1]
            assert parse._cols(measured) == row["summary_cols"], (row["id"], parse._cols(measured), measured)
        if row.get("block_rerun"):
            assert any(item.block_rerun for item in parsed[1]), row["id"]
        if "rerun" in row:
            line = command.build_rerun(row["dialect"], row["argv"], parsed[1])
            assert line == row["rerun"], (row["id"], line)
        if row.get("anchor_prefix"):
            anchor = parsed[1][0].anchor
            assert anchor.startswith(row["anchor_prefix"]), (row["id"], anchor)
            offset = parse.byte_offset(row["log"], anchor, parsed[1][0].anchor_from)
            assert row["log"].encode()[offset:].decode().startswith(anchor), row["id"]
    assert seen == [row["id"] for row in ROWS]
    assert len(seen) == len(set(seen)) == len(ROWS)
    assert len(LIVE_ROWS) == 4


def _pytest_env() -> dict[str, str]:
    """Pytest on CI keeps a summary message that a terminal of width 80 cuts."""
    env = os.environ.copy()
    for key in ("CI", "BUILD_NUMBER", "PYTEST_ADDOPTS", "FORCE_COLOR", "CLICOLOR_FORCE", "CLICOLOR", "NO_COLOR", "COLUMNS"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _run_pytest(cwd: Path, args: list[str]) -> tuple[int, str]:
    ran = subprocess.run(
        [sys.executable, "-m", "pytest", "--color=no", "-p", "no:cacheprovider", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
        env=_pytest_env(),
    )
    return ran.returncode, ran.stdout + ran.stderr


def test_real_pytest_rows_match_the_table(tmp_path):
    """The three shapes from a real pytest run, not a hand-written log."""
    assert list(LIVE_ROWS) == [
        "pytest-real-captured-stale",
        "pytest-real-helper",
        "pytest-real-dotdot",
        "pytest-real-dashs",
    ]
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "test_prints_old.py").write_text(
        "from pathlib import Path\n"
        "def test_prints_old_log():\n"
        "    print(Path(%r).read_text(encoding='utf-8'))\n"
        "    assert 1 == 2\n" % str(FIXTURES / "pytest.log"),
        encoding="utf-8",
    )
    code, text = _run_pytest(stale, ["-q", "test_prints_old.py"])
    assert code == 1
    parsed = parse.classify(text)
    assert parsed is not None and parsed[0] == "pytest"
    assert [(item.name, item.line, item.point) for item in parsed[1]] == [
        ("test_prints_old_log", 0, "assert 1 == 2"),
    ]
    assert parsed[1][0].file.endswith("test_prints_old.py")
    assert "test_token_expired" not in [item.name for item in parsed[1]]

    helper = tmp_path / "helper"
    helper.mkdir()
    (helper / "helper.py").write_text("def check(value):\n    assert value == 1\n", encoding="utf-8")
    (helper / "test_real.py").write_text(
        "from helper import check\n\ndef test_real_bug():\n    print('pad\\n' * 80)\n    check(0)\n",
        encoding="utf-8",
    )
    code, text = _run_pytest(helper, ["-q", "test_real.py"])
    assert code == 1
    parsed = parse.classify(text)
    assert parsed is not None
    item = parsed[1][0]
    assert item.file.endswith("test_real.py"), item.file
    assert "helper.py" not in item.file
    assert item.line == 0
    assert item.name == "test_real_bug"
    assert item.point
    assert "helper.py" not in item.point
    rerun = command.build_rerun("pytest", [sys.executable, "-m", "pytest", "test_real.py"], parsed[1])
    assert rerun is not None
    assert rerun.endswith("test_real.py -k test_real_bug")
    assert "helper.py" not in rerun

    # /var and /private/var are one directory and two path strings. pytest then
    # prints an absolute frame and a node id that walks through "..".
    with tempfile.TemporaryDirectory(prefix="fs-deep-") as raw:
        scratch = Path(raw)
        link_deep = scratch.joinpath(*["d"] * 12)
        link_deep.mkdir(parents=True)
        target = scratch / "work"
        target.mkdir()
        token = target / "test_token.py"
        token.write_text(
            "def test_token_expired():\n    print('stale\\n' * 80)\n    assert 1 == 0\n",
            encoding="utf-8",
        )
        deep = Path(os.path.realpath(link_deep))
        code, text = _run_pytest(deep, ["-q", str(token)])
        assert code == 1
        parsed = parse.classify(text)
        assert parsed is not None and len(parsed[1]) == 1
        item = parsed[1][0]
        assert item.name == "test_token_expired"
        assert item.line == 0
        assert item.point == "assert 1 == 0"
        assert item.file.endswith("test_token.py")
        assert ".." in item.file.split("/")
        assert item.block_rerun is True
        rerun = command.build_rerun(
            "pytest",
            [sys.executable, "-m", "pytest", "-q", str(token)],
            parsed[1],
        )
        assert rerun is None

    dashs = tmp_path / "dashs"
    dashs.mkdir()
    (dashs / "test_same.py").write_text(
        "from pathlib import Path\n"
        "def test_token_expired():\n"
        "    print(Path(%r).read_text(encoding='utf-8'))\n"
        "    assert 1 == 2\n" % str(FIXTURES / "pytest.log"),
        encoding="utf-8",
    )
    code, text = _run_pytest(dashs, ["-q", "-s", "test_same.py"])
    assert code == 1
    parsed = parse.classify(text)
    assert parsed is not None and parsed[0] == "pytest"
    assert len(parsed[1]) == 1
    item = parsed[1][0]
    assert item.name == "test_token_expired"
    assert item.line == 0
    assert item.point == "assert 1 == 2"
    assert item.file.endswith("test_same.py")
    assert "test_auth.py" not in item.file

    def shrink_of(command_line: str, code: int, output: str):
        return shrink.transform(
            "terminal",
            {"command": command_line},
            {"output": output, "exit_code": code, "error": None},
            root=tmp_path / "logs",
            json_shape=False,
        )

    (tmp_path / "logs").mkdir()
    styles = (
        ("line", ["-q", "--tb=line", "test_same.py"]),
        ("short", ["-q", "--tb=short", "test_same.py"]),
        ("no-s", ["-q", "-s", "--tb=no", "test_same.py"]),
        ("long-s", ["-q", "-s", "test_same.py"]),
    )
    for label, args in styles:
        code, text = _run_pytest(dashs, args)
        assert code == 1, label
        parsed = parse.classify(text)
        assert parsed is not None and parsed[0] == "pytest", label
        assert len(parsed[1]) == 1, label
        item = parsed[1][0]
        assert item.name == "test_token_expired", label
        assert item.file.endswith("test_same.py"), (label, item.file)
        assert "test_auth.py" not in item.file, label
        assert "stale token" not in item.point, (label, item.point)
        assert item.point == "assert 1 == 2", (label, item.point)
        assert item.line == 0, (label, item.line)
        if label in {"line", "no-s"} and len(text) > 2000:
            tail_command = " ".join([sys.executable, "-m", "pytest", *args])
            tail_parsed = parse.classify(text[-2000:], command=tail_command)
            assert tail_parsed is not None and tail_parsed[0] == "pytest", label
            tail_item = tail_parsed[1][0]
            assert tail_item.file.endswith("test_same.py"), (label, tail_item.file)
            assert "test_auth.py" not in tail_item.file, label
            assert tail_item.line == 0, (label, tail_item.line, tail_item.point)
            assert tail_item.point == "assert 1 == 2", label
        packed = shrink_of(" ".join([sys.executable, "-m", "pytest", *args]), code, text)
        assert packed is not None, label
        block = json.loads(packed)["output"]
        assert json.loads(packed)["exit_code"] == 1
        assert "tests/test_auth.py" not in block, label
        assert "stale token" not in block, label
        assert "test_same.py test_token_expired" in block
        assert "test_same.py:" not in block

    fragment = tmp_path / "fragment"
    fragment.mkdir()
    printed = (
        "______________________________ test_token_expired ______________________________\n"
        "E       assert 1 == 2\n"
        "test_same.py:167: AssertionError\n"
    )
    pad = "\n".join(f"noise line {index:03d}" for index in range(80))
    (fragment / "test_same.py").write_text(
        "def test_token_expired():\n"
        f"    print({pad!r})\n"
        f"    print({printed!r})\n"
        "    assert 1 == 2\n",
        encoding="utf-8",
    )
    for label, args in (
        ("fragment-long", ["-q", "test_same.py"]),
        ("fragment-short", ["-q", "--tb=short", "test_same.py"]),
        ("fragment-line", ["-q", "--tb=line", "test_same.py"]),
        ("fragment-s", ["-q", "-s", "test_same.py"]),
        ("fragment-no-s", ["-q", "-s", "--tb=no", "test_same.py"]),
    ):
        code, text = _run_pytest(fragment, args)
        assert code == 1, label
        parsed = parse.classify(text)
        assert parsed is not None and len(parsed[1]) == 1, label
        item = parsed[1][0]
        assert item.name == "test_token_expired", label
        assert item.file.endswith("test_same.py"), (label, item.file)
        assert item.line == 0, (label, item.line, item.point)
        assert "167" not in item.point
        assert item.point == "assert 1 == 2"

    names = tmp_path / "names"
    names.mkdir()
    (names / "test_names.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('who', [\n"
        "    'hello world', 'say \"hi\"', 'José', 'Jose', 'a - b', 'slash/name', 'q?x',\n"
        "])\n"
        "def test_person(who):\n"
        "    assert who == 'present'\n",
        encoding="utf-8",
    )
    code, text = _run_pytest(names, ["-q", "test_names.py"])
    assert code == 1
    parsed = parse.classify(text)
    assert parsed is not None and parsed[0] == "pytest"
    got_names = [item.name for item in parsed[1]]
    assert got_names == [
        'test_person[hello world]',
        'test_person[say "hi"]',
        r"test_person[Jos\xe9]",
        "test_person[Jose]",
        "test_person[a - b]",
        "test_person[slash/name]",
        "test_person[q?x]",
    ]
    for item in parsed[1]:
        assert item.file.endswith("test_names.py")
        assert item.line == 0
        assert item.point
    assert command.build_rerun(
        "pytest",
        [sys.executable, "-m", "pytest", "-q", "test_names.py"],
        parsed[1],
    ) is None

    native = tmp_path / "native"
    native.mkdir()
    (native / "test_plain.py").write_text(
        "def test_plain():\n    assert 1 == 2\n",
        encoding="utf-8",
    )
    code, text = _run_pytest(native, ["-q", "--tb=native", "test_plain.py"])
    assert code == 1
    parsed = parse.classify(text)
    assert parsed is not None and len(parsed[1]) == 1
    item = parsed[1][0]
    assert item.name == "test_plain"
    assert item.line == 0
    assert item.file.endswith("test_plain.py")
    assert "runner.py" not in item.file
    assert item.point == "assert 1 == 2"


def test_process_manage_tail_of_the_measured_pytest_log_stays_whole(isolated):
    output = _log("pytest")
    assert len(output) == 15058
    tail = output[-2000:]
    assert parse.classify(tail) is None
    command_line = MANIFEST["pytest"]["command"]
    exited = {"status": "exited", "command": command_line, "output": tail, "exit_code": 1}
    assert shrink.transform("process_manage", {"action": "wait"}, exited, root=isolated, json_shape=False) is None


def test_sliced_pytest_tail_keeps_the_live_line(tmp_path, isolated):
    work = tmp_path / "work"
    work.mkdir()
    (work / "test_token.py").write_text(
        "def test_token_expired():\n"
        "    print('\\n'.join(f'stale token line {i:03d}' for i in range(70)))\n"
        "    assert 1 == 0\n",
        encoding="utf-8",
    )
    code, text = _run_pytest(work, ["-q", "test_token.py"])
    assert code == 1
    assert len(text) > 2000
    tail = text[-2000:]
    assert "FAILURES" not in tail
    assert "test_token.py:3" in tail
    parsed = parse.classify(tail)
    assert parsed is not None and parsed[0] == "pytest"
    item = parsed[1][0]
    assert item.line == 0
    assert item.file.endswith("test_token.py")
    assert item.name == "test_token_expired"
    assert item.point == "assert 1 == 0"
    command_line = sys.executable + " -m pytest -q test_token.py"
    raw = shrink.transform(
        "process_manage",
        {"action": "wait"},
        {"status": "exited", "command": command_line, "output": tail, "exit_code": 1},
        root=isolated,
        json_shape=False,
    )
    assert raw is not None
    body = json.loads(raw)
    assert body["exit_code"] == 1
    assert "test_token.py test_token_expired" in body["output"]
    assert "test_token.py:" not in body["output"]
    assert "rerun:" in body["output"]
    assert "outside this tail" not in body["output"]


def test_printed_capture_tail_is_not_the_failure_line(tmp_path, isolated):
    """A 2000-character tail that starts inside captured stdout.

    The shapes are the rows pytest-tail-capture-section,
    pytest-tail-printed-abs-line, pytest-tail-plain-stdout, and a --tb=line
    capture whose crash line is still the last line.
    """
    scratch = tmp_path / "tails"
    scratch.mkdir()
    pad = "\n".join(f"noise {i:04d} " + ("x" * 60) for i in range(90))
    section = "\n".join([
        pad,
        "=" * 40,
        "______________________________ test_token_expired ______________________________",
        "E       assert 1 == 0",
        "/tmp/old/test_token.py:999: AssertionError",
    ])
    cases = (
        (
            "section",
            "def test_token_expired():\n"
            f"    print({section!r})\n"
            "    assert 1 == 0\n",
            ["-q", "test_token.py"],
            False,
        ),
        (
            "absline",
            "def test_token_expired():\n"
            f"    print({pad!r})\n"
            "    print('/tmp/old/test_token.py:999: assert 1 == 0')\n"
            "    assert 1 == 0\n",
            ["-q", "test_token.py"],
            False,
        ),
        (
            "plain",
            "def test_token_expired():\n"
            "    print('\\n'.join(f'row {i:04d}' for i in range(200)))\n"
            "    assert 1 == 0\n",
            ["-q", "test_token.py"],
            False,
        ),
        (
            "tb-line",
            "def test_token_expired():\n"
            f"    print({pad!r})\n"
            "    assert 1 == 0\n",
            ["-q", "--tb=line", "test_token.py"],
            True,
        ),
    )
    for label, source, args, _keep_line in cases:
        work = scratch / label
        work.mkdir()
        (work / "test_token.py").write_text(source, encoding="utf-8")
        code, text = _run_pytest(work, args)
        assert code == 1, label
        assert len(text) > 2000, label
        tail = text[-2000:]
        command_line = " ".join([sys.executable, "-m", "pytest", *args])
        parsed = parse.classify(tail, command=command_line)
        assert parsed is not None and parsed[0] == "pytest", label
        item = parsed[1][0]
        assert item.name == "test_token_expired", label
        assert item.file.endswith("test_token.py"), (label, item.file)
        assert "/tmp/old" not in item.file, (label, item.file)
        assert item.line == 0, (label, item.line, item.file)
        log_root = isolated / label
        log_root.mkdir()
        raw = shrink.transform(
            "process_manage",
            {"action": "wait"},
            {
                "status": "exited",
                "command": command_line,
                "output": tail,
                "exit_code": 1,
            },
            root=log_root,
            json_shape=False,
        )
        assert raw is not None, label
        body = json.loads(raw)
        assert body["exit_code"] == 1
        output = body["output"]
        assert "/tmp/old" not in output, label
        assert "test_token.py:999" not in output, label
        assert "test_token.py test_token_expired" in output
        assert "test_token.py:" not in output
        assert "outside this tail" not in output
        assert "rerun:" in output
        assert "/tmp/old" not in output.split("rerun:", 1)[1]


def test_omitted_file_is_named_and_rerun(isolated):
    blocks = []
    for index in range(8):
        blocks.append(
            f"___________________________________ test_a[{index}] ___________________________________\n"
            f"E       assert {index} == -1\n"
            f"test_a.py:4: AssertionError\n"
        )
    for index in range(2):
        blocks.append(
            f"___________________________________ test_b[{index}] ___________________________________\n"
            f"E       assert {index} == -1\n"
            f"test_b.py:4: AssertionError\n"
        )
    failed = []
    for index in range(8):
        failed.append(f"FAILED test_a.py::test_a[{index}] - assert {index} == -1")
    for index in range(2):
        failed.append(f"FAILED test_b.py::test_b[{index}] - assert {index} == -1")
    log = (
        "=================================== FAILURES ===================================\n"
        + "".join(blocks)
        + "=========================== short test summary info ============================\n"
        + "\n".join(failed)
        + "\n============================== 10 failed in 0.04s ==============================\n"
    )
    log = ("pad\n" * 40) + log
    command_line = "python -m pytest -q test_a.py test_b.py"
    raw = shrink.transform(
        "terminal",
        {"command": command_line},
        {"output": log, "exit_code": 1, "error": None},
        root=isolated,
        json_shape=False,
    )
    assert raw is not None
    output = json.loads(raw)["output"]
    assert "showing 8 of 10 failures." in output
    assert "also test_b.py (2)." in output
    assert "test_b.py" in output.split("rerun:", 1)[1]
    assert "test_b[0]" in output.split("rerun:", 1)[1]
    assert "test_b[1]" in output.split("rerun:", 1)[1]


_LONG = "P" * 2400
_FAKE = "/tmp/old/test_token.py:999: assert 1 == 0"
_FOOTER = "========================= 1 failed, 40 passed in 0.07s ========================="
_CONFIGS = {
    "ini": {"pytest.ini": "[pytest]\naddopts = --tb=line\n"},
    "pyproject": {"pyproject.toml": '[tool.pytest.ini_options]\naddopts = "--tb=line"\n'},
    "pyproject-list": {"pyproject.toml": '[tool.pytest.ini_options]\naddopts = ["--tb=line"]\n'},
    "setupcfg": {"setup.cfg": "[tool:pytest]\naddopts = --tb=line\n"},
    "tox": {"tox.ini": "[pytest]\naddopts = --tb=line\n"},
    "toml": {"pytest.toml": '[pytest]\naddopts = ["--tb=line"]\n'},
    "dottoml": {".pytest.toml": '[pytest]\naddopts = ["--tb=line"]\n'},
    "dotini": {".pytest.ini": "[pytest]\naddopts = --tb=line\n"},
    "env": {},
    "none": {},
}


def _crash_files(shape: str, path: Path, rel: str = "test_token.py") -> dict[str, str]:
    """Source for one crash-line row. Line numbers match CRASH_LINE_ROWS."""
    cited = str(path)
    if shape == "long":
        body = f"def test_token_expired():\n    print({_LONG!r})\n    assert 1 == 0\n"
    elif shape == "short":
        body = "def test_token_expired():\n    assert 1 == 0\n"
    elif shape == "fake":
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({_FAKE!r})\n"
            "    assert 1 == 0\n"
        )
    elif shape == "banner":
        banner = "=================================== FAILURES ==================================="
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({banner!r})\n"
            f"    print({_FAKE!r})\n"
            "    assert 1 == 0\n"
        )
    elif shape == "errors":
        banner = "==================================== ERRORS ===================================="
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({banner!r})\n"
            f"    print({_FAKE!r})\n"
            "    assert 1 == 0\n"
        )
    elif shape == "foreign-assert":
        other = path.parent / "test_other.py"
        return {
            "test_other.py": "x = 1\nassert 1 == 0\n",
            "test_token.py": (
                "def test_token_expired():\n"
                f"    print({_LONG!r})\n"
                f"    print({str(other) + ':2: assert 1 == 0'!r})\n"
                "    assert 1 == 0\n"
            ),
        }
    elif shape == "foreign-value":
        mod = path.parent / "mod.py"
        return {
            "mod.py": "def f():\n    return 1\n",
            "test_token.py": (
                "def test_token_expired():\n"
                f"    print({_LONG!r})\n"
                f"    print({str(mod) + ':2: ValueError: nope'!r})\n"
                "    raise ValueError('nope')\n"
            ),
        }
    elif shape == "same-return":
        body = (
            "def unused():\n"
            "    return 1\n"
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({cited + ':2: ValueError: nope'!r})\n"
            "    raise ValueError('nope')\n"
        )
    elif shape == "raise-helper":
        return {
            "helper.py": "def boom():\n    raise ValueError('nope')\n",
            "test_token.py": (
                "from helper import boom\n"
                "def test_token_expired():\n"
                f"    print({_LONG!r})\n"
                "    boom()\n"
            ),
        }
    elif shape == "footer":
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({_FOOTER!r})\n"
            f"    print({cited + ':5: assert 1 == 0'!r})\n"
            "    assert 1 == 0\n"
        )
    elif shape == "def-line":
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({cited + ':1: assert 1 == 0'!r})\n"
            "    assert 1 == 0\n"
        )
    elif shape == "other":
        body = (
            "def test_token_expired():\n"
            "    assert True\n"
            f"    print({_LONG!r})\n"
            f"    print({cited + ':2: assert 1 == 0'!r})\n"
            "    assert 1 == 0\n"
        )
    elif shape == "tb-no":
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({cited + ':4: assert 1 == 0'!r})\n"
            "    assert 1 == 0\n"
        )
    elif shape == "raise-bare":
        body = f"def test_token_expired():\n    print({_LONG!r})\n    raise AssertionError\n"
    elif shape == "raise-msg":
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            "    raise AssertionError('token expired')\n"
        )
    elif shape == "divzero":
        body = f"def test_token_expired():\n    print({_LONG!r})\n    1 / 0\n"
    elif shape == "raise-footer":
        body = (
            "def test_token_expired():\n"
            f"    print({_LONG!r})\n"
            f"    print({_FOOTER!r})\n"
            "    raise AssertionError\n"
        )
    elif shape == "foreign-bare":
        other = path.parent / "test_other.py"
        return {
            "test_other.py": "x = 1\nassert 1 == 0\n",
            rel: (
                "def test_token_expired():\n"
                f"    print({_LONG!r})\n"
                f"    print({str(other) + ':2: AssertionError'!r})\n"
                "    raise AssertionError\n"
            ),
        }
    elif shape == "foreign-raise-live":
        mod = path.parent / "mod.py"
        return {
            "mod.py": "def f():\n    raise ValueError('nope')\n",
            rel: (
                "def test_token_expired():\n"
                f"    print({_LONG!r})\n"
                f"    print({str(mod) + ':2: ValueError: nope'!r})\n"
                "    raise ValueError('nope')\n"
            ),
        }
    elif shape == "comment-bare":
        body = (
            "def test_token_expired():\n"
            "    # AssertionError\n"
            f"    print({_LONG!r})\n"
            f"    print({cited + ':2: AssertionError'!r})\n"
            "    raise AssertionError\n"
        )
    elif shape == "helper":
        return {
            "helper.py": "def boom(value):\n    assert value == 1\n",
            "test_token.py": (
                "from helper import boom\n"
                "def test_token_expired():\n"
                f"    print({_LONG!r})\n"
                "    boom(0)\n"
            ),
        }
    else:
        raise AssertionError(shape)
    return {rel: body}


def test_summary_cite_has_no_outside_sentence():
    """A summary cite names the node id. It does not guess a line that is absent."""
    absolute = parse.Finding(
        "/var/work/test_token.py", 0, "test_token_expired", "assert 1 == 0", "FAILED"
    )
    relative = parse.Finding(
        "test_token.py", 0, "test_token_expired", "assert 1 == 0", "FAILED"
    )
    for finding in (absolute, relative):
        block = shrink._render("pytest", 1, [finding], "/tmp/saved.log", 0, None)
        assert "outside this tail" not in block
        assert "test_token_expired" in block
        assert ":0" not in block


def test_crash_line_rows_cite_the_summary_node(tmp_path, monkeypatch):
    """Every printed path and every --tb setting still cites the summary node id."""
    ids = [row["id"] for row in CRASH_LINE_ROWS]
    assert ids == list(dict.fromkeys(ids))
    assert len(ids) == 50
    assert not Path(_FAKE.split(":", 1)[0]).exists()
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("BUILD_NUMBER", raising=False)
    env = _pytest_env()
    for row in CRASH_LINE_ROWS:
        work = tmp_path / row["id"]
        work.mkdir()
        rel = row.get("rel", "test_token.py")
        target = work / rel
        files = _crash_files(row["shape"], target, rel)
        files.update(_CONFIGS[row["config"]])
        for name, text in files.items():
            dest = work / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        run_env = dict(env)
        if row["config"] == "env":
            run_env["PYTEST_ADDOPTS"] = "--tb=line"
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--color=no", "-p", "no:cacheprovider", *row["args"]],
            cwd=work,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
            env=run_env,
        )
        assert proc.returncode == 1, (row["id"], proc.stdout, proc.stderr)
        text = proc.stdout + (("\n" + proc.stderr) if proc.stderr else "")
        tail = text[-2000:]
        for label, sample in (("full", text), ("tail", tail)):
            parsed = parse.classify(sample, command=row["command"])
            assert parsed is not None and parsed[0] == "pytest", (row["id"], label)
            item = parsed[1][0]
            assert item.name == "test_token_expired", (row["id"], label)
            assert item.line == 0, (row["id"], label, item.file, item.line, item.point)
            assert item.file.endswith("test_token.py"), (row["id"], label, item.file)
            assert "helper.py" not in item.file, (row["id"], label, item.file)
            assert "test_other.py" not in item.file, (row["id"], label, item.file)
            assert item.file.endswith("mod.py") is False
            assert "/tmp/old" not in item.file, (row["id"], label)
        root = tmp_path / (row["id"] + "-logs")
        root.mkdir()
        raw = shrink.transform(
            "process_manage",
            {"action": "wait"},
            {
                "status": "exited",
                "command": row["command"],
                "output": tail,
                "exit_code": 1,
                "error": None,
            },
            root=root,
            json_shape=False,
        )
        if raw is None:
            assert not shrink.is_long(tail), row["id"]
            continue
        output = json.loads(raw)["output"]
        assert "/tmp/old" not in output, row["id"]
        assert "exit 1" in output
        assert "outside this tail" not in output, row["id"]
        assert "test_token.py test_token_expired" in output, (row["id"], output)
        assert "helper.py" not in output, (row["id"], output)
        assert "test_other.py" not in output, (row["id"], output)
        assert "mod.py" not in output, (row["id"], output)


def test_runner_name_ignores_case(isolated):
    assert command.runner_kind(command.simple_argv("Pytest tests/test_auth.py")) == "pytest"
    assert command.runner_kind(command.simple_argv("python -m Pytest -q tests/test_auth.py")) == "pytest"
    assert command.runner_kind(command.simple_argv("Jest auth.test.js")) == "jest"
    assert command.runner_kind(command.simple_argv("npx Jest auth.test.js")) == "jest"
    assert command.runner_kind(command.simple_argv("Cargo test")) == "cargo"
    assert command.runner_kind(command.simple_argv("Go test .")) == "go"
    assert command.runner_kind(command.simple_argv("Ruff check auth.py")) == "ruff"
    assert command.runner_kind(command.simple_argv("Tsc --pretty false")) == "tsc"
    assert command.runner_kind(command.simple_argv("Eslint lint-me.js")) == "eslint"
    assert command.runner_kind(command.simple_argv("npx Vitest run token.test.js")) == "vitest"
    command_line = "Pytest -q tests/test_auth.py"
    raw = shrink.transform(
        "terminal",
        {"command": command_line},
        _envelope(_log("pytest"), 1, command_line),
        root=isolated,
        json_shape=False,
    )
    output = json.loads(raw)["output"]
    assert "tests/test_auth.py test_token_expired" in output
    assert "tests/test_auth.py:" not in output
    assert "rerun: Pytest " in output
    assert "-k" in output.split("rerun:", 1)[1]
