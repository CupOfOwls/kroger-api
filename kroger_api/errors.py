"""
Exceptions raised by kroger-api.

Every exception derives from KrogerAPIError, so a single
``except KrogerAPIError`` catches anything the library raises about a request.
HTTP-status and network errors also derive from the matching ``requests``
exception, so code written for earlier versions (``except
requests.exceptions.HTTPError`` followed by ``e.response.status_code``) still
catches every error response. It no longer catches invalid arguments: those
raise InvalidParameterError, a ValueError, before any request is sent.
Catch KrogerAPIError to handle both.

    KrogerAPIError
    ├── ConfigurationError        (also ValueError)  missing credentials or settings
    ├── InvalidParameterError     (also ValueError)  bad argument, nothing was sent
    ├── NotAuthenticatedError     (also ValueError)  no access token on the client
    ├── APIConnectionError        (also requests ConnectionError)
    │   └── APITimeoutError       (also requests Timeout)
    ├── APIStatusError            (also requests HTTPError)  non-2xx response
    │   ├── BadRequestError       400
    │   ├── AuthenticationError   401
    │   ├── PermissionDeniedError 403
    │   ├── NotFoundError         404
    │   ├── RateLimitError        429
    │   └── InternalServerError   5xx
    └── InvalidResponseError      2xx response that is not valid JSON

Each exception has a ``to_dict()`` that returns its details as JSON-safe
data, for logging or for returning to another program (kroger-mcp uses it for
structured tool errors), and an ``outcome_unknown`` flag that is True when the
failed request may have changed data anyway, so resending it could repeat the
change (for example, add cart items twice).
"""

import email.utils
import http
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

import requests

TOKEN_ENDPOINT = "/v1/connect/oauth2/token"

# Methods that never change data, so resending them is always safe.
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

# Bodies longer than this are truncated in messages and to_dict() output.
_MAX_BODY_CHARS = 2000


def _json_safe(value: Any) -> Any:
    """Return value if it serializes to JSON as-is, else its repr()."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return repr(value)


def _changes_data(method: str, url: Optional[str]) -> bool:
    """True for a request that can change data, such as PUT /v1/cart/add.

    Token requests count as safe: resending one creates nothing, and at worst
    the token endpoint rejects a code or refresh token that was already used.
    """
    return method.upper() not in SAFE_METHODS and urlsplit(url or "").path != TOKEN_ENDPOINT


def _rebuild(cls: type, args: tuple, state: Dict[str, Any]) -> "KrogerAPIError":
    """Unpickle an error without calling its __init__, whose arguments differ per class."""
    error = cls.__new__(cls)
    error.args = args
    error.__dict__.update(state)
    return error


def _display_url(url: Optional[str]) -> str:
    """Path and query of a URL, which is all a reader needs to identify the call."""
    if not url:
        return "<unknown URL>"
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "")


class KrogerAPIError(Exception):
    """Base class for every error kroger-api raises."""

    #: Short, stable, machine-readable category of the error.
    error_type = "kroger_api_error"

    #: True when the request may have changed data before it failed, so
    #: resending it could repeat the change. Only a timeout, a lost
    #: connection, a 5xx, or an unreadable 2xx on a request that changes data
    #: (such as a cart add) can leave the outcome unknown.
    outcome_unknown = False

    def __init__(self, message: str, *args: Any, **kwargs: Any):
        super().__init__(message, *args, **kwargs)
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __reduce__(self):
        # The default pickling calls cls(*self.args), which does not match
        # the __init__ signature of most subclasses.
        return _rebuild, (type(self), self.args, self.__dict__)

    def to_dict(self) -> Dict[str, Any]:
        """The error's details as JSON-safe data."""
        return {"type": self.error_type, "message": self.message, "outcome_unknown": self.outcome_unknown}


class ConfigurationError(KrogerAPIError, ValueError):
    """A required setting, such as the client ID or redirect URI, is missing."""

    error_type = "configuration_error"


class InvalidParameterError(KrogerAPIError, ValueError):
    """An argument failed validation, so no request was sent.

    Attributes:
        param: Name of the argument, as the method's caller spells it
            (for example ``limit`` or ``items[2].upc``).
        value: The rejected value.
        requirement: What a valid value looks like.
    """

    error_type = "invalid_parameter"

    def __init__(self, param: str, value: Any, requirement: str):
        self.param = param
        self.value = value
        self.requirement = requirement
        super().__init__(f"Invalid {param}={value!r}: {requirement}. No request was sent.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "param": self.param,
            "value": _json_safe(self.value),
            "requirement": self.requirement,
        }


