"""Decide whether a command line can become one rerun line."""

from __future__ import annotations

import re
import shlex

_PYTEST = {"pytest", "py.test"}
_NODE_TOOLS = {"jest", "vitest", "tsc", "eslint", "ruff"}


def has_shell_composition(command: str) -> bool:
    """True when the line is a pipeline, a redirect, a substitution, or an open quote."""
    if any(ch in command for ch in "\n\r\x00"):
        return True
    i = 0
    n = len(command)
    quote = ""
    while i < n:
        ch = command[i]
        if quote == "'":
            if ch == "'":
                quote = ""
            i += 1
            continue
        if quote == '"':
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                quote = ""
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            i += 1
            continue
        if ch == "`" or command.startswith("$(", i):
            return True
        if command.startswith("&&", i) or command.startswith("||", i):
            return True
        if command.startswith(">>", i) or command.startswith("<<", i):
            return True
        if command.startswith(">&", i) or command.startswith("&>", i):
            return True
        if ch in "|&;<>#*?$":
            return True
        i += 1
    return quote != ""


def simple_argv(command: str) -> list[str] | None:
    if not command or has_shell_composition(command):
        return None
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return None
    if not argv or any(part == "" for part in argv):
        return None
    return argv


def shell_join(argv: list[str]) -> str | None:
    if any("\n" in part or "\x00" in part or part == "" for part in argv):
        return None
    try:
        line = shlex.join(argv)
        if shlex.split(line) != argv:
            return None
    except ValueError:
        return None
    return line


def _base(token: str) -> str:
    return token.replace("\\", "/").rsplit("/", 1)[-1]


def _python(token: str) -> bool:
    base = _base(token).casefold()
    return base in {"python", "python2", "python3"} or base.startswith("python3.") or base.startswith("python2.")


def _url(token: str) -> bool:
    """A pasted URL is not an executable. Its last segment can look like a runner."""
    return "://" in token


def runner_kind(argv: list[str] | None) -> str | None:
    if not argv or _url(argv[0]):
        return None
    base = _base(argv[0]).casefold()
    if _python(argv[0]) and len(argv) >= 3 and argv[1] == "-m":
        if _url(argv[2]):
            return None
        if _base(argv[2]).casefold() in _PYTEST:
            return "pytest"
    if base in _PYTEST:
        return "pytest"
    if base == "npx" and len(argv) >= 2:
        if _url(argv[1]):
            return None
        if _base(argv[1]).casefold() in _NODE_TOOLS:
            return _base(argv[1]).casefold()
    if base in _NODE_TOOLS:
        return base
    if base == "cargo" and len(argv) >= 2 and argv[1].casefold() == "test":
        return "cargo"
    if base == "go" and len(argv) >= 2 and argv[1].casefold() == "test":
        return "go"
    return None


def runner_prefix(argv: list[str], kind: str) -> list[str]:
    base = _base(argv[0]).casefold()
    if kind == "pytest" and _python(argv[0]):
        return argv[:3]
    if base == "npx":
        return argv[:2]
    if kind == "cargo":
        return [argv[0], "test"]
    if kind == "go":
        return [argv[0], "test"]
    return [argv[0]]


def _parent_walk(path: str) -> bool:
    return any(part == ".." for part in path.replace("\\", "/").split("/"))


def _rerun_path(item) -> str:
    chosen = getattr(item, "rerun_file", "") or ""
    if chosen:
        return chosen
    return item.file


def _files(findings) -> list[str]:
    files = []
    for item in findings:
        path = _rerun_path(item)
        if path and path not in files:
            files.append(path)
    return files


def _one_file(findings) -> str | None:
    files = _files(findings)
    if len(files) == 1:
        return files[0]
    return None


def _names(findings) -> list[str]:
    names = []
    for item in findings:
        if item.name and item.name not in names:
            names.append(item.name)
    return names


def build_rerun(kind: str, argv: list[str], findings) -> str | None:
    """Build one rerun from the runner that actually ran and the parsed names."""
    if any(getattr(item, "block_rerun", False) for item in findings):
        return None
    if kind == "tsc":
        if runner_kind(argv) != "tsc":
            return None
        return shell_join(argv)
    prefix = runner_prefix(argv, kind)
    names = _names(findings)
    file_name = _one_file(findings)
    if file_name and _parent_walk(file_name):
        return None
    if kind == "pytest":
        if not names or any(re.fullmatch(r"[A-Za-z0-9_\-\[\]]+", name) is None for name in names):
            return None
        files = _files(findings)
        if any(_parent_walk(path) for path in files):
            return None
        built = list(prefix) + files
        built.extend(["-k", " or ".join(names)])
        return shell_join(built)
    if kind in {"jest", "vitest"}:
        if len(names) != 1:
            return None
        name = names[0]
        if re.search(r"[()\[\]{}|+*?^$\\]", name):
            return None
        built = list(prefix)
        if kind == "vitest" and "run" not in built:
            built.append("run")
        if file_name:
            built.append(file_name)
        built.extend(["-t", name])
        return shell_join(built)
    if kind == "cargo":
        if len(names) != 1 or re.fullmatch(r"[A-Za-z0-9_:]+", names[0]) is None:
            return None
        kept = []
        for part in argv[2:]:
            if part == "--":
                break
            if part in {"--offline", "--frozen", "--locked"}:
                kept.append(part)
        return shell_join(list(prefix) + kept + [names[0], "--", "--exact"])
    if kind == "go":
        if len(names) != 1 or re.fullmatch(r"[A-Za-z0-9_]+", names[0]) is None:
            return None
        packages = [part for part in argv[2:] if not part.startswith("-")]
        built = list(prefix) + ["-count=1", "-run", f"^{names[0]}$"]
        if len(packages) == 1 and re.fullmatch(r"[A-Za-z0-9_./\-]+", packages[0]):
            built.append(packages[0])
        return shell_join(built)
    if kind == "ruff":
        built = list(prefix)
        if _base(built[-1]) == "ruff":
            built.append("check")
        if file_name:
            built.append(file_name)
        elif not any(not part.startswith("-") for part in built[1:]):
            return None
        return shell_join(built)
    if kind == "eslint":
        built = list(prefix)
        if file_name:
            built.append(file_name)
        else:
            return None
        return shell_join(built)
    return None
