from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Iterable, Mapping

import httpx
from pydantic import BaseModel

from .errors import GmoCoinApiError, GmoCoinHttpError
from .models import (
    ActiveOrdersData,
    APIResponse,
    AssetItem,
    CryptoHistoryItem,
    ExecutionsData,
    KlineItem,
    LatestExecutionsData,
    MarginData,
    OpenPositionsData,
    OrderbookData,
    OrdersData,
    PositionSummaryData,
    ServiceStatusData,
    SymbolRule,
    TickerItem,
    TradesData,
    TradingVolumeData,
    FiatHistoryItem,
)

PUBLIC_BASE_URL = "https://api.coin.z.com/public"
PRIVATE_BASE_URL = "https://api.coin.z.com/private"


def _timestamp_ms() -> str:
    return str(int(time.time() * 1000))


def _prune_params(params: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _comma_list(values: Iterable[Any] | str | int) -> str:
    if isinstance(values, (str, int)):
        return str(values)
    return ",".join(str(value) for value in values)


class GmoCoinClient:
    def __init__(
            self,
            api_key: str | None = None,
            api_secret: str | None = None,
            *,
            public_base_url: str = PUBLIC_BASE_URL,
            private_base_url: str = PRIVATE_BASE_URL,
            timeout: float | None = 10.0,
            raise_on_error: bool = True,
            client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.public_base_url = public_base_url.rstrip("/")
        self.private_base_url = private_base_url.rstrip("/")
        self.raise_on_error = raise_on_error
        self._client = client or httpx.Client(timeout=timeout)

    def __enter__(self) -> "GmoCoinClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @classmethod
    def from_env(
            cls,
            *,
            api_key_env: str = "GMO_API_KEY",
            api_secret_env: str = "GMO_SECRET_KEY",
            **kwargs: Any,
    ) -> "GmoCoinClient":
        return cls(
            api_key=os.getenv(api_key_env),
            api_secret=os.getenv(api_secret_env),
            **kwargs,
        )

    def close(self) -> None:
        self._client.close()

    def _ensure_private_auth(self) -> None:
        if not self.api_key or not self.api_secret:
            raise ValueError("api_key and api_secret are required for private API calls")

    def _sign(self, timestamp: str, method: str, path: str, body: str) -> str:
        text = f"{timestamp}{method}{path}{body}"
        return hmac.new(
            self.api_secret.encode("ascii"),
            text.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

    def _private_headers(self, method: str, path: str, body: str, sign_body: bool) -> dict[str, str]:
        self._ensure_private_auth()
        timestamp = _timestamp_ms()
        signature_body = body if sign_body else ""
        sign = self._sign(timestamp, method, path, signature_body)
        return {
            "API-KEY": self.api_key,
            "API-TIMESTAMP": timestamp,
            "API-SIGN": sign,
        }

    def _handle_response(self, response: httpx.Response) -> Any:
        data: Any = None
        try:
            data = response.json()
        except ValueError:
            if self.raise_on_error:
                raise GmoCoinHttpError(
                    response.status_code,
                    f"Non-JSON response (status {response.status_code})",
                ) from None
            return response.text

        if self.raise_on_error:
            if response.is_error:
                raise GmoCoinHttpError(response.status_code, "HTTP request failed", data)
            if isinstance(data, dict) and data.get("status") not in (None, 0):
                raise GmoCoinApiError(data.get("status"), data.get("messages"), data)

        return data

    def _request(
        self,
        method: str,
        path: str,
        *,
        private: bool = False,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        sign_body: bool | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> Any:
        base_url = self.private_base_url if private else self.public_base_url
        url = f"{base_url}{path}"
        headers: dict[str, str] = {}
        body = ""
        if json_body is not None:
            body = json.dumps(json_body, separators=(",", ":"), ensure_ascii=False)
            headers["Content-Type"] = "application/json"

        if private:
            if sign_body is None:
                sign_body = method.upper() != "GET"
            headers.update(self._private_headers(method.upper(), path, body, sign_body))

        response = self._client.request(
            method=method,
            url=url,
            params=params,
            content=body if body else None,
            headers=headers or None,
        )
        data = self._handle_response(response)
        if response_model is not None:
            return response_model.model_validate(data)
        return data

    # Public API methods
    def get_status(self) -> APIResponse[ServiceStatusData]:
        return self._request("GET", "/v1/status", response_model=APIResponse[ServiceStatusData])

    def get_ticker(self, symbol: str | None = None) -> APIResponse[list[TickerItem]]:
        params = _prune_params({"symbol": symbol})
        return self._request(
            "GET",
            "/v1/ticker",
            params=params,
            response_model=APIResponse[list[TickerItem]],
        )

    def get_orderbooks(self, symbol: str) -> APIResponse[OrderbookData]:
        return self._request(
            "GET",
            "/v1/orderbooks",
            params={"symbol": symbol},
            response_model=APIResponse[OrderbookData],
        )

    def get_trades(self, symbol: str, *, page: int | None = None, count: int | None = None) -> APIResponse[TradesData]:
        params = _prune_params({"symbol": symbol, "page": page, "count": count})
        return self._request(
            "GET",
            "/v1/trades",
            params=params,
            response_model=APIResponse[TradesData],
        )

    def get_klines(self, symbol: str, interval: str, date: str) -> APIResponse[list[KlineItem]]:
        params = {"symbol": symbol, "interval": interval, "date": date}
        return self._request(
            "GET",
            "/v1/klines",
            params=params,
            response_model=APIResponse[list[KlineItem]],
        )

    def get_symbols(self) -> APIResponse[list[SymbolRule]]:
        return self._request("GET", "/v1/symbols", response_model=APIResponse[list[SymbolRule]])

    # Private API methods (Account)
    def get_margin(self) -> APIResponse[MarginData]:
        return self._request(
            "GET",
            "/v1/account/margin",
            private=True,
            response_model=APIResponse[MarginData],
        )

    def get_assets(self) -> APIResponse[list[AssetItem]]:
        return self._request(
            "GET",
            "/v1/account/assets",
            private=True,
            response_model=APIResponse[list[AssetItem]],
        )

    def get_trading_volume(self) -> APIResponse[TradingVolumeData]:
        return self._request(
            "GET",
            "/v1/account/tradingVolume",
            private=True,
            response_model=APIResponse[TradingVolumeData],
        )

    def get_fiat_deposits(
            self,
            from_timestamp: str,
            *,
            to_timestamp: str | None = None,
    ) -> APIResponse[list[FiatHistoryItem]]:
        params = _prune_params({"fromTimestamp": from_timestamp, "toTimestamp": to_timestamp})
        return self._request(
            "GET",
            "/v1/account/fiatDeposit/history",
            private=True,
            params=params,
            response_model=APIResponse[list[FiatHistoryItem]],
        )

    def get_fiat_withdrawals(
            self,
            from_timestamp: str,
            *,
            to_timestamp: str | None = None,
    ) -> APIResponse[list[FiatHistoryItem]]:
        params = _prune_params({"fromTimestamp": from_timestamp, "toTimestamp": to_timestamp})
        return self._request(
            "GET",
            "/v1/account/fiatWithdrawal/history",
            private=True,
            params=params,
            response_model=APIResponse[list[FiatHistoryItem]],
        )

    def get_crypto_deposits(
            self,
            symbol: str,
            from_timestamp: str,
            *,
            to_timestamp: str | None = None,
    ) -> APIResponse[list[CryptoHistoryItem]]:
        params = _prune_params(
            {"symbol": symbol, "fromTimestamp": from_timestamp, "toTimestamp": to_timestamp},
        )
        return self._request(
            "GET",
            "/v1/account/deposit/history",
            private=True,
            params=params,
            response_model=APIResponse[list[CryptoHistoryItem]],
        )

    def get_crypto_withdrawals(
            self,
            symbol: str,
            from_timestamp: str,
            *,
            to_timestamp: str | None = None,
    ) -> APIResponse[list[CryptoHistoryItem]]:
        params = _prune_params(
            {"symbol": symbol, "fromTimestamp": from_timestamp, "toTimestamp": to_timestamp},
        )
        return self._request(
            "GET",
            "/v1/account/withdrawal/history",
            private=True,
            params=params,
            response_model=APIResponse[list[CryptoHistoryItem]],
        )

    # Private API methods (Orders)
    def get_orders(self, order_ids: Iterable[Any] | str | int) -> APIResponse[OrdersData]:
        params = {"orderId": _comma_list(order_ids)}
        return self._request(
            "GET",
            "/v1/orders",
            private=True,
            params=params,
            response_model=APIResponse[OrdersData],
        )

    def get_active_orders(
            self,
            symbol: str,
            *,
            page: int | None = None,
            count: int | None = None,
    ) -> APIResponse[ActiveOrdersData]:
        params = _prune_params({"symbol": symbol, "page": page, "count": count})
        return self._request(
            "GET",
            "/v1/activeOrders",
            private=True,
            params=params,
            response_model=APIResponse[ActiveOrdersData],
        )

    def get_executions(
            self,
            *,
            order_id: int | None = None,
            execution_id: Iterable[Any] | str | int | None = None,
    ) -> APIResponse[ExecutionsData]:
        if order_id is None and execution_id is None:
            raise ValueError("order_id or execution_id is required")
        params = _prune_params(
            {
                "orderId": order_id,
                "executionId": _comma_list(execution_id) if execution_id is not None else None,
            },
        )
        return self._request(
            "GET",
            "/v1/executions",
            private=True,
            params=params,
            response_model=APIResponse[ExecutionsData],
        )

    def get_latest_executions(
            self,
            symbol: str,
            *,
            page: int | None = None,
            count: int | None = None,
    ) -> APIResponse[LatestExecutionsData]:
        params = _prune_params({"symbol": symbol, "page": page, "count": count})
        return self._request(
            "GET",
            "/v1/latestExecutions",
            private=True,
            params=params,
            response_model=APIResponse[LatestExecutionsData],
        )

    def create_order(
            self,
            *,
            symbol: str,
            side: str,
            execution_type: str,
            size: str,
            time_in_force: str | None = None,
            price: str | None = None,
            losscut_price: str | None = None,
            cancel_before: bool | None = None,
    ) -> Any:
        body = _prune_params(
            {
                "symbol": symbol,
                "side": side,
                "executionType": execution_type,
                "timeInForce": time_in_force,
                "price": price,
                "losscutPrice": losscut_price,
                "size": size,
                "cancelBefore": cancel_before,
            },
        )
        return self._request("POST", "/v1/order", private=True, json_body=body)

    def change_order(
            self,
            *,
            order_id: int,
            price: str,
            losscut_price: str | None = None,
    ) -> Any:
        body = _prune_params({"orderId": order_id, "price": price, "losscutPrice": losscut_price})
        return self._request("POST", "/v1/changeOrder", private=True, json_body=body)

    def cancel_order(self, order_id: int) -> Any:
        return self._request("POST", "/v1/cancelOrder", private=True, json_body={"orderId": order_id})

    def cancel_orders(self, order_ids: Iterable[Any]) -> Any:
        return self._request("POST", "/v1/cancelOrders", private=True, json_body={"orderIds": list(order_ids)})

    def cancel_bulk_order(
            self,
            symbols: Iterable[str],
            *,
            side: str | None = None,
            settle_type: str | None = None,
            desc: bool | None = None,
    ) -> Any:
        body = _prune_params(
            {
                "symbols": list(symbols),
                "side": side,
                "settleType": settle_type,
                "desc": desc,
            },
        )
        return self._request("POST", "/v1/cancelBulkOrder", private=True, json_body=body)

    # Private API methods (Positions)
    def get_open_positions(
        self,
        symbol: str,
        *,
        page: int | None = None,
        count: int | None = None,
    ) -> APIResponse[OpenPositionsData]:
        params = _prune_params({"symbol": symbol, "page": page, "count": count})
        return self._request(
            "GET",
            "/v1/openPositions",
            private=True,
            params=params,
            response_model=APIResponse[OpenPositionsData],
        )

    def get_position_summary(self, symbol: str | None = None) -> APIResponse[PositionSummaryData]:
        params = _prune_params({"symbol": symbol})
        return self._request(
            "GET",
            "/v1/positionSummary",
            private=True,
            params=params,
            response_model=APIResponse[PositionSummaryData],
        )

    def transfer(self, *, amount: str, transfer_type: str) -> Any:
        body = {"amount": amount, "transferType": transfer_type}
        return self._request("POST", "/v1/account/transfer", private=True, json_body=body)

    def close_order(
            self,
            *,
            symbol: str,
            side: str,
            execution_type: str,
            settle_positions: Iterable[Mapping[str, Any]],
            time_in_force: str | None = None,
            price: str | None = None,
            cancel_before: bool | None = None,
    ) -> Any:
        body = _prune_params(
            {
                "symbol": symbol,
                "side": side,
                "executionType": execution_type,
                "timeInForce": time_in_force,
                "price": price,
                "settlePosition": list(settle_positions),
                "cancelBefore": cancel_before,
            },
        )
        return self._request("POST", "/v1/closeOrder", private=True, json_body=body)

    def close_bulk_order(
            self,
            *,
            symbol: str,
            side: str,
            execution_type: str,
            size: str,
            time_in_force: str | None = None,
            price: str | None = None,
    ) -> Any:
        body = _prune_params(
            {
                "symbol": symbol,
                "side": side,
                "executionType": execution_type,
                "timeInForce": time_in_force,
                "price": price,
                "size": size,
            },
        )
        return self._request("POST", "/v1/closeBulkOrder", private=True, json_body=body)

    def change_losscut_price(self, *, position_id: int, losscut_price: str) -> Any:
        body = {"positionId": position_id, "losscutPrice": losscut_price}
        return self._request("POST", "/v1/changeLosscutPrice", private=True, json_body=body)

    # Private API methods (WebSocket auth)
    def ws_auth_create(self) -> Any:
        return self._request("POST", "/v1/ws-auth", private=True, json_body={})

    def ws_auth_extend(self, token: str) -> Any:
        return self._request(
            "PUT",
            "/v1/ws-auth",
            private=True,
            json_body={"token": token},
            sign_body=False,
        )

    def ws_auth_delete(self, token: str) -> Any:
        return self._request(
            "DELETE",
            "/v1/ws-auth",
            private=True,
            json_body={"token": token},
            sign_body=False,
        )
