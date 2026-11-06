"""Turn a long classified failure into a short block. Leave everything else whole."""

from __future__ import annotations

import json
from typing import Any

from . import command, parse, store

MIN_LINES = 40
MIN_CHARS = 1500
JSON_CHARS = 4000
SHOW_FINDINGS = 8
_TERMINAL = "terminal"
_PROCESS = "process_manage"


def is_long(output: str) -> bool:
    if len(output) >= MIN_CHARS:
        return True
    if output.endswith("\n"):
        lines = output.count("\n")
    else:
        lines = output.count("\n") + (1 if output else 0)
    return lines >= MIN_LINES


def _original(result: Any) -> str | None:
    if isinstance(result, str):
        return result
    if isinstance(result, (dict, list)):
        return json.dumps(result, ensure_ascii=False)
    return None


def _payload(result: Any) -> Any:
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None
    if isinstance(result, (dict, list)):
        return result
    return None


def _command_from(args: Any, payload: Any) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("command"), str):
        return payload["command"]
    if isinstance(args, dict) and isinstance(args.get("command"), str):
        return args["command"]
    return ""


def _exit_code(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _failure_view(tool_name: str, args: Any, result: Any) -> tuple[str, int, str] | None:
    payload = _payload(result)
    if not isinstance(payload, dict):
        return None
    if payload.get("error") not in (None, ""):
        return None
    if tool_name == _TERMINAL:
        output = payload.get("output")
        code = _exit_code(payload.get("exit_code"))
        if not isinstance(output, str) or code is None or code == 0:
            return None
        command = ""
        if isinstance(args, dict) and isinstance(args.get("command"), str):
            command = args["command"]
        return output, code, command
    if tool_name == _PROCESS:
        if payload.get("status") != "exited":
            return None
        output = payload.get("output")
        code = _exit_code(payload.get("exit_code"))
        if not isinstance(output, str) or code is None or code == 0:
            return None
        if "output" not in payload:
            return None
        return output, code, _command_from(args, payload)
    return None


def _pack(result: Any, original: str, block: str) -> str | None:
    """Put the short block in output and keep every other field, including exit_code."""
    payload = _payload(result)
    if not isinstance(payload, dict) or "output" not in payload:
        return None
    updated = dict(payload)
    updated["output"] = block
    preview = updated.get("output_preview")
    if isinstance(preview, str) and len(preview) > len(block):
        updated["output_preview"] = block
    text = json.dumps(updated, ensure_ascii=False)
    if len(text) >= len(original):
        return None
    return text


def _failure_fields(value: Any, original: str) -> dict | None:
    """Fields Hermes uses to call a result a failure, or None when it would not.

    An empty dict means the text has the mark and there is no field to keep.
    """
    head = original[:500].lower()
    string_mark = '"error"' in head or '"failed"' in head or original.startswith("Error")
    if isinstance(value, dict):
        err = value.get("error") or value.get("message")
        dict_mark = bool(err) and (value.get("success") is False or "error" in value)
        if not string_mark and not dict_mark:
            return None
        kept = {}
        for key in ("success", "error", "message", "exit_code", "status"):
            if key in value:
                kept[key] = value[key]
        if kept:
            return kept
        return {} if string_mark else None
    return {} if string_mark else None


def _cite(item) -> str:
    if item.line:
        return f"{item.file}:{item.line} {item.name}".rstrip()
    if item.file:
        return f"{item.file} {item.name}".rstrip()
    return item.name


def _also(omitted: list) -> str:
    labels = []
    for item in omitted:
        label = item.file or item.name or "(unnamed)"
        if label not in labels:
            labels.append(label)
    parts = []
    for label in labels:
        count = sum(1 for item in omitted if (item.file or item.name or "(unnamed)") == label)
        parts.append(f"{label} ({count})")
    return "also " + ", ".join(parts) + "."


def _render(
    dialect: str,
    code: int,
    findings: list,
    path: str,
    offset: int,
    rerun: str | None,
) -> str:
    shown = findings[:SHOW_FINDINGS]
    lines = [f"{dialect} failed. exit {code}."]
    if len(findings) > len(shown):
        lines.append(f"showing {len(shown)} of {len(findings)} failures.")
    for item in shown:
        lines.append(_cite(item))
        if item.point:
            lines.append(f"  {item.point}")
    omitted = findings[len(shown):]
    if omitted:
        lines.append(_also(omitted))
    lines.append(f"full log: {path} offset={offset}")
    if rerun:
        lines.append(f"rerun: {rerun}")
    return "\n".join(lines) + "\n"


def _shrink_failure(output: str, code: int, command_line: str, root):
    if not is_long(output):
        return None
    parsed = parse.classify(output, command=command_line)
    if parsed is None:
        return None
    dialect, findings = parsed
    argv = command.simple_argv(command_line) if command_line else None
    kind = command.runner_kind(argv)
    if kind is not None and kind != dialect:
        return None
    rerun = None
    if argv is not None and kind == dialect:
        rerun = command.build_rerun(dialect, argv, findings)
    saved = store.save_text(root, output)
    if saved is None:
        return None
    offset = parse.byte_offset(output, findings[0].anchor, findings[0].anchor_from)
    block = _render(dialect, code, findings, str(saved), offset, rerun)
    return block, saved


def _type_sketch(value: Any, depth: int = 0) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        if not value:
            return "array[0]"
        return f"array[{len(value)}] of {_type_sketch(value[0], depth + 1)}"
    if isinstance(value, dict):
        if depth >= 2:
            return "object"
        parts = []
        for index, (key, item) in enumerate(value.items()):
            if index >= 8:
                parts.append("...")
                break
            parts.append(f"{key}: {_type_sketch(item, depth + 1)}")
        return "object{" + ", ".join(parts) + "}"
    return "other"


def _first_item(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, dict):
        for item in value.values():
            if isinstance(item, list) and item:
                return item[0]
        return value
    return value


def _shape_json(original: str, value: Any, root):
    if not isinstance(value, (dict, list)):
        return None
    saved = store.save_text(root, original)
    if saved is None:
        return None
    raw = json.dumps(_first_item(value), ensure_ascii=False)
    note = ""
    if len(raw) > 400:
        raw = raw[:400]
        note = "\nfirst item truncated."
    block = (
        f"json {_type_sketch(value)}\n"
        f"first: {raw}{note}\n"
        f"full log: {saved} offset=0\n"
    )
    return block, saved


def transform(tool_name: str, args: Any, result: Any, *, root, json_shape: bool) -> str | None:
    """Return a shorter string, or None when the result must stay as it arrived.

    A classified failure stays JSON. The short block replaces output. exit_code
    and the other fields stay, so Hermes still sees the failure.
    """
    original = _original(result)
    if original is None or root is None:
        return None
    failure = _failure_view(tool_name, args, result)
    if failure is not None:
        output, code, cmd = failure
        built = _shrink_failure(output, code, cmd, root)
        if built is None:
            return None
        block, saved = built
        packed = _pack(result, original, block)
        if packed is None:
            store.remove_log(saved)
            return None
        return packed
    if not json_shape or tool_name in {_TERMINAL, _PROCESS}:
        return None
    if len(original) < JSON_CHARS:
        return None
    value = _payload(result)
    shaped = _shape_json(original, value, root)
    if shaped is None:
        return None
    block, saved = shaped
    fields = _failure_fields(value, original)
    if fields is None:
        text = block
    elif not fields:
        store.remove_log(saved)
        return None
    else:
        body = dict(fields)
        body["output"] = block
        text = json.dumps(body, ensure_ascii=False)
    if len(text) >= len(original):
        store.remove_log(saved)
        return None
    return text
