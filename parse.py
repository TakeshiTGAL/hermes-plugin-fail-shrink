"""Classify one captured runner log from that tool's own summary lines.

A shrink is allowed only when a summary line is complete in the text and the
cited place is on that line. Pytest's place is the node id on a ``FAILED`` or
``ERROR`` row in the last ``short test summary info`` section. The stats line
closes that section. It does not add a line number. Jest, Vitest, cargo, and
Go contribute the file or the name written on their summary rows. tsc, Ruff,
and ESLint contribute the file and line on a complete diagnostic row. A path
printed in captured output is not a summary row. A tail with no summary row
classifies as nothing. When pytest cuts the message off a wide summary row,
the point and the offset come from the E line in that test's failure
section. A short row with no message keeps an empty point.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_SUMMARY = re.compile(r"^={5,} short test summary info =+\s*$", re.M)
_EQ_FOOTER = re.compile(r"^={5,} (?!short test summary info\b).+ =+\s*$")
_INTERRUPTED = re.compile(r"^!{5,} .+ !+\s*$")
_QUIET_STATS = re.compile(
    r"^\d+ (?:failed|passed|error|errors|skipped|xfailed|xpassed|warnings|warning|deselected|rerun)\b"
    r".* in \d+(?:\.\d+)?s\s*$"
)
_JEST_FAIL = re.compile(
    r"^FAIL\s+(.+?)(?:\s+\(\d+(?:\.\d+)?\s*(?:ms|s)\))?\s*$",
    re.M,
)
_JEST_BULLET = re.compile(r"^  ●\s+(.+?)\s*$", re.M)
_JEST_SUITES = re.compile(r"^Test Suites:.*\bfailed\b.*$", re.M)
_VITEST_BANNER = re.compile(r"^[⎯─-]{5,} Failed Tests \d+ [⎯─-]{5,}\s*$", re.M)
_VITEST_FAIL = re.compile(r"^ FAIL\s+(.+)$", re.M)
_VITEST_FILES = re.compile(r"^ Test Files\b.*\bfailed\b", re.M)
_CARGO_RESULT = re.compile(r"^test result: FAILED\b.*$", re.M)
_CARGO_FAILURES = re.compile(r"^failures:\s*$", re.M)
_GO_HEADER = re.compile(r"^--- FAIL: (\S+)", re.M)
_GO_PACKAGE = re.compile(r"^FAIL\t.+$", re.M)
_HEADING = re.compile(r"^_+\s+(.+?)\s+_+\s*$")
_CAPTURE = re.compile(r"^-{5,} .+ -{5,}\s*$")
_E_LINE = re.compile(r"^E\s+\S")
_E_BLANK = re.compile(r"^E\s*$")
_SECTION_BANNER = re.compile(r"^={5,} (?:FAILURES|ERRORS|XFAILURES) =+\s*$", re.M)
_CRASH_LINE = re.compile(r"^.+:\d+:")
# Pytest drops the summary message when the row is wider than the terminal
# minus " - " and "...". The narrowest width pytest keeps is 80 columns.
_WIDE_ROW = 75


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    name: str
    point: str
    anchor: str
    rerun_file: str = ""
    block_rerun: bool = False
    anchor_from: int = 0


def _clip(text: str, limit: int = 180) -> str:
    one = " ".join(text.split())
    if len(one) <= limit:
        return one
    return one[: limit - 3] + "..."


def _parent_walk(path: str) -> bool:
    return any(part == ".." for part in path.replace("\\", "/").split("/"))


def _node_file(node: str) -> tuple[str, str]:
    if "::" in node:
        return node.split("::", 1)[0], node.split("::")[-1]
    return node, ""


def _split_failed(line: str) -> tuple[str, str] | None:
    """Node id, then the message. `` - `` inside brackets stays in the node id."""
    if line.startswith("FAILED "):
        rest = line[len("FAILED "):].strip()
    elif line.startswith("ERROR "):
        rest = line[len("ERROR "):].strip()
    else:
        return None
    depth = 0
    index = 0
    while index < len(rest):
        ch = rest[index]
        if ch == "[":
            depth += 1
        elif ch == "]" and depth:
            depth -= 1
        elif depth == 0 and rest.startswith(" - ", index):
            node = rest[:index].strip()
            if node:
                return node, rest[index + 3:].strip()
        index += 1
    if rest:
        return rest, ""
    return None


def _lines_with_start(text: str) -> list[tuple[int, str]]:
    rows = []
    index = 0
    for raw in text.splitlines(keepends=True):
        rows.append((index, raw.rstrip("\r\n")))
        index += len(raw)
    return rows


def _stats_line(line: str) -> bool:
    stripped = line.strip()
    if _INTERRUPTED.match(stripped) or _QUIET_STATS.match(stripped):
        return True
    return _EQ_FOOTER.match(stripped) is not None


def _finding(file_name: str, line: int, name: str, point: str, anchor: str, anchor_from: int) -> Finding:
    return Finding(
        file_name,
        line,
        name,
        _clip(point) if point else "",
        anchor,
        block_rerun=_parent_walk(file_name),
        anchor_from=anchor_from,
    )


def _pytest_rows(text: str) -> list[tuple[int, str]]:
    """Complete FAILED and ERROR rows from the last summary section."""
    banners = list(_SUMMARY.finditer(text))
    numbered = _lines_with_start(text)
    if banners:
        body_at = banners[-1].end()
        rows = []
        for start, line in numbered:
            if start < body_at:
                continue
            if _stats_line(line):
                break
            rows.append((start, line))
        return rows
    stats_at = None
    for index in range(len(numbered) - 1, -1, -1):
        if _stats_line(numbered[index][1]):
            stats_at = index
            break
    if stats_at is None:
        return []
    chosen: list[tuple[int, str]] = []
    index = stats_at - 1
    while index >= 0 and numbered[index][1].strip() == "":
        index -= 1
    while index >= 0 and (
        numbered[index][1].startswith("FAILED ") or numbered[index][1].startswith("ERROR ")
    ):
        chosen.append(numbered[index])
        index -= 1
    chosen.reverse()
    return chosen


def _cols(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def _heading_name(line: str) -> str | None:
    match = _HEADING.match(line.strip())
    if match is None:
        return None
    name = match.group(1).strip()
    if not re.search(r"[A-Za-z0-9]", name):
        return None
    return name


def _node_heads(node: str) -> set[str]:
    file_name, name = _node_file(node)
    heads = set()
    if "::" in node:
        heads.add(node.split("::", 1)[1].replace("::", "."))
    if name:
        heads.add(name)
        heads.add(f"ERROR at setup of {name}")
        heads.add(f"ERROR at teardown of {name}")
    if file_name:
        base = file_name.replace("\\", "/").rsplit("/", 1)[-1]
        heads.add(f"ERROR collecting {base}")
        if base != file_name:
            heads.add(f"ERROR collecting {file_name}")
    return {head for head in heads if head}


def _body_before(text: str, first_row_at: int) -> tuple[int, str] | None:
    """FAILURES or ERRORS text that belongs to the summary at first_row_at."""
    banner = None
    for match in _SUMMARY.finditer(text):
        if match.end() <= first_row_at:
            banner = match
        else:
            break
    if banner is not None:
        region_end = banner.start()
        prev = 0
        for match in _SUMMARY.finditer(text):
            if match.start() < banner.start():
                prev = match.end()
            else:
                break
    else:
        region_end = first_row_at
        prev = 0
    chunk = text[prev:region_end]
    match = _SECTION_BANNER.search(chunk)
    if match is None:
        return None
    base = prev + match.end()
    return base, text[base:region_end]


def _split_sections(body: str, base: int) -> list[tuple[str, list[tuple[int, str]]]]:
    sections: list[tuple[str, list[tuple[int, str]]]] = []
    heading = ""
    chunk: list[tuple[int, str]] = []
    started = False
    for rel, line in _lines_with_start(body):
        name = _heading_name(line)
        if name is not None:
            if started:
                sections.append((heading, chunk))
            heading = name
            chunk = []
            started = True
            continue
        if _SECTION_BANNER.match(line.strip()):
            if started:
                sections.append((heading, chunk))
            heading = ""
            chunk = []
            started = True
            continue
        chunk.append((base + rel, line))
        started = True
    if started:
        sections.append((heading, chunk))
    return sections


def _pre_capture(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    kept = []
    for item in lines:
        if _CAPTURE.match(item[1].strip()):
            break
        kept.append(item)
    return kept


def _message_from_block(block: list[tuple[int, str]]) -> tuple[int, str, str] | None:
    texts = []
    for at, line in block:
        text = re.sub(r"^E\s+", "", line).strip()
        if text:
            texts.append((at, line.rstrip(), text))
    if not texts:
        return None
    if texts[0][2].startswith("File "):
        for at, raw, text in reversed(texts):
            if "Error" in text or "Exception" in text:
                return at, raw, text
    at, raw, text = texts[0]
    return at, raw, text


def _e_row(line: str, open_block: bool) -> bool:
    """An E row. A blank E row continues the open block, so a diff stays with it."""
    if _E_LINE.match(line):
        return True
    return open_block and _E_BLANK.match(line) is not None


def _last_e_message(lines: list[tuple[int, str]]) -> tuple[int, str, str] | None:
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for item in lines:
        if _e_row(item[1], bool(current)):
            current.append(item)
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    if not blocks:
        return None
    return _message_from_block(blocks[-1])


def _line_style_messages(lines: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """E blocks in a --tb=line region. Capture text between them is skipped."""
    found: list[list[tuple[int, str]]] = []
    buf: list[tuple[int, str]] = []
    in_capture = False
    for at, line in lines:
        stripped = line.strip()
        if _CAPTURE.match(stripped):
            if buf:
                found.append(buf)
                buf = []
            in_capture = True
            continue
        if in_capture:
            if _CRASH_LINE.match(stripped):
                in_capture = False
            continue
        if _e_row(line, bool(buf)):
            buf.append((at, line))
            continue
        if buf and _CRASH_LINE.match(stripped):
            found.append(buf)
            buf = []
    if buf:
        found.append(buf)
    messages = []
    for block in found:
        message = _last_e_message(block)
        if message is not None:
            messages.append(message)
    return messages


def _upgrade(summary_line: str, summary_message: str, recovered: str) -> str | None:
    """Fuller message, or None when the summary row already says enough."""
    if not recovered or recovered == summary_message:
        return None
    if summary_message.endswith("...") and len(recovered) > len(summary_message):
        prefix = summary_message[:-3]
        if prefix and recovered.startswith(prefix):
            return recovered
        return None
    if summary_message:
        return None
    if _cols(summary_line) >= _WIDE_ROW:
        return recovered
    return None


def _cut_points(text: str, raw: list[tuple]) -> list[tuple[str, str, int]]:
    """Point, anchor, and anchor index for each summary row."""
    defaults = [(item[3], item[1], item[0]) for item in raw]
    body = _body_before(text, raw[0][0])
    if body is None:
        return defaults
    base, chunk = body
    sections = _split_sections(chunk, base)
    headed: dict[int, int] = {}
    used: set[int] = set()
    for index in range(len(raw) - 1, -1, -1):
        heads = _node_heads(raw[index][2])
        match = None
        for sec_index, (heading, _lines) in enumerate(sections):
            if heading and heading in heads and sec_index not in used:
                match = sec_index
        if match is not None:
            headed[index] = match
            used.add(match)
    bare = []
    for heading, lines in sections:
        if heading:
            continue
        bare.extend(_line_style_messages(lines))
    bare_at = 0
    points = []
    for index, item in enumerate(raw):
        start, stripped, _node, message, _file_name, _name = item
        recovered = None
        if index in headed:
            recovered = _last_e_message(_pre_capture(sections[headed[index]][1]))
        elif bare_at < len(bare):
            recovered = bare[bare_at]
            bare_at += 1
        if recovered is None:
            points.append((message, stripped, start))
            continue
        at, raw_line, fuller = recovered
        upgraded = _upgrade(stripped, message, fuller)
        if upgraded is None:
            points.append((message, stripped, start))
        else:
            points.append((upgraded, raw_line, at))
    return points


def parse_pytest(text: str, command: str = "") -> list[Finding]:
    del command
    raw = []
    for start, line in _pytest_rows(text):
        stripped = line.strip()
        split = _split_failed(stripped)
        if split is None:
            continue
        node, message = split
        file_name, name = _node_file(node)
        if not file_name and not name:
            continue
        raw.append((start, stripped, node, message, file_name, name))
    if not raw:
        return []
    findings = []
    for item, extra in zip(raw, _cut_points(text, raw)):
        _start, _stripped, _node, _message, file_name, name = item
        point, anchor, anchor_from = extra
        findings.append(_finding(file_name, 0, name, point, anchor, anchor_from))
    return findings


def _jest_region(text: str) -> str | None:
    summaries = list(_JEST_SUITES.finditer(text))
    if not summaries:
        return None
    start = summaries[-2].end() if len(summaries) >= 2 else 0
    return text[start:summaries[-1].start()]


def parse_jest(text: str) -> list[Finding]:
    region = _jest_region(text)
    if region is None:
        return []
    fails = list(_JEST_FAIL.finditer(region))
    if not fails:
        return []
    findings = []
    for index, fail in enumerate(fails):
        end = fails[index + 1].start() if index + 1 < len(fails) else len(region)
        section = region[fail.end():end]
        file_name = fail.group(1).strip()
        if file_name.startswith("./"):
            file_name = file_name[2:]
        bullets = list(_JEST_BULLET.finditer(section))
        names = [bullet.group(1).strip() for bullet in bullets] or [""]
        anchor = fail.group(0).strip()
        for name in names:
            findings.append(_finding(file_name, 0, name, "", anchor, 0))
    return findings


def _vitest_region(text: str) -> str | None:
    banners = list(_VITEST_BANNER.finditer(text))
    if banners:
        return text[banners[-1].end():]
    files = list(_VITEST_FILES.finditer(text))
    if not files:
        return None
    return text[:files[-1].start()]


def parse_vitest(text: str) -> list[Finding]:
    if "Test Suites:" in text:
        return []
    region = _vitest_region(text)
    if region is None:
        return []
    heads = list(_VITEST_FAIL.finditer(region))
    if not heads:
        return []
    findings = []
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else len(region)
        section = region[head.end():end]
        title = head.group(1).strip()
        parts = [part.strip() for part in title.split(" > ")]
        file_name = parts[0]
        name = parts[-1] if len(parts) > 1 else ""
        point_match = re.search(r"^(AssertionError:.*)$", section, re.M)
        point = point_match.group(1) if point_match else ""
        findings.append(_finding(file_name, 0, name, point, head.group(0).strip(), 0))
    return findings


def parse_cargo(text: str) -> list[Finding]:
    results = list(_CARGO_RESULT.finditer(text))
    if not results:
        return []
    start = results[-2].end() if len(results) >= 2 else 0
    region = text[start:results[-1].start()]
    blocks = list(_CARGO_FAILURES.finditer(region))
    if not blocks:
        return []
    names = re.findall(r"^    (\S+)\s*$", region[blocks[-1].end():], re.M)
    return [_finding("", 0, name, "", f"    {name}", 0) for name in names]


def parse_go(text: str) -> list[Finding]:
    packages = list(_GO_PACKAGE.finditer(text))
    if not packages or _GO_HEADER.search(text) is None:
        return []
    start = packages[-2].end() if len(packages) >= 2 else 0
    region = text[start:packages[-1].start()]
    findings = []
    for line in region.splitlines():
        head = _GO_HEADER.match(line)
        if head is None:
            continue
        findings.append(_finding("", 0, head.group(1), "", line.strip(), 0))
    return findings


def parse_tsc(text: str) -> list[Finding]:
    findings = []
    for match in re.finditer(r"^(.+?)\((\d+),(\d+)\): error (TS\d+): (.+)$", text, re.M):
        findings.append(_finding(
            match.group(1), int(match.group(2)), match.group(4), match.group(5), match.group(0), match.start(),
        ))
    if findings:
        return findings
    for match in re.finditer(r"^(.+?):(\d+):\d+ - error (TS\d+): (.+)$", text, re.M):
        findings.append(_finding(
            match.group(1), int(match.group(2)), match.group(3), match.group(4), match.group(0), match.start(),
        ))
    return findings


def parse_ruff(text: str) -> list[Finding]:
    """A complete ``--> file:line:col`` row is Ruff's own diagnostic."""
    code_line = re.compile(r"^([A-Z]\d{3,4})(?:\s+\[\*])?\s+(.+)$")
    arrow_line = re.compile(r"^\s*-->\s+(.+):(\d+):\d+\s*$")
    lines = text.splitlines()
    findings = []
    for index, line in enumerate(lines):
        arrow = arrow_line.match(line)
        if arrow is None:
            continue
        name = ""
        summary = ""
        if index:
            head = code_line.match(lines[index - 1])
            if head:
                name = head.group(1)
                summary = head.group(2)
        findings.append(_finding(arrow.group(1), int(arrow.group(2)), name, summary, line.strip(), 0))
    return findings


