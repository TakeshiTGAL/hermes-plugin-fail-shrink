"""Save one log under the plugin data directory and read it back."""

from __future__ import annotations

try:
    import fcntl
except ImportError:
    fcntl = None
import os
import re
import secrets
import stat
import time
from pathlib import Path

from . import runtime
from .safe_write import WriteRefused, directory_is_real, write_bytes

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILES = 40
MAX_LINES = 20_000
MAX_READ = 32_000
DEFAULT_READ = 8_000
_NAME = re.compile(r"^[0-9]{16,}-[0-9a-f]{16}\.log$")
_EXCL_LOCK = ".lock.excl"


def _directory_flags() -> int | None:
    """Flags for a no-follow directory fd. None when this host has no such open."""
    directory = getattr(os, "O_DIRECTORY", None)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if directory is None or nofollow is None:
        return None
    flags = os.O_RDONLY | directory | nofollow
    cloexec = getattr(os, "O_CLOEXEC", None)
    if cloexec is not None:
        flags |= cloexec
    return flags


_DIR_FLAGS = _directory_flags()


class StoreError(Exception):
    def __init__(self, kind: str):
        self.kind = kind
        super().__init__(kind)


def line_count(text: str) -> int:
    if text == "":
        return 0
    newlines = text.count("\n")
    if text.endswith("\n"):
        return newlines
    return newlines + 1


def _usable_dir(root: Path) -> Path | None:
    """Use the real directory when a parent is a symlink. Refuse a symlink at the leaf."""
    try:
        info = os.lstat(root)
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        return None
    physical = Path(os.path.realpath(root))
    try:
        physical_info = os.lstat(physical)
    except OSError:
        return None
    if stat.S_ISLNK(physical_info.st_mode) or not stat.S_ISDIR(physical_info.st_mode):
        return None
    if (physical_info.st_ino, physical_info.st_dev) != (info.st_ino, info.st_dev):
        return None
    return physical


def active_root() -> Path | None:
    if runtime.ROOT_OVERRIDE is not None:
        return Path(runtime.ROOT_OVERRIDE)
    try:
        from plugins.plugin_storage import plugin_data_dir
    except Exception:
        return None
    try:
        return plugin_data_dir("fail-shrink")
    except Exception:
        return None


def _open_root(root: Path):
    if _DIR_FLAGS is None:
        raise OSError("directory fd is unavailable")
    directory_is_real(root)
    fd = os.open(root, _DIR_FLAGS)
    return fd


def _lock_flags(extra: int = 0) -> int:
    flags = os.O_RDWR | extra
    cloexec = getattr(os, "O_CLOEXEC", None)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if cloexec is not None:
        flags |= cloexec
    if nofollow is not None:
        flags |= nofollow
    return flags


def _acquire_lock(root_fd: int) -> tuple[int, bool]:
    """Lock the directory. The bool is true when the caller must unlink the excl file."""
    if fcntl is not None:
        fd = os.open(".lock", _lock_flags(os.O_CREAT), 0o600, dir_fd=root_fd)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd, False
    excl = _lock_flags(os.O_CREAT | os.O_EXCL)
    try:
        fd = os.open(_EXCL_LOCK, excl, 0o600, dir_fd=root_fd)
        return fd, True
    except FileExistsError:
        info = os.lstat(_EXCL_LOCK, dir_fd=root_fd)
        if time.time() - info.st_mtime < 60 or not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise OSError("lock busy")
        os.unlink(_EXCL_LOCK, dir_fd=root_fd)
        fd = os.open(_EXCL_LOCK, excl, 0o600, dir_fd=root_fd)
        return fd, True


