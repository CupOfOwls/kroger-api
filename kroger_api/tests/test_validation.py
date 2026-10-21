"""Parameter validation: bad arguments raise InvalidParameterError before any request is sent."""
import time

import pytest

from kroger_api import KrogerAPI
from kroger_api.errors import InvalidParameterError

BASE = "https://api.kroger.com"


@pytest.fixture(autouse=True)
def token_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KROGER_TOKEN_DIR", str(tmp_path))


@pytest.fixture
def kroger():
    api = KrogerAPI(client_id="id", client_secret="secret")
    api.client.token_info = {"access_token": "valid", "expires_at": time.time() + 1800}
    return api


# Each case: (callable taking the API, param named in the error, fragment of the requirement)
INVALID_CALLS = [
    (lambda k: k.product.search_products(), "term", "needs a term or a product_id"),
    (lambda k: k.product.search_products(term="ab"), "term", "at least 3 characters"),
    (lambda k: k.product.search_products(term="  ab  "), "term", "at least 3 characters"),
    (lambda k: k.product.search_products(term="one two three four five six seven eight nine"), "term", "at most 8 words"),
    (lambda k: k.product.search_products(term="a  b c d e f g h"), "term", "each extra space counts"),
    (lambda k: k.product.search_products(term="milk", limit=0), "limit", "from 1 to 50"),
    (lambda k: k.product.search_products(term="milk", limit=51), "limit", "from 1 to 50"),
    (lambda k: k.product.search_products(term="milk", limit=True), "limit", "must be an integer"),
    (lambda k: k.product.search_products(term="milk", start=251), "start", "from 0 to 250"),
    (lambda k: k.product.search_products(term="milk", location_id="123"), "location_id", "8-character"),
    (lambda k: k.product.search_products(term="milk", fulfillment="delivery"), "fulfillment", "'delivery' is not one of them"),
    (lambda k: k.product.search_products(term="milk", fulfillment="CSP"), "fulfillment", "use 'csp'"),
    (lambda k: k.product.search_products(term="milk", fulfillment="csp,"), "fulfillment", "'' is not one of them"),
    (lambda k: k.product.search_products(product_id="123"), "product_id", "13-digit"),
    (lambda k: k.product.search_products(term="milk", brand=""), "brand", "non-empty"),
    (lambda k: k.product.get_product("abcdefghijklm"), "product_id", "13-digit"),
    (lambda k: k.product.get_product("0001111041700", location_id=1400513), "location_id", "8-character"),
    (lambda k: k.location.search_locations(zip_code="4520"), "zip_code", "5-digit"),
    (lambda k: k.location.search_locations(zip_code="45202-1234"), "zip_code", "ZIP+4 is not accepted"),
    (lambda k: k.location.search_locations(zip_code="45202", radius_in_miles=0), "radius_in_miles", "from 1 to 100"),
    (lambda k: k.location.search_locations(zip_code="45202", limit=0), "limit", "from 1 to 200"),
    (lambda k: k.location.search_locations(zip_code="45202", limit=201), "limit", "from 1 to 200"),
    (lambda k: k.location.search_locations(lat_long="abc"), "lat_long", "latitude,longitude"),
    (lambda k: k.location.search_locations(lat_long="91,-84.5"), "lat_long", "-90 to 90"),
    (lambda k: k.location.search_locations(lat="x"), "lat", "decimal number"),
    (lambda k: k.location.search_locations(lon="-181"), "lon", "-180 to 180"),
    (lambda k: k.location.search_locations(zip_code="45202", department="ZZZ"), "department", "2-character"),
    (lambda k: k.location.search_locations(location_id="01400513,123"), "location_id", "'123' is not"),
    (lambda k: k.location.get_location("123"), "location_id", "8-character"),
    (lambda k: k.location.location_exists("123"), "location_id", "8-character"),
    (lambda k: k.location.get_chain(""), "name", "non-empty"),
    (lambda k: k.location.get_department("ZZZ"), "department_id", "2-character"),
    (lambda k: k.location.department_exists("ZZZ"), "department_id", "2-character"),
    (lambda k: k.cart.add_to_cart([]), "items", "non-empty list"),
    (lambda k: k.cart.add_to_cart([{"product_id": "0001111041700", "quantity": 1}]), "items[0].upc", "names the product identifier 'upc'"),
    (lambda k: k.cart.add_to_cart([{"upc": "x", "quantity": 1}]), "items[0].upc", "13-digit"),
    (lambda k: k.cart.add_to_cart([{"upc": "0001111041700", "quantity": 0}]), "items[0].quantity", "1 or more"),
    (lambda k: k.cart.add_to_cart([{"upc": "0001111041700"}]), "items[0].quantity", "is required"),
    (lambda k: k.cart.add_to_cart([{"upc": "0001111041700", "quantity": 1},
                                   {"upc": "0001111041700", "quantity": 1, "modality": "pickup"}]),
     "items[1].modality", "use 'PICKUP'"),
    (lambda k: k.authorization.get_token_with_client_credentials(""), "scope", "non-empty"),
]


