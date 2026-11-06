"""fail_full reads one saved log and does not write."""

from __future__ import annotations

import json
from typing import Any

from . import store
from .errors import failure, success

_FIELDS = frozenset({"path", "offset", "limit"})


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _reject(args: dict) -> dict | None:
    if not isinstance(args, dict):
        return failure("bad_argument", "Arguments must be an object.")
    extra = sorted(set(args) - _FIELDS)
    if extra:
        return failure("bad_argument", f"{extra[0]} is not accepted.")
    if "path" not in args:
        return failure("bad_argument", "path is required.")
    if not isinstance(args["path"], str):
        return failure("bad_argument", "path must be a string.")
    if "offset" in args and (isinstance(args["offset"], bool) or not isinstance(args["offset"], int)):
        return failure("bad_offset", "offset must be an integer.")
    if "limit" in args and (isinstance(args["limit"], bool) or not isinstance(args["limit"], int)):
        return failure("bad_limit", "limit must be an integer.")
    return None


def _read(args: dict) -> dict:
    rejected = _reject(args)
    if rejected is not None:
        return rejected
    offset = args.get("offset", 0)
    limit = args.get("limit", store.DEFAULT_READ)
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        return failure("bad_offset", "offset must be an integer from 0.")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > store.MAX_READ:
        return failure("bad_limit", "limit must be an integer from 1 through 32000.")
    root = store.active_root()
    if root is None:
        return failure("path_refused", "The log directory is not available.")
    try:
        chunk, size = store.read_bytes(root, args["path"], offset, limit)
    except store.StoreError as exc:
        messages = {
            "path_refused": "That path is outside the saved logs.",
            "not_found": "No saved log has that path.",
            "bad_offset": "offset is past the end of the log.",
            "bad_limit": "limit must be an integer from 1 through 32000.",
        }
        return failure(exc.kind, messages.get(exc.kind, "The log could not be read."))
    text = chunk.decode("utf-8", errors="replace")
    return success(path=args["path"], offset=offset, limit=limit, size=size, text=text)


def handle_fail_full(args: dict | None = None, **_kwargs: Any) -> str:
    try:
        if not isinstance(args, dict):
            payload = failure("bad_argument", "Arguments must be an object.")
        else:
            payload = _read(dict(args))
    except Exception:
        payload = failure("internal", "The tool failed before it finished.")
    return _dump(payload)
