"""
Parameter checks that run before a request is sent.

The constraints come from the Kroger Public API OpenAPI specifications
(Products 1.3.0, Location 1.2.3, Cart 1.2.3) and were confirmed against live
responses on 2026-10-21. Checking them in the client matters most where the
API does not reject bad input: an unknown or wrongly cased fulfillment type, a
location search limit or radius of 0, and a product search limit of 0 (which
older versions of this client dropped) all return 200 with the filter
silently ignored.

The constants are public so that other packages, such as kroger-mcp, can
publish the same limits in their own schemas.
"""

import re
from typing import Any, Dict, List

from kroger_api.errors import InvalidParameterError

# Anchored so that JSON Schema and pydantic, which search for a match, check
# the whole value too. Python code matches them with re.fullmatch, because
# re.match lets "$" match before a trailing newline.
LOCATION_ID_PATTERN = r"^[A-Za-z0-9]{8}$"
PRODUCT_ID_PATTERN = r"^[0-9]{13}$"
DEPARTMENT_ID_PATTERN = r"^[A-Za-z0-9]{2}$"
ZIP_CODE_PATTERN = r"^[0-9]{5}$"

PRODUCT_TERM_MIN_LENGTH = 3
PRODUCT_TERM_MAX_WORDS = 8
PRODUCT_LIMIT_MIN, PRODUCT_LIMIT_MAX = 1, 50
# The API's message says 1-250, but it accepts 0 (skip nothing).
PRODUCT_START_MIN, PRODUCT_START_MAX = 0, 250

LOCATION_RADIUS_MIN, LOCATION_RADIUS_MAX = 1, 100
LOCATION_LIMIT_MIN, LOCATION_LIMIT_MAX = 1, 200

# Case-sensitive. Any other value is silently ignored by the API.
FULFILLMENT_TYPES = {
    "ais": "available in store",
    "csp": "curbside pickup",
    "dth": "delivery to home",
    "sth": "ship to home",
}
CART_MODALITIES = ("DELIVERY", "PICKUP")


def check_int(param: str, value: Any, minimum: int, maximum: int) -> int:
    """Return value as an int within [minimum, maximum]. Digit strings are accepted."""
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidParameterError(param, value, f"must be an integer from {minimum} to {maximum}")
    if not minimum <= value <= maximum:
        raise InvalidParameterError(param, value, f"must be from {minimum} to {maximum}")
    return value


def check_pattern(param: str, value: Any, pattern: str, description: str) -> str:
    """Return value as a str that matches pattern. Integers are converted to str first."""
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise InvalidParameterError(param, value, f"must be {description}")
    return value


def check_list(param: str, value: Any, pattern: str, description: str) -> str:
    """Validate a comma-separated list in which every item matches pattern."""
    if not isinstance(value, str) or not value:
        raise InvalidParameterError(param, value, f"must be a comma-separated list of {description}")
    for item in value.split(","):
        if not re.fullmatch(pattern, item):
            raise InvalidParameterError(
                param, value, f"must be a comma-separated list of {description}; {item!r} is not"
            )
    return value


