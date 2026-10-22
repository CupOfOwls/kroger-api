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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Holds the lock of argv[1] until stdin closes, after printing "locked"
HOLDER = """
import sys
from kroger_api.utils.locking import file_lock
with file_lock(sys.argv[1], timeout=5) as held:
    print("locked" if held else "not locked", flush=True)
    sys.stdin.read()
"""


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


def test_lock_is_released_for_other_processes(path):
    with file_lock(path, timeout=5) as held:
        assert held
    # A new process gets the lock at once
    result = subprocess.run([sys.executable, "-c", HOLDER, path], input="", capture_output=True, text=True,
                            timeout=10, cwd=REPO_ROOT)
    assert result.stdout.strip() == "locked"


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
