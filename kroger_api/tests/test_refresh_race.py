"""Threads and processes that renew the same saved token at the same moment

The token server here rotates refresh tokens and, as RFC 9700 section 4.14.2
recommends, treats a refresh token that is sent again as stolen: it rejects
it and revokes the newer one too. Two refreshes of the same token at once
would then sign the user out.
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import pytest

from kroger_api import KrogerAPI
from kroger_api.client import KrogerClient
from kroger_api.token_storage import USER_TOKEN_FILE, load_token, save_token

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TokenServer:
    """A Kroger token endpoint that rotates refresh tokens and detects reuse

    It also serves the Identity profile, which rejects the access token a0
    as revoked: two requests with a0 are both held until both have arrived.
    """

    def __init__(self, delay=0.5):
        self.delay = delay
        self.current = "r0"
        self.issued = 0
        self.requests = []
        self.lock = threading.Lock()
        self.both_sent = threading.Barrier(2)
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.headers["Authorization"] == "Bearer a0":
                    server.both_sent.wait(timeout=5)
                    self.answer(401, {"message": "Unauthorized"})
                else:
                    self.answer(200, {"data": {"id": "user-1"}})

            def do_POST(self):
                body = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
                refresh_token = body["refresh_token"][0]
                server.requests.append(refresh_token)
                # Keep both requests in flight at once, if two are sent
                time.sleep(server.delay)
                with server.lock:
                    if refresh_token == server.current:
                        server.issued += 1
                        server.current = f"r{server.issued}"
                        status, answer = 200, {"access_token": f"a{server.issued}", "refresh_token": server.current,
                                               "expires_in": 1800}
                    else:
                        server.current = ""  # reuse: revoke the whole sign-in
                        status, answer = 400, {"error": "invalid_request", "error_description": "invalid refresh_token"}
                self.answer(status, answer)

            def answer(self, status, answer):
                data = json.dumps(answer).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def token_server(monkeypatch):
    server = TokenServer()
    monkeypatch.setattr(KrogerClient, "BASE_URL", server.url)
    yield server
    server.close()


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("KROGER_TOKEN_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NO_PROXY", "*")
    for name in ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


# Loads the expired saved token, renewing it, when the "go" file appears
RENEWER = """
import json, os, sys, time
from kroger_api import KrogerAPI
from kroger_api.client import KrogerClient
KrogerClient.BASE_URL = sys.argv[1]
kroger = KrogerAPI(client_id="id", client_secret="secret")
print("ready", flush=True)
while not os.path.exists(sys.argv[2]):
    time.sleep(0.01)