def check_non_empty(param: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidParameterError(param, value, "must be a non-empty string")
    return value


def location_id(value: Any, param: str = "location_id") -> str:
    return check_pattern(param, value, LOCATION_ID_PATTERN, "an 8-character store locationId such as '01400513'")


def location_id_list(value: Any, param: str = "location_id") -> str:
    return check_list(param, value, LOCATION_ID_PATTERN, "8-character store locationIds")


def product_id(value: Any, param: str = "product_id") -> str:
    return check_pattern(param, value, PRODUCT_ID_PATTERN, "a 13-digit productId or UPC such as '0001111041700'")


def product_id_list(value: Any, param: str = "product_id") -> str:
    return check_list(param, value, PRODUCT_ID_PATTERN, "13-digit productIds")


def department_id(value: Any, param: str = "department_id") -> str:
    return check_pattern(param, value, DEPARTMENT_ID_PATTERN, "a 2-character departmentId such as '09' or '0A'")


def department_id_list(value: Any, param: str = "department") -> str:
    return check_list(param, value, DEPARTMENT_ID_PATTERN, "2-character departmentIds")


def zip_code(value: Any, param: str = "zip_code") -> str:
    return check_pattern(param, value, ZIP_CODE_PATTERN, "a 5-digit ZIP code (ZIP+4 is not accepted)")


def search_term(value: Any, param: str = "term") -> str:
    if not isinstance(value, str) or len(value.strip()) < PRODUCT_TERM_MIN_LENGTH:
        raise InvalidParameterError(
            param, value, f"must have at least {PRODUCT_TERM_MIN_LENGTH} characters, not counting leading and trailing spaces"
        )
    # The API splits on single spaces, so "milk  bread" counts as three words.
    words = value.strip().split(" ")
    if len(words) > PRODUCT_TERM_MAX_WORDS:
        raise InvalidParameterError(
            param,
            value,
            f"must have at most {PRODUCT_TERM_MAX_WORDS} words; it has {len(words)} when split on single "
            f"spaces (each extra space counts as a word)",
        )
    return value


def fulfillment(value: Any, param: str = "fulfillment") -> str:
    valid = ", ".join(f"'{k}' ({v})" for k, v in FULFILLMENT_TYPES.items())
    if not isinstance(value, str) or not value:
        raise InvalidParameterError(param, value, f"must be a comma-separated list of: {valid}")
    for item in value.split(","):
        if item not in FULFILLMENT_TYPES:
            requirement = f"must be a comma-separated list of: {valid}. {item!r} is not one of them"
            if item.lower() in FULFILLMENT_TYPES:
                requirement += f" (values are case-sensitive: use {item.lower()!r})"
            raise InvalidParameterError(param, value, requirement)
    return value


def modality(value: Any, param: str = "modality") -> str:
    if value not in CART_MODALITIES:
        requirement = f"must be one of {', '.join(CART_MODALITIES)}"
        if isinstance(value, str) and value.upper() in CART_MODALITIES:
            requirement += f" (values are case-sensitive: use {value.upper()!r})"
        raise InvalidParameterError(param, value, requirement)
    return value


def coordinate(value: Any, param: str, limit: float) -> str:
    """A latitude (limit 90) or longitude (limit 180) as the decimal string the API expects."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise InvalidParameterError(param, value, "must be a decimal number") from None
    if isinstance(value, bool) or not -limit <= number <= limit:
        raise InvalidParameterError(param, value, f"must be a decimal number from -{limit:g} to {limit:g}")
    return str(value)


def lat_long(value: Any, param: str = "lat_long") -> str:
    parts = value.split(",") if isinstance(value, str) else []
    if len(parts) != 2:
        raise InvalidParameterError(param, value, "must be 'latitude,longitude', for example '39.306346,-84.278902'")
    coordinate(parts[0].strip(), param, 90)
    coordinate(parts[1].strip(), param, 180)
    return value


def cart_items(items: Any, param: str = "items") -> List[Dict[str, Any]]:
    """Validate the item list for PUT /v1/cart/add, and return it as a list."""
    if not isinstance(items, (list, tuple)) or not items:
        raise InvalidParameterError(param, items, "must be a non-empty list of {'upc', 'quantity', 'modality'} dicts")
    for index, item in enumerate(items):
        where = f"{param}[{index}]"
        if not isinstance(item, dict):
            raise InvalidParameterError(where, item, "must be a dict with 'upc', 'quantity', and optional 'modality'")
        if "upc" not in item:
            requirement = "is required"
            if "product_id" in item or "productId" in item:
                requirement += " (the cart API names the product identifier 'upc')"
            raise InvalidParameterError(f"{where}.upc", None, requirement)
        product_id(item["upc"], f"{where}.upc")
        if "quantity" not in item:
            raise InvalidParameterError(f"{where}.quantity", None, "is required")
        quantity = item["quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise InvalidParameterError(f"{where}.quantity", quantity, "must be an integer of 1 or more")
        if item.get("modality") is not None:
            modality(item["modality"], f"{where}.modality")
    return list(items)
