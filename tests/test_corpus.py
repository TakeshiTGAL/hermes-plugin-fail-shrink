"""Every captured runner log in tests/corpus matches the answer beside it.

The answer is shrink or unchanged for the last 2000 characters, the tail
Hermes keeps. Shrink names the place on that tool's own summary line.
"""

from __future__ import annotations

import json
from pathlib import Path

from support import ROOT, parse, shrink

CORPUS = ROOT / "tests" / "corpus"
WINDOW = 2000
CORPUS_COUNT = 91

DIALECTS = ("pytest", "jest", "vitest", "cargo", "go", "tsc", "ruff", "eslint")

# Axes the corpus has to cover. A renamed or dropped sample fails here.
REQUIRED = {
    "pytest-tb-auto-q",
    "pytest-tb-long-q",
    "pytest-tb-short-q",
    "pytest-tb-line-q",
    "pytest-tb-native-q",
    "pytest-tb-no-q",
    "pytest-tb-auto-v",
    "pytest-tb-line-v",
    "pytest-tb-short-x",
    "pytest-collect-syntax",
    "pytest-collect-import",
    "pytest-import-in-test",
    "pytest-internal",
    "pytest-fixture",
    "pytest-xfail",
    "pytest-xpass-strict",
    "pytest-print-fileline",
    "pytest-print-heading",
    "pytest-print-footer",
    "pytest-footer-only",
    "pytest-failures-abspath",
    "pytest-mid-heading",
    "pytest-mid-traceback",
    "pytest-mid-lineno",
    "tsc-short-false",
    "tsc-short-true",
    "tsc-long",
    "tsc-zero",
    "ruff-short",
    "ruff-long",
    "ruff-zero",
    "eslint-short",
    "eslint-long",
    "eslint-zero",
    "jest-short",
    "jest-long",
    "jest-zero",
    "vitest-short",
    "vitest-long",
    "vitest-zero",
    "cargo-short",
    "cargo-long",
    "cargo-zero",
    "go-short",
    "go-long",
    "go-zero",
}
for _dialect in DIALECTS:
    for _edge in ("mid-heading", "mid-traceback", "mid-lineno"):
        REQUIRED.add(f"{_dialect}-{_edge}")


def _samples() -> list[tuple[dict, str]]:
    rows = []
    for path in sorted(CORPUS.glob("*.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        text = (CORPUS / f"{meta['id']}.log").read_text(encoding="utf-8")
        rows.append((meta, text))
    return rows


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _window(text: str) -> str:
    if len(text) <= WINDOW:
        return text
    return text[-WINDOW:]


def _product(meta: dict, text: str):
    window = _window(text)
    parsed = parse.classify(window, meta["command"])
    if parsed is None:
        return None
    dialect, findings = parsed
    block = shrink._render(
        dialect,
        meta["exit_code"],
        findings,
        "log.txt",
        0,
        None,
    )
    assert "outside this tail" not in block
    got = []
    for item in findings:
        got.append({
            "file": _basename(item.file) if item.file else "",
            "line": item.line or None,
            "name": item.name,
            "summary": item.point,
        })
    return dialect, got


def _same(want: dict, got: dict) -> bool:
    if _basename(want["file"] or "") != got["file"]:
        return False
    if want["line"] != got["line"]:
        return False
    if want["name"] != got["name"]:
        return False
    summary = want["summary"]
    point = got["summary"]
    if summary and summary not in point and point not in summary:
        return False
    return True


def test_corpus_covers_the_requested_axes():
    rows = _samples()
    ids = {meta["id"] for meta, _text in rows}
    assert REQUIRED <= ids
    assert len(rows) == len(ids) == CORPUS_COUNT
    by_dialect: dict[str, list[dict]] = {name: [] for name in DIALECTS}
    for meta, text in rows:
        assert "/" not in meta["id"]
        assert (CORPUS / f"{meta['id']}.json").is_file()
        assert (CORPUS / f"{meta['id']}.log").is_file()
        assert len(text) == meta["chars"]
        assert meta["dialect"] in DIALECTS
        by_dialect[meta["dialect"]].append(meta)
    for name, group in by_dialect.items():
        edges = {meta["window_boundary"] for meta in group}
        assert {"mid-heading", "mid-traceback", "mid-lineno"} <= edges, name
    shapes = {meta["shape"] for meta, _text in rows}
    assert any("tb=auto" in shape for shape in shapes)
    assert any("tb=long" in shape for shape in shapes)
    assert any("tb=short" in shape for shape in shapes)
    assert any("tb=line" in shape for shape in shapes)
    assert any("tb=native" in shape for shape in shapes)
    assert any("tb=no" in shape for shape in shapes)
    commands = [meta["command"] for meta, _text in rows]
    assert any(" -v " in command or command.endswith(" -v") for command in commands)
    assert any(" -x " in command or command.endswith(" -x") for command in commands)


def test_every_corpus_sample_matches_its_answer():
    shrinks = 0
    for meta, text in _samples():
        answer = meta["answer"]
        assert answer["verdict"] in {"shrink", "unchanged"}, meta["id"]
        got = _product(meta, text)
        if answer["verdict"] == "unchanged":
            assert got is None, meta["id"]
            assert answer["items"] == []
            continue
        shrinks += 1
        assert got is not None, meta["id"]
        dialect, items = got
        assert dialect == meta["dialect"], meta["id"]
        assert len(items) == len(answer["items"]), meta["id"]
        for want, item in zip(answer["items"], items):
            assert _same(want, item), (meta["id"], want, item)
            assert item["line"] != 999, meta["id"]
            assert "/tmp/old" not in item["file"], meta["id"]
            assert "helper.py" not in item["file"] or meta["dialect"] != "pytest", meta["id"]
    assert shrinks > 0