@pytest.mark.parametrize("call, param, fragment", INVALID_CALLS)
def test_invalid_arguments_raise_before_sending(kroger, requests_mock, call, param, fragment):
    with pytest.raises(InvalidParameterError) as excinfo:
        call(kroger)
    error = excinfo.value
    assert error.param == param
    assert fragment in error.requirement
    assert "No request was sent" in str(error)
    assert isinstance(error, ValueError)
    assert error.to_dict()["param"] == param
    assert requests_mock.call_count == 0


def test_valid_product_filters_reach_the_query(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/products", json={"data": []})
    kroger.product.search_products(term="milk  bread", location_id="01400513", fulfillment="csp,ais",
                                   brand="Kroger|Simple Truth", start=0, limit="5")
    query = requests_mock.request_history[0].qs
    assert query["filter.term"] == ["milk  bread"]
    assert query["filter.fulfillment"] == ["csp,ais"]
    assert query["filter.start"] == ["0"]  # 0 is valid and is now sent, not dropped
    assert query["filter.limit"] == ["5"]


def test_eight_single_spaced_words_are_allowed(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/products", json={"data": []})
    kroger.product.search_products(term="red green blue white black pink gray milk")
    assert requests_mock.call_count == 1


def test_chain_names_are_url_quoted(kroger, requests_mock):
    requests_mock.get(f"{BASE}/v1/chains/LOAF%20%27N%20JUG", json={"data": {"name": "LOAF 'N JUG"}})
    assert kroger.location.get_chain("LOAF 'N JUG")["data"]["name"] == "LOAF 'N JUG"


def test_exists_checks_return_false_on_404(kroger, requests_mock):
    requests_mock.head(f"{BASE}/v1/locations/99999999", status_code=404)
    requests_mock.head(f"{BASE}/v1/chains/NOTACHAIN", status_code=404)
    requests_mock.head(f"{BASE}/v1/departments/ZZ", status_code=404)
    requests_mock.head(f"{BASE}/v1/locations/01400513", status_code=204)
    assert kroger.location.location_exists("99999999") is False
    assert kroger.location.chain_exists("NOTACHAIN") is False
    assert kroger.location.department_exists("ZZ") is False
    assert kroger.location.location_exists("01400513") is True


def test_valid_cart_items_are_sent(kroger, requests_mock):
    requests_mock.put(f"{BASE}/v1/cart/add", status_code=204)
    assert kroger.cart.add_to_cart([{"upc": "0001111041700", "quantity": 2, "modality": "DELIVERY"},
                                    {"upc": "0001111041700", "quantity": 1}]) is None
    assert requests_mock.request_history[0].json()["items"][0]["quantity"] == 2
