"""Error handling: response parsing, exception types, 401 recovery, and token expiry.

The response bodies and headers below are copies of live Kroger API responses
captured on 2026-10-21.
"""
import json
import os
import time

import pytest
import requests

from kroger_api import KrogerAPI
from kroger_api.client import DEFAULT_TIMEOUT
from kroger_api.errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConfigurationError,
    InternalServerError,
    InvalidResponseError,
    KrogerAPIError,
    NotAuthenticatedError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from kroger_api.token_storage import load_token, save_token

BASE = "https://api.kroger.com"
TOKEN_URL = f"{BASE}/v1/connect/oauth2/token"
CORRELATION = "akam_1792605127_f359b0c4-65e2-44c8-a4c9-0c1fb72e39a1"
GATEWAY_401 = {
    "status_code": 401,
    "json": {"message": "Unauthorized"},
    "headers": {"WWW-Authenticate": 'Bearer realm="api.kroger.com", error="invalid_token"'},
}


@pytest.fixture(autouse=True)
def token_dir(tmp_path, monkeypatch):
    """Keep every token file a test writes out of the real data directory."""
    monkeypatch.setenv("KROGER_TOKEN_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def kroger():
    api = KrogerAPI(client_id="id", client_secret="secret", redirect_uri="http://localhost:8000/callback")
    api.client.token_info = {"access_token": "valid", "expires_in": 1800, "expires_at": time.time() + 1800}
    return api


def test_bad_request_carries_kroger_code_reason_and_correlation_id(kroger, requests_mock):
    requests_mock.get(
        f"{BASE}/v1/products",
        status_code=400,
        json={"errors": {"timestamp": 1792605127667, "code": "PRODUCT-2017",
                         "reason": "Field 'term' must have three or more characters and less than 128 characters"}},
        headers={"X-Correlation-Id": CORRELATION},
    )
    # A term the client accepts (three characters) but the mocked API rejects.
    with pytest.raises(BadRequestError) as excinfo:
        kroger.product.search_products(term="abc", location_id="01400513")
    error = excinfo.value
    assert error.status_code == 400
    assert error.kroger_code == "PRODUCT-2017"
    assert error.kroger_message.startswith("Field 'term' must have three")
    assert error.correlation_id == CORRELATION
    assert error.method == "GET"
    text = str(error)
    assert text.startswith("Kroger API error 400 Bad Request: Field 'term' must have three")
    assert "[PRODUCT-2017]" in text
    assert "request: GET /v1/products?filter.term=abc&filter.locationId=01400513" in text
    assert CORRELATION in text
    # Backward compatible with code written for requests' HTTPError
    assert isinstance(error, requests.exceptions.HTTPError)
    assert error.response.status_code == 400


def test_flat_403_body_on_cart_gets_user_token_hint(kroger, requests_mock):
    requests_mock.put(
        f"{BASE}/v1/cart/add",
        status_code=403,
        json={"timestamp": 1792605135282, "code": "AUTH-1007", "reason": "Invalid token on request"},
    )
    with pytest.raises(PermissionDeniedError) as excinfo:
        kroger.cart.add_to_cart([{"upc": "0001111041700", "quantity": 1, "modality": "PICKUP"}])
    error = excinfo.value
    assert error.kroger_code == "AUTH-1007"
    assert error.kroger_message == "Invalid token on request"
    assert "cart.basic:write" in error.hint


def test_404_with_empty_body_explains_what_is_missing(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/locations/99999999", status_code=404, text="")
    with pytest.raises(NotFoundError) as excinfo:
        kroger.location.get_location("99999999")
    error = excinfo.value
    assert error.kroger_message is None and error.body is None
    assert "no error message in the response body" in str(error)
    assert "No store has this locationId" in error.hint


@pytest.mark.parametrize(
    "status, body, expected_class, hint_fragment",
    [
        (401, {"error": "unauthorized", "error_description": "invalid credentials"}, AuthenticationError, "KROGER_CLIENT_ID"),
        (400, {"error": "invalid_scope", "error_description": "invalid scope not.a.scope"}, BadRequestError, "enabled for this app"),
        (400, {"error": "invalid_request", "error_description": "invalid refresh_token"}, BadRequestError, "Sign the user in again"),
        (400, {"error": "invalid_request", "error_description": "invalid code"}, BadRequestError, "Start the sign-in again"),
    ],
)
def test_token_endpoint_errors(requests_mock, status, body, expected_class, hint_fragment):
    requests_mock.post(TOKEN_URL, status_code=status, json=body)
    api = KrogerAPI(client_id="id", client_secret="wrong")
    with pytest.raises(expected_class) as excinfo:
        api.authorization.get_token_with_client_credentials("product.compact")
    error = excinfo.value
    assert error.kroger_code == body["error"]
    assert error.kroger_message == body["error_description"]
    assert hint_fragment in error.hint


def test_rate_limit_reports_retry_after(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", status_code=429, text="", headers={"Retry-After": "120"})
    with pytest.raises(RateLimitError) as excinfo:
        kroger.location.list_chains()
    assert excinfo.value.retry_after == 120
    assert "retry after: 120 seconds" in str(excinfo.value)


def test_html_server_error_keeps_body_but_not_as_message(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", status_code=503, text="<html><body>Service Unavailable</body></html>",
                      headers={"Content-Type": "text/html"})
    with pytest.raises(InternalServerError) as excinfo:
        kroger.location.list_chains()
    error = excinfo.value
    assert error.kroger_message is None
    assert "Service Unavailable" in error.body
    assert "retry may succeed" in error.hint


def test_unmapped_status_uses_base_class(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", status_code=418, text="")
    with pytest.raises(APIStatusError) as excinfo:
        kroger.location.list_chains()
    assert type(excinfo.value) is APIStatusError


def test_non_json_success_body_raises_invalid_response(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", status_code=200, text="<html>maintenance</html>")
    with pytest.raises(InvalidResponseError) as excinfo:
        kroger.location.list_chains()
    assert "not valid JSON" in str(excinfo.value)


def test_connection_failure_and_timeout_are_wrapped(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", exc=requests.exceptions.ConnectionError("Name or service not known"))
    with pytest.raises(APIConnectionError) as excinfo:
        kroger.location.list_chains()
    assert isinstance(excinfo.value, requests.exceptions.ConnectionError)
    assert "Name or service not known" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, requests.exceptions.ConnectionError)

    requests_mock.get(f"{BASE}/v1/departments", exc=requests.exceptions.ReadTimeout("read timed out"))
    with pytest.raises(APITimeoutError) as excinfo:
        kroger.location.list_departments()
    assert isinstance(excinfo.value, requests.exceptions.Timeout)
    assert isinstance(excinfo.value, APIConnectionError)
    assert "did not respond within 30 seconds" in str(excinfo.value)


def test_requests_carry_the_default_timeout(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", json={"data": []})
    kroger.location.list_chains()
    assert requests_mock.request_history[0].timeout == DEFAULT_TIMEOUT


def test_to_dict_is_json_serializable(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/locations/99999999", status_code=404, text="",
                      headers={"X-Correlation-Id": CORRELATION})
    with pytest.raises(NotFoundError) as excinfo:
        kroger.location.get_location("99999999")
    data = json.loads(json.dumps(excinfo.value.to_dict()))
    assert data["type"] == "not_found"
    assert data["status_code"] == 404
    assert data["url"] == f"{BASE}/v1/locations/99999999"
    assert data["correlation_id"] == CORRELATION
    assert set(data) >= {"message", "status_text", "kroger_code", "kroger_message", "method",
                         "retry_after", "note", "hint", "response_body"}


def test_every_error_is_a_kroger_api_error(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", status_code=500, json={"errors": {"code": "LOCATION-4000", "reason": "boom"}})
    with pytest.raises(KrogerAPIError):
        kroger.location.list_chains()


# --- configuration and missing tokens -------------------------------------


def test_missing_credentials_raise_configuration_error(monkeypatch):
    monkeypatch.delenv("KROGER_CLIENT_ID", raising=False)
    monkeypatch.delenv("KROGER_CLIENT_SECRET", raising=False)
    with pytest.raises(ConfigurationError) as excinfo:
        KrogerAPI(client_id=None, client_secret=None)
    assert isinstance(excinfo.value, ValueError)
    assert "KROGER_CLIENT_ID" in str(excinfo.value) and "KROGER_CLIENT_SECRET" in str(excinfo.value)


def test_authorization_url_without_redirect_uri_raises_configuration_error(monkeypatch):
    monkeypatch.delenv("KROGER_REDIRECT_URI", raising=False)
    api = KrogerAPI(client_id="id", client_secret="secret")
    with pytest.raises(ConfigurationError) as excinfo:
        api.authorization.get_authorization_url(scope="cart.basic:write")
    assert "KROGER_REDIRECT_URI" in str(excinfo.value)


def test_request_without_token_raises_not_authenticated(requests_mock):
    api = KrogerAPI(client_id="id", client_secret="secret")
    with pytest.raises(NotAuthenticatedError) as excinfo:
        api.location.list_chains()
    assert isinstance(excinfo.value, ValueError)
    assert requests_mock.call_count == 0


# --- 401 recovery ----------------------------------------------------------


def test_401_refreshes_user_token_and_retries(kroger, requests_mock):
    kroger.client.token_info["refresh_token"] = "refresh-1"
    kroger.client.token_file = ".kroger_token_user.json"
    requests_mock.get(f"{BASE}/v1/identity/profile",
                      [GATEWAY_401, {"status_code": 200, "json": {"data": {"id": "user-1"}}}])
    requests_mock.post(TOKEN_URL, json={"access_token": "new", "refresh_token": "refresh-2", "expires_in": 1800})

    assert kroger.identity.get_profile() == {"data": {"id": "user-1"}}
    token_request = requests_mock.request_history[1]
    assert "grant_type=refresh_token" in token_request.text and "refresh_token=refresh-1" in token_request.text
    assert requests_mock.request_history[2].headers["Authorization"] == "Bearer new"
    assert load_token(".kroger_token_user.json")["refresh_token"] == "refresh-2"


def test_401_replaces_client_credentials_token_and_retries(requests_mock):
    requests_mock.post(TOKEN_URL, [
        {"json": {"access_token": "first", "expires_in": 1800}},
        {"json": {"access_token": "second", "expires_in": 1800}},
    ])
    requests_mock.get(f"{BASE}/v1/chains", [GATEWAY_401, {"status_code": 200, "json": {"data": []}}])
    api = KrogerAPI(client_id="id", client_secret="secret")
    api.authorization.get_token_with_client_credentials("product.compact")

    assert api.location.list_chains() == {"data": []}
    assert requests_mock.request_history[-1].headers["Authorization"] == "Bearer second"


def test_401_when_refresh_fails_explains_why(kroger, requests_mock):
    kroger.client.token_info["refresh_token"] = "stale"
    requests_mock.get(f"{BASE}/v1/identity/profile", **GATEWAY_401)
    requests_mock.post(TOKEN_URL, status_code=400,
                       json={"error": "invalid_request", "error_description": "invalid refresh_token"})
    with pytest.raises(AuthenticationError) as excinfo:
        kroger.identity.get_profile()
    error = excinfo.value
    assert error.kroger_code == "invalid_token"
    assert error.kroger_message == "Unauthorized"
    assert "Getting a new token failed" in error.note and "invalid refresh_token" in error.note


def test_401_after_retry_says_it_was_retried(kroger, requests_mock):
    kroger.client.token_info["refresh_token"] = "refresh-1"
    requests_mock.get(f"{BASE}/v1/identity/profile", **GATEWAY_401)
    requests_mock.post(TOKEN_URL, json={"access_token": "new", "expires_in": 1800})
    with pytest.raises(AuthenticationError) as excinfo:
        kroger.identity.get_profile()
    assert "retried once" in excinfo.value.note
    assert sum(1 for r in requests_mock.request_history if r.method == "GET") == 2


def test_401_without_any_way_to_recover(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains", **GATEWAY_401)
    with pytest.raises(AuthenticationError) as excinfo:
        kroger.location.list_chains()
    assert "no refresh token" in excinfo.value.note
    assert requests_mock.call_count == 1


# --- token expiry ------------------------------------------------------------


def test_unexpired_token_is_valid_without_any_request(kroger, requests_mock):
    assert kroger.test_current_token() is True
    assert requests_mock.call_count == 0


def test_token_without_expiry_is_treated_as_valid(kroger, requests_mock):
    kroger.client.token_info = {"access_token": "handmade"}
    assert kroger.test_current_token() is True
    assert requests_mock.call_count == 0


def test_expired_token_with_refresh_token_is_refreshed(kroger, requests_mock):
    kroger.client.token_info = {"access_token": "old", "refresh_token": "r", "expires_at": time.time() - 10}
    requests_mock.post(TOKEN_URL, json={"access_token": "new", "expires_in": 1800})
    assert kroger.test_current_token() is True
    assert kroger.client.token_info["access_token"] == "new"
    # The refresh response had no refresh token, so the old one is kept (RFC 6749 section 6)
    assert kroger.client.token_info["refresh_token"] == "r"


def test_expired_token_without_refresh_token_is_invalid(kroger, requests_mock):
    kroger.client.token_info = {"access_token": "old", "expires_at": time.time() - 10}
    assert kroger.test_current_token() is False
    assert requests_mock.call_count == 0


def test_legacy_token_file_gets_expiry_from_its_mtime(token_dir):
    save_token({"access_token": "legacy", "expires_in": 1800}, ".legacy.json")
    path = token_dir / ".legacy.json"
    an_hour_ago = time.time() - 3600
    os.utime(path, (an_hour_ago, an_hour_ago))
    token_info = load_token(".legacy.json")
    assert token_info["expires_at"] == pytest.approx(an_hour_ago + 1800, abs=1)


def test_refresh_token_if_needed_installs_an_unexpired_token(requests_mock):
    save_token({"access_token": "saved", "refresh_token": "r", "expires_in": 1800}, ".kroger_token_user.json")
    api = KrogerAPI(client_id="id", client_secret="secret")
    assert api.authorization.refresh_token_if_needed()["access_token"] == "saved"
    assert api.client.token_info["access_token"] == "saved"
    requests_mock.get(f"{BASE}/v1/chains", json={"data": []})
    api.location.list_chains()
    assert requests_mock.last_request.headers["Authorization"] == "Bearer saved"


def test_refresh_token_if_needed_refreshes_an_expired_token(requests_mock):
    save_token({"access_token": "old", "refresh_token": "r", "expires_in": 1800,
                "expires_at": time.time() - 10}, ".kroger_token_user.json")
    requests_mock.post(TOKEN_URL, json={"access_token": "new", "expires_in": 1800})
    api = KrogerAPI(client_id="id", client_secret="secret")
    assert api.authorization.refresh_token_if_needed()["access_token"] == "new"
    assert api.client.token_info["access_token"] == "new"
    assert load_token(".kroger_token_user.json")["access_token"] == "new"


def test_refresh_token_if_needed_returns_none_for_a_rejected_refresh_token(requests_mock):
    save_token({"access_token": "old", "refresh_token": "bad", "expires_in": 1800,
                "expires_at": time.time() - 10}, ".kroger_token_user.json")
    requests_mock.post(TOKEN_URL, status_code=400,
                       json={"error": "invalid_grant", "error_description": "invalid refresh_token"})
    api = KrogerAPI(client_id="id", client_secret="secret")
    assert api.authorization.refresh_token_if_needed() is None


def test_refresh_token_if_needed_raises_network_errors(requests_mock):
    save_token({"access_token": "old", "refresh_token": "r", "expires_in": 1800,
                "expires_at": time.time() - 10}, ".kroger_token_user.json")
    requests_mock.post(TOKEN_URL, exc=requests.exceptions.ConnectionError("down"))
    api = KrogerAPI(client_id="id", client_secret="secret")
    with pytest.raises(APIConnectionError):
        api.authorization.refresh_token_if_needed()


def test_saved_client_credentials_token_is_reused_until_it_expires(requests_mock):
    requests_mock.post(TOKEN_URL, [
        {"json": {"access_token": "first", "expires_in": 1800}},
        {"json": {"access_token": "second", "expires_in": 1800}},
    ])
    api = KrogerAPI(client_id="id", client_secret="secret")
    assert api.authorization.get_token_with_client_credentials("product.compact")["access_token"] == "first"
    assert api.authorization.get_token_with_client_credentials("product.compact")["access_token"] == "first"
    assert requests_mock.call_count == 1

    stale = load_token(".kroger_token_client_product.compact.json")
    stale["expires_at"] = time.time() - 10
    save_token(stale, ".kroger_token_client_product.compact.json")
    assert api.authorization.get_token_with_client_credentials("product.compact")["access_token"] == "second"
    assert requests_mock.call_count == 2


def test_user_token_401_is_never_replaced_by_an_app_token(requests_mock):
    requests_mock.post(TOKEN_URL, [
        {"json": {"access_token": "app", "expires_in": 1800}},
        {"json": {"access_token": "user", "expires_in": 1800}},  # no refresh token
    ])
    requests_mock.get(f"{BASE}/v1/identity/profile", **GATEWAY_401)
    api = KrogerAPI(client_id="id", client_secret="secret", redirect_uri="http://localhost:8000/callback")
    api.authorization.get_token_with_client_credentials("product.compact")
    api.authorization.get_token_with_authorization_code("code-1")
    with pytest.raises(AuthenticationError):
        api.identity.get_profile()
    assert requests_mock.call_count == 3  # two token requests and the 401; no third token request


def test_unknown_product_404_names_the_product(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/products/9999999999999", status_code=404, text="")
    with pytest.raises(NotFoundError) as excinfo:
        kroger.product.get_product("9999999999999")
    assert "No product has this productId" in excinfo.value.hint