class NotAuthenticatedError(KrogerAPIError, ValueError):
    """The client has no access token, so it cannot call an authenticated endpoint."""

    error_type = "not_authenticated"


_UNKNOWN_OUTCOME_NOTE = (
    "The request may have reached Kroger before the connection failed, so check its effect "
    "(for a cart add, the cart in the Kroger app or website) before resending it."
)


class APIConnectionError(KrogerAPIError, requests.exceptions.ConnectionError):
    """The request got no HTTP response: DNS failure, refused or reset connection, TLS error.

    Attributes:
        method: HTTP method of the request.
        url: Full request URL.
        reason: The network error, as ``requests`` reported it.
        request_sent: False when the client never connected, so the request
            certainly did not reach Kroger; None when it may have.

    The underlying ``requests`` exception is chained as ``__cause__``.
    """

    error_type = "connection_error"

    def __init__(self, method: str, url: str, reason: str, request: Any = None, message: Optional[str] = None,
                 request_sent: Optional[bool] = None):
        self.method = method
        self.url = url
        self.reason = reason
        self.request_sent = request_sent
        message = message or f"Could not reach the Kroger API for {method} {_display_url(url)}: {reason}"
        if self.outcome_unknown:
            message += f" {_UNKNOWN_OUTCOME_NOTE}"
        super().__init__(message, request=request)

    @property
    def outcome_unknown(self) -> bool:
        return self.request_sent is not False and _changes_data(self.method, self.url)

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "method": self.method, "url": self.url, "reason": self.reason,
                "request_sent": self.request_sent}


class APITimeoutError(APIConnectionError, requests.exceptions.Timeout):
    """The Kroger API did not respond within the client's timeout."""

    error_type = "timeout"

    def __init__(self, method: str, url: str, timeout: Optional[float], reason: str, request: Any = None,
                 request_sent: Optional[bool] = None):
        self.timeout = timeout
        super().__init__(
            method,
            url,
            reason,
            request=request,
            message=(
                f"The Kroger API did not respond within {timeout} seconds for {method} {_display_url(url)} "
                f"({reason}). Set a different limit with KrogerAPI(timeout=...)."
            ),
            request_sent=request_sent,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "timeout": self.timeout}


