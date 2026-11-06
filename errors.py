"""Tool results. A failure names its kind and the next step."""

from __future__ import annotations

NEXT = {
    "bad_argument": "Fix the named field and call again. Nothing was written.",
    "path_refused": "Pass the path printed in the short block. Nothing was written.",
    "not_found": "That log is not in this profile. Nothing was written.",
    "bad_offset": "Pass an offset from 0 through the file size. Nothing was written.",
    "bad_limit": "Pass a limit from 1 through 32000. Nothing was written.",
    "internal": "Retry once. If it repeats, say the tool failed.",
}


def failure(kind: str, message: str) -> dict:
    return {
        "ok": False,
        "error_type": kind,
        "error": message,
        "next_step": NEXT[kind],
    }


def success(**payload: object) -> dict:
    body: dict = {"ok": True}
    body.update(payload)
    return body
