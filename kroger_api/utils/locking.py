"""
An exclusive lock on a file, shared by the threads of a process and by processes

kroger-api and kroger-mcp processes share token files, and kroger-mcp also
shares its state files. A lock held while a file is read, changed, and saved
keeps two of them from working on it at the same time.
"""
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Dict, Generator, Optional

if os.name == "nt":
    import msvcrt
else:
    import fcntl

logger = logging.getLogger(__name__)

# Seconds to wait for a lock before going on without it. A token refresh
# holds the lock for one token request, which with the default timeout can
# take 30 seconds to connect and 30 more to read.
LOCK_TIMEOUT_SECONDS = 90

# Seconds between attempts to lock a file that another process holds
_POLL_SECONDS = 0.05


class _PathLock:
    """The lock of one file in this process

    The thread lock orders the threads of this process; the operating system
    lock on the open lock file orders the processes. The thread lock is
    reentrant, and only the outermost hold of a thread locks the file, so a
    thread that holds the lock can take it again.
    """

    def __init__(self):
        self.thread_lock = threading.RLock()
        self.depth = 0
        self.fd: Optional[int] = None


_locks: Dict[str, _PathLock] = {}
_locks_guard = threading.Lock()


def _forget_locks():
    # A child process has only the thread that forked it, so locks held by
    # other threads of the parent would never be released in the child
    global _locks, _locks_guard
    _locks, _locks_guard = {}, threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_forget_locks)


@contextmanager
def file_lock(path: str, timeout: Optional[float] = None) -> Generator[bool, None, None]:
    """
    Hold the lock of a file while the block runs

    The lock is a separate file, path + ".lock", which is never deleted. It
    is held through an operating system lock (flock, or msvcrt.locking on
    Windows), which ends when the process does, so a process that crashes
    never leaves the file locked.

    Args:
        path: The file to lock
        timeout: Seconds to wait for the lock (default LOCK_TIMEOUT_SECONDS)

    Yields:
        True if the lock is held. False if it could not be taken within the
        timeout, or the file system does not support locks; the block then
        runs without the lock and a warning is logged, so a process that
        holds the lock too long never stops the others.
    """
    timeout = LOCK_TIMEOUT_SECONDS if timeout is None else timeout
    deadline = time.monotonic() + timeout
    lock_path = os.path.abspath(path) + ".lock"
    with _locks_guard:
        lock = _locks.setdefault(lock_path, _PathLock())

    if not lock.thread_lock.acquire(timeout=max(timeout, 0)):
        logger.warning("Another thread held %s for more than %s seconds; going on without the lock", lock_path, timeout)
        yield False
        return
    try:
        if lock.depth == 0:
            lock.fd = _lock_file(lock_path, deadline, timeout)
        held = lock.fd is not None
        if held:
            lock.depth += 1
        try:
            yield held
        finally:
            if held:
                lock.depth -= 1
                if lock.depth == 0 and lock.fd is not None:
                    _unlock_file(lock_path, lock.fd)
                    lock.fd = None
    finally:
        lock.thread_lock.release()


def _lock_file(lock_path: str, deadline: float, timeout: float) -> Optional[int]:
    """Lock lock_path for this process, polling until the deadline

    Returns:
        The open lock file, which holds the lock, or None if it is not locked
    """
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as e:
        logger.warning("Could not open the lock file %s (%s); going on without the lock", lock_path, e)
        return None
    while True:
        try:
            if os.name == "nt":
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError as e:
            # flock reports a lock held elsewhere as BlockingIOError;
            # msvcrt.locking raises OSError for it
            busy = isinstance(e, BlockingIOError) or os.name == "nt"
            if not busy:
                os.close(fd)
                logger.warning("Could not lock %s (%s); going on without the lock", lock_path, e)
                return None
        if time.monotonic() >= deadline:
            os.close(fd)
            logger.warning("Another process held %s for more than %s seconds; going on without the lock",
                           lock_path, timeout)
            return None
        time.sleep(min(_POLL_SECONDS, max(deadline - time.monotonic(), 0)))


def _unlock_file(lock_path: str, fd: int) -> None:
    try:
        if os.name == "nt":
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError as e:
        logger.warning("Could not unlock %s: %s", lock_path, e)
    finally:
        # Closing the file also releases the lock
        os.close(fd)
