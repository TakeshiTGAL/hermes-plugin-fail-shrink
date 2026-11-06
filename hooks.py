"""Public hooks. pre_llm_call only records a flag and returns None."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from . import runtime, shrink

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_PHRASES = (
    "\u5168\u90e8\u898b\u305b\u3066",
    "\u5168\u6587\u3092\u898b\u305b\u3066",
    "\u5168\u90e8\u51fa\u3057\u3066",
    "show me everything",
    "show everything",
    "show the full output",
    "show full output",
    "show the full log",
    "show the whole log",
    "do not shrink",
    "don't shrink",
)


def message_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        chunks = []
        for part in message:
            if isinstance(part, str):
                chunks.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks)
    return ""


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Match the phrase with any whitespace, including none, between characters."""
    return re.compile(r"\s*".join(re.escape(ch) for ch in phrase.casefold()))


_PHRASE_RES = tuple(_phrase_pattern(phrase) for phrase in _PHRASES)


def wants_full(text: str) -> bool:
    folded = _COMMENT.sub(" ", text)
    folded = unicodedata.normalize("NFKC", folded).casefold().replace("\u3000", " ")
    return any(pattern.search(folded) for pattern in _PHRASE_RES)


def _remember(session_id: str, turn_id: str, user_message: Any) -> None:
    key = (str(session_id or ""), str(turn_id or ""))
    runtime.SHOW_FULL[key] = wants_full(message_text(user_message))
    while len(runtime.SHOW_FULL) > 100:
        runtime.SHOW_FULL.pop(next(iter(runtime.SHOW_FULL)))


def on_pre_llm_call(
    user_message: Any = None,
    session_id: str = "",
    turn_id: str = "",
    **_ignored: Any,
) -> None:
    try:
        _remember(session_id, turn_id, user_message)
    except Exception:
        return None
    return None


def _json_shape(ctx: Any) -> bool:
    if ctx is None:
        return False
    try:
        return ctx.get_config("json_shape", False) is True
    except Exception:
        return False


def on_transform(
    ctx: Any = None,
    tool_name: str = "",
    args: Any = None,
    result: Any = None,
    session_id: str = "",
    turn_id: str = "",
    **_ignored: Any,
) -> str | None:
    try:
        key = (str(session_id or ""), str(turn_id or ""))
        if runtime.SHOW_FULL.get(key):
            return None
        root = shrink.store.active_root()
        if root is None:
            return None
        return shrink.transform(
            tool_name,
            args,
            result,
            root=root,
            json_shape=_json_shape(ctx),
        )
    except Exception:
        return None
