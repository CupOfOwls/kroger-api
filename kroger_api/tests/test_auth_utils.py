"""OAuth helpers and token storage."""
import os
import stat

import pytest

from kroger_api.token_storage import get_token_file_path, load_token, save_token
from kroger_api.utils.oauth import extract_port_from_redirect_uri, generate_random_state


@pytest.fixture(autouse=True)
def token_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KROGER_TOKEN_DIR", str(tmp_path))
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
