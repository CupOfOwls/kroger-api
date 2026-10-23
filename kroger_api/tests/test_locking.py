"""The file lock that token refreshes hold, across threads and processes"""
import errno
import logging
import os
import stat
import subprocess
import sys
import threading
import time

import pytest

from kroger_api.utils import locking
from kroger_api.utils.locking import file_lock

if os.name != "nt":
    import fcntl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Holds the lock of argv[1] until stdin closes, after printing "locked";
# argv[2], if given, is the timeout
HOLDER = """
import sys
from kroger_api.utils.locking import file_lock
with file_lock(sys.argv[1], timeout=float(sys.argv[2]) if len(sys.argv) > 2 else 5) as held:
    print("locked" if held else "not locked", flush=True)
    sys.stdin.read()
"""

posix_only = pytest.mark.skipif(os.name == "nt", reason="uses flock")


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "token.json")


@pytest.fixture
def other_process(path):
    """A process that holds the lock of path until the test ends"""
    process = subprocess.Popen([sys.executable, "-c", HOLDER, path], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, text=True,
                               cwd=REPO_ROOT)
    assert process.stdout.readline().strip() == "locked"
    yield process
    process.stdin.close()
    process.wait(timeout=10)


def test_threads_take_the_lock_one_at_a_time(path):
    events = []

    def worker(name):
        with file_lock(path, timeout=5) as held:
            events.append((name, "in", held))
            time.sleep(0.2)
            events.append((name, "out", held))

    threads = [threading.Thread(target=worker, args=(n,)) for n in "ab"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Each thread leaves before the other enters
    assert [e[1] for e in events] == ["in", "out", "in", "out"]
    assert all(e[2] for e in events)


def test_another_process_holding_the_lock_makes_this_one_wait(path, other_process):
    started = time.monotonic()
    with file_lock(path, timeout=0.3) as held:
        assert held is False
    assert time.monotonic() - started >= 0.3

    other_process.stdin.close()
    other_process.wait(timeout=10)
    with file_lock(path, timeout=5) as held:
        assert held is True


def another_process_can_lock(path, timeout=5):
    result = subprocess.run([sys.executable, "-c", HOLDER, path, str(timeout)], input="", capture_output=True,
                            text=True, timeout=30, cwd=REPO_ROOT)
    return result.stdout.strip() == "locked"


def test_lock_is_released_for_other_processes(path):
    with file_lock(path, timeout=5) as held:
        assert held
    # A new process gets the lock at once
    assert another_process_can_lock(path)


def test_timeout_goes_on_without_the_lock_and_warns(path, other_process, caplog):
    ran = []
    with caplog.at_level(logging.WARNING, logger="kroger_api.utils.locking"):
        with file_lock(path, timeout=0.1) as held:
            ran.append(held)
    assert ran == [False]
    assert "going on without the lock" in caplog.text


def test_lock_is_reentrant_within_a_thread(path):
    started = time.monotonic()
    with file_lock(path, timeout=2) as outer:
        with file_lock(path, timeout=2) as inner:
            assert outer and inner
    assert time.monotonic() - started < 1


def test_lock_file_is_private_and_kept(path):
    with file_lock(path):
        pass
    if os.name != "nt":  # Windows has no file modes; the file gets its folder's permissions
        assert stat.S_IMODE(os.stat(path + ".lock").st_mode) == 0o600
    with file_lock(path) as held:
        assert held


@pytest.mark.skipif(os.name == "nt", reason="flock is POSIX")
def test_file_system_without_locks_goes_on_without_the_lock(path, monkeypatch, caplog):
    def flock(fd, operation):
        raise OSError(errno.ENOLCK, "No locks available")

    monkeypatch.setattr(locking.fcntl, "flock", flock)
    started = time.monotonic()
    with caplog.at_level(logging.WARNING, logger="kroger_api.utils.locking"):
        with file_lock(path, timeout=5) as held:
            assert held is False
    # Not a lock held elsewhere, so there is nothing to wait for
    assert time.monotonic() - started < 1
    assert "No locks available" in caplog.text


@posix_only
def test_a_symbolic_link_to_the_file_shares_its_lock(path, tmp_path):
    open(path, "w").close()
    link = str(tmp_path / "link.json")
    os.symlink(path, link)
    with file_lock(link, timeout=5) as held:
        assert held
        assert another_process_can_lock(path, timeout=0.2) is False


@posix_only
@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs os.fork")
def test_a_forked_child_that_leaves_the_block_keeps_the_parents_lock(path):
    """The child's copy of the lock file shares the parent's lock, so unlocking it would release both"""

    def fork_in_block():
        with file_lock(path, timeout=5) as held:
            assert held
            child = os.fork()
            if child:
                os.waitpid(child, 0)
                # The child has left the block and exited
                return another_process_can_lock(path, timeout=0.2)

    parent = os.getpid()
    try:
        locked_elsewhere = fork_in_block()
    finally:
        if os.getpid() != parent:
            os._exit(0)
    assert locked_elsewhere is False
    assert another_process_can_lock(path)


class FakeMsvcrt:
    """msvcrt.locking as Microsoft documents it, on top of flock, to run the Windows code here

    A lock held elsewhere fails with EACCES, and locking and unlocking start
    at the file's current position. Each call is recorded as (mode, position, nbytes).
    """

    LK_UNLCK, LK_NBLCK = 0, 2

    def __init__(self):
        self.calls = []

    def locking(self, fd, mode, nbytes):
        self.calls.append((mode, os.lseek(fd, 0, os.SEEK_CUR), nbytes))
        if mode == self.LK_UNLCK:
            fcntl.flock(fd, fcntl.LOCK_UN)
            return
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PermissionError(errno.EACCES, "Permission denied") from None


@pytest.fixture
def windows(monkeypatch):
    fake = FakeMsvcrt()
    monkeypatch.setattr(locking, "_WINDOWS", True)
    monkeypatch.setattr(locking, "msvcrt", fake, raising=False)
    return fake


@posix_only
def test_windows_waits_for_a_lock_held_by_another_process(path, other_process, windows):
    started = time.monotonic()
    with file_lock(path, timeout=0.3) as held:
        assert held is False
    assert time.monotonic() - started >= 0.3
    assert len(windows.calls) > 1
    assert all(call == (FakeMsvcrt.LK_NBLCK, 0, 1) for call in windows.calls)

    other_process.stdin.close()
    other_process.wait(timeout=10)
    with file_lock(path, timeout=5) as held:
        assert held is True
    assert windows.calls[-1] == (FakeMsvcrt.LK_UNLCK, 0, 1)
    assert another_process_can_lock(path)


@posix_only
def test_windows_error_other_than_a_held_lock_goes_on_at_once(path, windows, monkeypatch, caplog):
    def locking(fd, mode, nbytes):
        raise OSError(errno.EBADF, "Bad file descriptor")

    monkeypatch.setattr(windows, "locking", locking)
    started = time.monotonic()
    with caplog.at_level(logging.WARNING, logger="kroger_api.utils.locking"):
        with file_lock(path, timeout=5) as held:
            assert held is False
    assert time.monotonic() - started < 1
    assert "Bad file descriptor" in caplog.text