def save_text(root: Path, text: str) -> Path | None:
    """Write the text as one new log. Return its path, or None when it does not fit."""
    data = text.encode("utf-8")
    if len(data) > MAX_FILE_BYTES or line_count(text) > MAX_LINES:
        return None
    resolved = _usable_dir(Path(root))
    if resolved is None:
        return None
    root = resolved
    try:
        root_fd = _open_root(root)
    except (WriteRefused, OSError):
        return None
    lock_fd = -1
    drop_excl = False
    try:
        try:
            lock_fd, drop_excl = _acquire_lock(root_fd)
        except OSError:
            return None
        kept: list[tuple[float, str, int]] = []
        for name in os.listdir(root_fd):
            if not _NAME.fullmatch(name):
                continue
            try:
                info = os.lstat(name, dir_fd=root_fd)
            except OSError:
                continue
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                continue
            if info.st_nlink != 1:
                continue
            kept.append((info.st_mtime, name, info.st_size))
        kept.sort()
        total = sum(size for _, _, size in kept)
        while kept and (len(kept) >= MAX_FILES or total + len(data) > MAX_TOTAL_BYTES):
            _, name, size = kept.pop(0)
            try:
                os.unlink(name, dir_fd=root_fd)
            except OSError:
                return None
            total -= size
        if len(kept) >= MAX_FILES or total + len(data) > MAX_TOTAL_BYTES:
            return None
        name = f"{time.time_ns()}-{secrets.token_hex(8)}.log"
        try:
            write_bytes(root, name, data, create=True, exclusive=True)
        except (WriteRefused, OSError):
            return None
        return root / name
    finally:
        if lock_fd >= 0:
            try:
                os.close(lock_fd)
            except OSError:
                pass
        if drop_excl:
            try:
                os.unlink(_EXCL_LOCK, dir_fd=root_fd)
            except OSError:
                pass
        try:
            os.close(root_fd)
        except OSError:
            pass


def _reject_path(raw: str) -> str:
    if not isinstance(raw, str) or raw == "" or "\x00" in raw or len(raw) > 4096:
        raise StoreError("path_refused")
    if any(part in ("", ".", "..") for part in Path(raw).parts):
        raise StoreError("path_refused")
    candidate = Path(raw)
    if not candidate.is_absolute():
        if len(candidate.parts) != 1 or not _NAME.fullmatch(candidate.name):
            raise StoreError("path_refused")
        return candidate.name
    if not _NAME.fullmatch(candidate.name):
        raise StoreError("path_refused")
    return candidate.name


def read_bytes(root: Path, raw: str, offset: int, limit: int) -> tuple[bytes, int]:
    """Return a slice and the file size. The file is opened with O_NOFOLLOW."""
    name = _reject_path(raw)
    resolved = _usable_dir(Path(root))
    if resolved is None:
        raise StoreError("path_refused")
    root = resolved
    try:
        root_fd = _open_root(root)
    except (WriteRefused, OSError) as exc:
        raise StoreError("path_refused") from exc
    try:
        if Path(raw).is_absolute():
            parent = Path(raw).parent
            try:
                parent_info = os.lstat(parent)
                root_info = os.fstat(root_fd)
            except OSError as exc:
                raise StoreError("path_refused") from exc
            if stat.S_ISLNK(parent_info.st_mode):
                raise StoreError("path_refused")
            if parent_info.st_ino != root_info.st_ino or parent_info.st_dev != root_info.st_dev:
                raise StoreError("path_refused")
        try:
            info = os.lstat(name, dir_fd=root_fd)
        except FileNotFoundError as exc:
            raise StoreError("not_found") from exc
        except OSError as exc:
            raise StoreError("path_refused") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise StoreError("path_refused")
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root_fd)
        except OSError as exc:
            raise StoreError("path_refused") from exc
        try:
            size = os.fstat(fd).st_size
            if offset < 0 or offset > size:
                raise StoreError("bad_offset")
            if offset == size:
                return b"", size
            os.lseek(fd, offset, os.SEEK_SET)
            chunk = os.read(fd, limit)
            return chunk, size
        finally:
            os.close(fd)
    finally:
        os.close(root_fd)


def remove_log(path: Path) -> None:
    """Drop a log this process just wrote, when the short block is not shorter."""
    name = path.name
    if not _NAME.fullmatch(name):
        return
    parent = _usable_dir(path.parent)
    if parent is None:
        return
    try:
        root_fd = _open_root(parent)
    except (WriteRefused, OSError):
        return
    try:
        info = os.lstat(name, dir_fd=root_fd)
        if stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode) and info.st_nlink == 1:
            os.unlink(name, dir_fd=root_fd)
    except OSError:
        return
    finally:
        os.close(root_fd)
