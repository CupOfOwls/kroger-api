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

_WINDOWS = os.name == "nt"
if _WINDOWS:
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
        # The process that locked fd. A child forked while the lock is held
        # has a copy of fd that shares the lock, and must not unlock it.
        self.pid: Optional[int] = None


_locks: Dict[str, _PathLock] = {}
_locks_guard = threading.Lock()


def _forget_locks():
    # A child process has only the thread that forked it, so locks held by
    # other threads of the parent would never be released in the child. Its
    # copies of their lock files close when it runs another program or exits.
    global _locks, _locks_guard
    _locks, _locks_guard = {}, threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_forget_locks)


@contextmanager
def file_lock(path: str, timeout: Optional[float] = None) -> Generator[bool, None, None]:
    """
    Hold the lock of a file while the block runs

    The lock is a separate file, the resolved path + ".lock", which is never deleted. It
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
    # Two paths to one file, through a symbolic link, share one lock
    lock_path = os.path.realpath(path) + ".lock"
    with _locks_guard:
        lock = _locks.setdefault(lock_path, _PathLock())

    if not lock.thread_lock.acquire(timeout=max(timeout, 0)):
        logger.warning("Another thread held %s for more than %s seconds; going on without the lock", lock_path, timeout)
        yield False
        return
    try:
        if lock.depth == 0:
            lock.fd = _lock_file(lock_path, deadline, timeout)
            lock.pid = os.getpid()
        held = lock.fd is not None
        if held:
            lock.depth += 1
        try:
            yield held
        finally:
            if held:
                lock.depth -= 1
                if lock.depth == 0 and lock.fd is not None:
                    if lock.pid == os.getpid():
                        _unlock_file(lock_path, lock.fd)
                    else:
                        # A forked child: closing its copy leaves the parent's lock held
                        os.close(lock.fd)
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
            if _WINDOWS:
                # Some versions of the C runtime wait 1 second before they
                # report a lock held elsewhere, so on Windows an attempt can
                # take that long and the timeout can be exceeded by as much
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError as e:
            # A lock held elsewhere is EWOULDBLOCK (BlockingIOError) from
            # flock and EACCES (PermissionError) from msvcrt.locking. Other
            # errors, such as a file system without locks, do not go away
            # with waiting.
            busy = isinstance(e, PermissionError if _WINDOWS else BlockingIOError)
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
        if _WINDOWS:
            # msvcrt.locking unlocks from the current position, like it locks
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError as e:
        logger.warning("Could not unlock %s: %s", lock_path, e)
    finally:
        # Closing the file also releases the lock
        os.close(fd)
