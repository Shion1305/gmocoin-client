import hashlib
import hmac
import json

import httpx
import pytest

import gmocoin_client.client as client_module
from gmocoin_client import Client
from gmocoin_client.errors import GmoCoinApiError, GmoCoinHttpError


def _sign(secret: str, timestamp: str, method: str, path: str, body: str) -> str:
    text = f"{timestamp}{method}{path}{body}"
    return hmac.new(secret.encode("ascii"), text.encode("ascii"), hashlib.sha256).hexdigest()


def test_public_ticker_query(httpx_mock):
    # Validates public ticker query is built with the symbol parameter.
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/public/v1/ticker"
        assert request.url.params["symbol"] == "BTC"
        return httpx.Response(200, json={"status": 0, "data": []})

    httpx_mock.add_callback(handler)

    client = Client()
    client.get_ticker("BTC")


def test_private_get_signing(httpx_mock, monkeypatch):
    # Ensures private GET requests are signed with timestamp and path only.
    timestamp = "1700000000000"
    monkeypatch.setattr(client_module, "_timestamp_ms", lambda: timestamp)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/private/v1/account/margin"
        assert request.headers["API-KEY"] == "key"
        assert request.headers["API-TIMESTAMP"] == timestamp
        expected = _sign("secret", timestamp, "GET", "/v1/account/margin", "")
        assert request.headers["API-SIGN"] == expected
        return httpx.Response(200, json={"status": 0, "data": {}})

    httpx_mock.add_callback(handler)

    client = Client(api_key="key", api_secret="secret")
    client.get_margin()


def test_private_post_signing_with_body(httpx_mock, monkeypatch):
    # Ensures private POST requests are signed including the JSON body.
    timestamp = "1700000000000"
    monkeypatch.setattr(client_module, "_timestamp_ms", lambda: timestamp)

    expected_body = json.dumps(
        {
            "symbol": "BTC_JPY",
            "side": "BUY",
            "executionType": "LIMIT",
            "timeInForce": "FAS",
            "price": "430001",
            "size": "0.02",
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/private/v1/order"
        assert request.headers["Content-Type"] == "application/json"
        assert request.content.decode("utf-8") == expected_body
        expected = _sign("secret", timestamp, "POST", "/v1/order", expected_body)
        assert request.headers["API-SIGN"] == expected
        return httpx.Response(200, json={"status": 0, "data": "12345"})

    httpx_mock.add_callback(handler)

    client = Client(api_key="key", api_secret="secret")
    client.create_order(
        symbol="BTC_JPY",
        side="BUY",
        execution_type="LIMIT",
        time_in_force="FAS",
        price="430001",
        size="0.02",
    )


def test_ws_auth_extend_signing_without_body(httpx_mock, monkeypatch):
    # Ensures ws-auth extend signs only timestamp+method+path.
    timestamp = "1700000000000"
    monkeypatch.setattr(client_module, "_timestamp_ms", lambda: timestamp)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/private/v1/ws-auth"
        assert request.content.decode("utf-8") == json.dumps({"token": "token123"}, separators=(",", ":"))
        expected = _sign("secret", timestamp, "PUT", "/v1/ws-auth", "")
        assert request.headers["API-SIGN"] == expected
        return httpx.Response(200, json={"status": 0})

    httpx_mock.add_callback(handler)

    client = Client(api_key="key", api_secret="secret")
    client.ws_auth_extend("token123")


def test_api_error_raises(httpx_mock):
    # Raises API error when status indicates failure.
    httpx_mock.add_response(
        method="GET",
        url="https://api.coin.z.com/public/v1/status",
        json={
            "status": 5,
            "messages": [{"message_code": "ERR-5106", "message_string": "Invalid"}],
        },
    )
    client = Client()
    with pytest.raises(GmoCoinApiError):
        client.get_status()


def test_http_error_raises(httpx_mock):
    # Raises HTTP error for non-success HTTP status.
    httpx_mock.add_response(
        method="GET",
        url="https://api.coin.z.com/public/v1/status",
        status_code=500,
        json={"status": 5},
    )
    client = Client()
    with pytest.raises(GmoCoinHttpError):
        client.get_status()


def test_private_call_requires_keys():
    # Enforces that private endpoints require API credentials.
    client = Client()
    with pytest.raises(ValueError):
        client.get_assets()
