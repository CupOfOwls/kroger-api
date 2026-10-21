"""OAuth helpers, the interactive sign-in, and token storage."""
import os
import stat
import time
from urllib.parse import parse_qs, urlparse

import pytest

from kroger_api import KrogerAPI
from kroger_api.token_storage import USER_TOKEN_FILE, get_token_file_path, load_token, save_token
from kroger_api.utils.oauth import extract_port_from_redirect_uri, generate_random_state


@pytest.fixture(autouse=True)
def token_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KROGER_TOKEN_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    "uri, port",
    [
        ("http://localhost:8000/callback", 8000),
        ("http://127.0.0.1:9000", 9000),
        ("http://localhost/callback", 80),
        ("https://example.com/callback", 443),
    ],
)
def test_port_comes_from_the_redirect_uri(uri, port):
    assert extract_port_from_redirect_uri(uri) == port


@pytest.mark.parametrize("uri", ["localhost/callback", "http://localhost:notaport/callback"])
def test_redirect_uri_without_a_usable_port_is_rejected(uri):
    with pytest.raises(ValueError):
        extract_port_from_redirect_uri(uri)


def test_random_state_is_unpredictable_and_url_safe():
    states = {generate_random_state() for _ in range(50)}
    assert len(states) == 50
    assert all(len(s) == 16 and all(c.isalnum() or c in "-_" for c in s) for s in states)


def test_saved_token_is_private_and_replaces_the_old_file(token_dir):
    save_token({"access_token": "first"}, "token.json")
    save_token({"access_token": "second"}, "token.json")
    path = get_token_file_path("token.json")
    assert load_token("token.json")["access_token"] == "second"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert sorted(os.listdir(token_dir)) == ["token.json"]  # no temporary file left behind


def test_failed_save_keeps_the_old_token(token_dir, monkeypatch):
    import json

    save_token({"access_token": "first"}, "token.json")

    def fail(*args, **kwargs):
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(json, "dump", fail)
        with pytest.raises(OSError):
            save_token({"access_token": "second"}, "token.json")
    assert load_token("token.json")["access_token"] == "first"
    assert sorted(os.listdir(token_dir)) == ["token.json"]


TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"


def test_sign_in_with_a_token_file_saves_only_to_that_file(monkeypatch, requests_mock):
    import kroger_api.auth.interactive as interactive

    monkeypatch.setenv("KROGER_CLIENT_ID", "id")
    monkeypatch.setenv("KROGER_CLIENT_SECRET", "secret")
    monkeypatch.setenv("KROGER_REDIRECT_URI", "http://localhost:8765/callback")
    save_token({"access_token": "DEFAULT", "refresh_token": "r0", "expires_at": time.time() + 1800}, USER_TOKEN_FILE)

    class Server:
        def shutdown(self):
            pass

    callbacks = []
    monkeypatch.setattr(interactive, "start_oauth_server", lambda port, cb: (callbacks.append(cb), (Server(), None))[1])

    def approve(url):
        callbacks[0]("CODE", parse_qs(urlparse(url).query)["state"][0])

    monkeypatch.setattr(interactive, "open_browser_for_auth", approve)
    requests_mock.post(TOKEN_URL, json={"access_token": "ALT", "refresh_token": "r1", "expires_in": 1800})

    kroger = interactive.authenticate_user(token_file="alt.json", timeout=5)

    assert load_token("alt.json")["access_token"] == "ALT"
    assert load_token(USER_TOKEN_FILE)["access_token"] == "DEFAULT"
    assert kroger.client.token_file == "alt.json"


def test_unusable_saved_token_does_not_change_the_clients_token_file():
    # An expired user token without a refresh token cannot be used, so the
    # client keeps saving its own tokens where it did before
    save_token({"access_token": "OLD", "expires_at": time.time() - 60}, USER_TOKEN_FILE)
    kroger = KrogerAPI(client_id="id", client_secret="secret")
    kroger.client.token_file = ".kroger_token_client_product.compact.json"

    assert kroger.authorization.refresh_token_if_needed(USER_TOKEN_FILE) is None
    assert kroger.client.token_file == ".kroger_token_client_product.compact.json"


def test_rejected_refresh_does_not_change_the_clients_token_file(requests_mock):
    save_token({"access_token": "OLD", "refresh_token": "r0", "expires_at": time.time() - 60}, USER_TOKEN_FILE)
    requests_mock.post(
        TOKEN_URL, status_code=400, json={"error": "invalid_request", "error_description": "invalid refresh_token"}
    )
    kroger = KrogerAPI(client_id="id", client_secret="secret")
    kroger.client.token_file = None

    assert kroger.authorization.refresh_token_if_needed(USER_TOKEN_FILE) is None
    assert kroger.client.token_file is None


def test_env_file_supplies_only_kroger_settings_from_the_working_directory(tmp_path, monkeypatch):
    from kroger_api.utils.env import load_env_file

    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / ".env").write_text("KROGER_USER_ZIP_CODE=45202\nKROGER_CLIENT_ID=from-file\nHTTPS_PROXY=http://proxy:3128\n")
    monkeypatch.setenv("KROGER_CLIENT_ID", "from-environment")
    for name in ("KROGER_USER_ZIP_CODE", "HTTPS_PROXY"):
        # setenv first, so that monkeypatch also removes what load_env_file sets
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)

    # A .env file in a parent of the working directory is not read
    monkeypatch.chdir(project / "src")
    load_env_file()
    assert "KROGER_USER_ZIP_CODE" not in os.environ

    monkeypatch.chdir(project)
    load_env_file()
    assert os.environ["KROGER_USER_ZIP_CODE"] == "45202"
    assert os.environ["KROGER_CLIENT_ID"] == "from-environment"
    assert "HTTPS_PROXY" not in os.environ