token = kroger.authorization.refresh_token_if_needed()
print(json.dumps(token and token["access_token"]), flush=True)
"""


def test_two_processes_renew_an_expired_token_once(token_server, isolated):
    save_token({"access_token": "a0", "refresh_token": "r0", "expires_at": time.time() - 60}, USER_TOKEN_FILE)
    go = isolated / "go"
    processes = [
        subprocess.Popen([sys.executable, "-c", RENEWER, token_server.url, str(go)], cwd=REPO_ROOT,
                         stdout=subprocess.PIPE, text=True, env={**os.environ})
        for _ in range(2)
    ]
    for process in processes:
        assert process.stdout.readline().strip() == "ready"
    go.touch()
    results = [json.loads(process.communicate(timeout=30)[0]) for process in processes]

    # One refresh; the other process waited and used the renewed token
    assert token_server.requests == ["r0"]
    assert results == ["a1", "a1"]
    assert load_token(USER_TOKEN_FILE)["refresh_token"] == "r1"


def test_two_threads_that_get_401_at_once_refresh_once(token_server):
    """One client shared by two threads, as in kroger-mcp, and an access token that Kroger revoked early"""
    save_token({"access_token": "a0", "refresh_token": "r0", "expires_at": time.time() + 1800}, USER_TOKEN_FILE)
    kroger = KrogerAPI(client_id="id", client_secret="secret")
    assert kroger.authorization.refresh_token_if_needed()["access_token"] == "a0"
    results, errors = [], []

    def call():
        try:
            results.append(kroger.identity.get_profile())
        except Exception as e:  # reported below
            errors.append(e)

    threads = [threading.Thread(target=call) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert errors == []
    assert results == [{"data": {"id": "user-1"}}] * 2
    assert token_server.requests == ["r0"]
    assert kroger.client.token_info["access_token"] == "a1"


def test_test_token_uses_the_token_another_process_renewed(token_server):
    expired = {"access_token": "a0", "refresh_token": "r0", "expires_at": time.time() - 60}
    save_token(expired, USER_TOKEN_FILE)
    kroger = KrogerAPI(client_id="id", client_secret="secret")
    kroger.client.token_info = dict(expired)
    kroger.client.token_file = USER_TOKEN_FILE
    # Another process renews the saved token first
    other = KrogerAPI(client_id="id", client_secret="secret")
    assert other.authorization.refresh_token_if_needed()["access_token"] == "a1"
    assert token_server.requests == ["r0"]

    assert kroger.test_current_token() is True
    assert kroger.client.token_info["access_token"] == "a1"
    assert token_server.requests == ["r0"]  # r0 was not sent again


def test_load_saved_token_explains_why_it_cannot_load_one(token_server):
    from kroger_api.errors import BadRequestError, NotAuthenticatedError

    kroger = KrogerAPI(client_id="id", client_secret="secret")
    with pytest.raises(NotAuthenticatedError, match="no saved token"):
        kroger.authorization.load_saved_token()

    save_token({"access_token": "a0", "expires_at": time.time() - 60}, USER_TOKEN_FILE)
    with pytest.raises(NotAuthenticatedError, match="has expired and has no refresh token"):
        kroger.authorization.load_saved_token()

    save_token({"access_token": "a0", "refresh_token": "stale", "expires_at": time.time() - 60}, USER_TOKEN_FILE)
    with pytest.raises(BadRequestError) as excinfo:
        kroger.authorization.load_saved_token()
    assert excinfo.value.kroger_message == "invalid refresh_token"
    assert kroger.authorization.refresh_token_if_needed() is None


def _hold_lock_then_save(token_info, held, seconds=0.3):
    """In another thread: hold the user token file's lock, then save token_info and release"""
    from kroger_api.token_storage import token_file_lock

    def run():
        with token_file_lock(USER_TOKEN_FILE):
            held.set()
            time.sleep(seconds)
            save_token(token_info, USER_TOKEN_FILE)

    thread = threading.Thread(target=run)
    thread.start()
    assert held.wait(timeout=5)
    return thread


def test_sign_in_is_not_overwritten_by_a_refresh_in_progress(requests_mock):
    """A refresh of the previous sign-in finishes after the new sign-in's code exchange"""
    requests_mock.post(f"{KrogerClient.BASE_URL}/v1/connect/oauth2/token",
                       json={"access_token": "signed-in", "refresh_token": "s1", "expires_in": 1800})
    kroger = KrogerAPI(client_id="id", client_secret="secret", redirect_uri="http://localhost:8000/callback")
    held = threading.Event()
    refresh = _hold_lock_then_save({"access_token": "refreshed-old", "refresh_token": "r1", "expires_in": 1800,
                                    "expires_at": time.time() + 1800}, held)
    kroger.authorization.get_token_with_authorization_code("CODE")
    refresh.join()
    assert load_token(USER_TOKEN_FILE)["access_token"] == "signed-in"


def test_sign_out_is_not_undone_by_a_refresh_in_progress():
    from kroger_api.token_storage import clear_token

    save_token({"access_token": "a0", "refresh_token": "r0", "expires_at": time.time() - 60}, USER_TOKEN_FILE)
    held = threading.Event()
    refresh = _hold_lock_then_save({"access_token": "a1", "refresh_token": "r1", "expires_in": 1800,
                                    "expires_at": time.time() + 1800}, held)
    clear_token(USER_TOKEN_FILE)
    refresh.join()
    assert load_token(USER_TOKEN_FILE) is None


def test_refresh_rejected_because_another_process_renewed_without_the_lock(requests_mock):
    """An older kroger-api, which does not take the lock, renews the token while this one refreshes"""
    save_token({"access_token": "a0", "refresh_token": "r0", "expires_at": time.time() - 60}, USER_TOKEN_FILE)

    def token_response(request, context):
        save_token({"access_token": "from-other", "refresh_token": "r1", "expires_in": 1800,
                    "expires_at": time.time() + 1800}, USER_TOKEN_FILE)
        context.status_code = 400
        return {"error": "invalid_request", "error_description": "invalid refresh_token"}

    requests_mock.post(f"{KrogerClient.BASE_URL}/v1/connect/oauth2/token", json=token_response)
    kroger = KrogerAPI(client_id="id", client_secret="secret")
    assert kroger.authorization.load_saved_token()["access_token"] == "from-other"