def parse_eslint(text: str) -> list[Finding]:
    if not re.search(r"\d+ problems?", text):
        return []
    file_name = ""
    findings = []
    for line in text.splitlines():
        err = re.match(r"^\s*(\d+):(\d+)\s+error\s+(.+?)\s{2,}(\S+)\s*$", line)
        if err:
            if line[:1].isdigit():
                continue
            findings.append(_finding(
                file_name, int(err.group(1)), err.group(4), err.group(3), line.strip(), 0,
            ))
            continue
        stripped = line.strip()
        if stripped.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
            file_name = stripped
    return findings


_PARSERS = (
    ("pytest", parse_pytest),
    ("jest", parse_jest),
    ("vitest", parse_vitest),
    ("cargo", parse_cargo),
    ("go", parse_go),
    ("tsc", parse_tsc),
    ("ruff", parse_ruff),
    ("eslint", parse_eslint),
)


def classify(text: str, command: str = "") -> tuple[str, list[Finding]] | None:
    plain = _ANSI.sub("", text)
    hits = []
    for name, parser in _PARSERS:
        found = parser(plain, command) if name == "pytest" else parser(plain)
        if found:
            hits.append((name, found))
    if len(hits) != 1:
        return None
    return hits[0]


def byte_offset(text: str, anchor: str, start: int = 0) -> int:
    if not anchor:
        return 0
    index = text.find(anchor, start)
    if index < 0 and start:
        index = text.find(anchor)
    if index < 0:
        plain = _ANSI.sub("", text)
        index = plain.find(anchor, start)
        if index < 0 and start:
            index = plain.find(anchor)
        if index < 0:
            return 0
        return len(plain[:index].encode("utf-8"))
    return len(text[:index].encode("utf-8"))