def _parse_error_body(response: requests.Response) -> Tuple[Any, Optional[str], Optional[str]]:
    """Return (body, kroger_code, kroger_message) from an error response.

    The Kroger API uses several error body shapes, depending on which layer
    rejected the request (observed live, 2026-10-21):

    - ``{"errors": {"code", "reason", "timestamp"}}``: Products and Locations 4xx/5xx
    - ``{"code", "reason", "timestamp"}``: 403 from the identity and cart endpoints
    - ``{"error", "error_description"}``: the OAuth2 token endpoint
    - ``{"message": "Unauthorized"}``: the API gateway's 401
    - empty body: most 404s and every HEAD response
    """
    if not response.content:
        return None, None, None
    try:
        body = response.json()
    except ValueError:
        text = response.text[:_MAX_BODY_CHARS]
        content_type = response.headers.get("Content-Type", "")
        # An HTML error page (from the CDN, for example) is noise as a message.
        message = None if "html" in content_type.lower() else (text.strip() or None)
        return text, None, message

    detail = body
    if isinstance(body, dict) and "errors" in body:
        detail = body["errors"]
        if isinstance(detail, list):
            detail = detail[0] if detail else {}
    if not isinstance(detail, dict):
        return body, None, None

    code = detail.get("code") or detail.get("error")
    message = detail.get("reason") or detail.get("error_description") or detail.get("message")
    return body, (str(code) if code is not None else None), (str(message) if message is not None else None)


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    """Seconds to wait, from a Retry-After header given as seconds or as an HTTP date."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, when.timestamp() - time.time())


def _standard_phrase(status_code: int) -> str:
    try:
        return http.HTTPStatus(status_code).phrase
    except ValueError:
        return ""


def _www_authenticate_error(header: Optional[str]) -> Optional[str]:
    """The error="..." value of a WWW-Authenticate header, such as invalid_token."""
    if not header or "error=" not in header:
        return None
    value = header.split("error=", 1)[1].split(",", 1)[0].strip()
    return value.strip('"') or None


class APIStatusError(KrogerAPIError, requests.exceptions.HTTPError):
    """The Kroger API answered with a non-2xx status.

    Attributes:
        status_code: HTTP status, for example 400.
        status_text: HTTP reason phrase, for example "Bad Request".
        method: HTTP method of the request.
        url: Full request URL, including the query string. It holds no
            credentials: the access token travels in a header.
        kroger_code: Kroger's error code, for example ``PRODUCT-2017`` or,
            from the token endpoint, an OAuth2 code such as ``invalid_scope``.
        kroger_message: Kroger's explanation, for example "Field 'term' must
            have three or more characters and less than 128 characters".
        body: The parsed JSON body, the raw text, or None when the body is empty.
        correlation_id: The ``X-Correlation-Id`` response header. Quote it
            when you report a problem to Kroger.
        retry_after: Seconds to wait, from a ``Retry-After`` header, if sent.
        hint: What usually causes this error and how to fix it, if known.
        response: The ``requests.Response`` (inherited from HTTPError).
    """

    error_type = "api_error"

    @property
    def outcome_unknown(self) -> bool:
        # A 4xx means the request was refused. A 5xx, often from a gateway
        # that timed out, can come after the request was processed.
        return self.status_code >= 500 and _changes_data(self.method, self.url)

    def __init__(self, response: requests.Response, note: Optional[str] = None):
        request = response.request
        self.status_code = response.status_code
        # HTTP/2 responses carry no reason phrase; use the standard one.
        self.status_text = response.reason or _standard_phrase(response.status_code)
        self.method = getattr(request, "method", None) or "?"
        self.url = response.url or getattr(request, "url", None) or ""
        self.body, self.kroger_code, self.kroger_message = _parse_error_body(response)
        www_auth_error = _www_authenticate_error(response.headers.get("WWW-Authenticate"))
        if self.kroger_code is None and www_auth_error:
            self.kroger_code = www_auth_error
        self.correlation_id = response.headers.get("X-Correlation-Id")
        self.retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        self.note = note
        self.hint = _hint_for(self)
        super().__init__(self._format(), response=response, request=request)

    def _format(self) -> str:
        head = f"{self.status_code} {self.status_text}".strip()
        detail = self.kroger_message or "(no error message in the response body)"
        if self.kroger_code:
            detail = f"{detail} [{self.kroger_code}]"
        lines = [
            f"Kroger API error {head}: {detail}",
            f"  request: {self.method} {_display_url(self.url)}",
        ]
        if self.correlation_id:
            lines.append(f"  correlation id: {self.correlation_id}")
        if self.retry_after is not None:
            lines.append(f"  retry after: {self.retry_after:g} seconds")
        if self.note:
            lines.append(f"  note: {self.note}")
        if self.hint:
            lines.append(f"  hint: {self.hint}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "status_code": self.status_code,
            "status_text": self.status_text,
            "kroger_code": self.kroger_code,
            "kroger_message": self.kroger_message,
            "method": self.method,
            "url": self.url,
            "correlation_id": self.correlation_id,
            "retry_after": self.retry_after,
            "note": self.note,
            "hint": self.hint,
            "response_body": _json_safe(self.body),
        }


class BadRequestError(APIStatusError):
    """400: the API rejected a parameter. ``kroger_message`` usually names it."""

    error_type = "bad_request"


class AuthenticationError(APIStatusError):
    """401: the access token, or at the token endpoint the client credentials, were rejected."""

    error_type = "authentication_error"


class PermissionDeniedError(APIStatusError):
    """403: the token is valid but may not use this endpoint (wrong token type or scope)."""

    error_type = "permission_denied"


class NotFoundError(APIStatusError):
    """404: the location, chain, department, or other resource does not exist."""

    error_type = "not_found"


class RateLimitError(APIStatusError):
    """429: the rate limit for this endpoint is used up."""

    error_type = "rate_limited"


class InternalServerError(APIStatusError):
    """5xx: the Kroger API failed to handle a request that may be valid."""

    error_type = "server_error"


_STATUS_CLASSES = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    429: RateLimitError,
}


def error_from_response(response: requests.Response, note: Optional[str] = None) -> APIStatusError:
    """Build the APIStatusError subclass that matches a non-2xx response."""
    status = response.status_code
    cls = _STATUS_CLASSES.get(status) or (InternalServerError if status >= 500 else APIStatusError)
    return cls(response, note=note)


class InvalidResponseError(KrogerAPIError):
    """A 2xx response whose body is not the JSON the endpoint documents."""

    error_type = "invalid_response"

    def __init__(self, response: requests.Response):
        self.status_code = response.status_code
        self.method = getattr(response.request, "method", None) or "?"
        self.url = response.url or ""
        self.correlation_id = response.headers.get("X-Correlation-Id")
        self.body = response.text[:_MAX_BODY_CHARS]
        snippet = self.body[:200].replace("\n", " ")
        message = (
            f"Kroger API returned {self.status_code} with a body that is not valid JSON for "
            f"{self.method} {_display_url(self.url)}: {snippet!r}"
        )
        if self.correlation_id:
            message += f" (correlation id {self.correlation_id})"
        if self.outcome_unknown:
            message += ". The request succeeded, so do not resend it."
        super().__init__(message)

    @property
    def outcome_unknown(self) -> bool:
        # The 2xx status says the request was processed, so resending repeats it
        return _changes_data(self.method, self.url)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "status_code": self.status_code,
            "method": self.method,
            "url": self.url,
            "correlation_id": self.correlation_id,
            "response_body": self.body,
        }


def _hint_for(error: APIStatusError) -> Optional[str]:
    """Known causes and fixes for an API error, or None if there is nothing to add."""
    status = error.status_code
    path = urlsplit(error.url).path
    code = (error.kroger_code or "").lower()
    message = (error.kroger_message or "").lower()

    if path == TOKEN_ENDPOINT:
        if status == 401:
            return "Kroger rejected the app credentials. Check KROGER_CLIENT_ID and KROGER_CLIENT_SECRET."
        if code == "invalid_scope":
            return (
                "Request only scopes that are enabled for this app in the Kroger Developer Portal, "
                "such as product.compact, cart.basic:write, or profile.compact."
            )
        if "refresh_token" in message:
            return "The refresh token is invalid or expired. Sign the user in again with the authorization-code flow."
        if "code" in message:
            return (
                "The authorization code is invalid, expired, or already used, or the redirect_uri or "
                "PKCE code_verifier does not match the authorization request. Start the sign-in again."
            )
        return None

    if status == 400:
        if message == "invalid parameters" and path.startswith("/v1/products"):
            return (
                "The API did not name the parameter. Known causes: a filter.term of more than eight "
                "space-separated words (repeated spaces count as extra words), or a malformed "
                "filter.productId list."
            )
        return None
    if status == 401:
        return (
            "The access token is missing, invalid, or expired. Request a new client-credentials token, "
            "refresh the user token, or sign the user in again."
        )
    if status == 403:
        if path.startswith(("/v1/cart", "/v1/identity")):
            return (
                "This endpoint needs a user access token from the authorization-code flow, with the "
                "cart.basic:write scope for the cart or profile.compact for the profile. "
                "A client-credentials token is always refused here."
            )
        return "The access token does not carry the scope this endpoint requires, such as product.compact for products."
    if status == 404:
        if path.startswith("/v1/locations/"):
            return "No store has this locationId. Find valid IDs with a location search."
        if path.startswith("/v1/products/"):
            return "No product has this productId or UPC. Find products with a product search."
        if path.startswith("/v1/chains/"):
            return "No chain has this name. Get the valid names from the chains list."
        if path.startswith("/v1/departments/"):
            return "No department has this ID. Get the valid IDs from the departments list."
        return "The endpoint or resource does not exist."
    if status == 429:
        hint = "The rate limit for this endpoint is used up. Kroger's limits are per day, so an immediate retry fails too."
        if error.retry_after is not None:
            hint += f" The API asked for a wait of {error.retry_after:g} seconds."
        return hint
    if status >= 500:
        if error.outcome_unknown:
            return (
                "The Kroger API failed while handling the request, and it may have been processed anyway. "
                "Check its effect (for a cart add, the cart in the Kroger app or website) before resending it. "
                "Quote the correlation id if you report the problem."
            )
        return (
            "The Kroger API failed to handle the request. A later retry may succeed. "
            "Quote the correlation id if you report the problem."
        )
    return None
