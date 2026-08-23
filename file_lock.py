"""Minimal cross-platform inter-process file locking."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator


def _lock_windows(lock_file: BinaryIO) -> None:
    import msvcrt

    lock_file.seek(0)
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)


def _unlock_windows(lock_file: BinaryIO) -> None:
    import msvcrt

    lock_file.seek(0)
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def _lock_posix(lock_file: BinaryIO) -> None:
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _unlock_posix(lock_file: BinaryIO) -> None:
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def exclusive_file_lock(target_path: str | Path) -> Iterator[None]:
    """Hold an exclusive lock associated with target_path until the block exits."""
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(f".{target.name}.lock")

    with lock_path.open("a+b") as lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()

        if os.name == "nt":
            _lock_windows(lock_file)
        else:
            _lock_posix(lock_file)
        try:
            yield
        finally:
            if os.name == "nt":
                _unlock_windows(lock_file)
            else:
                _unlock_posix(lock_file)
