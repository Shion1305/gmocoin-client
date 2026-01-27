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


class Client:
    """GMO Coin REST API client

    GMO Coin の REST API クライアント
    """
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

    def __enter__(self) -> "Client":
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
    ) -> "Client":
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
        """Fetch service status.

        サービスステータスを取得します。

        Docs: https://api.coin.z.com/docs/#status

        Args:
            None.

        Returns:
            APIResponse containing service status data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "status": "OPEN"
                  },
                  "responsetime": "2019-03-19T02:15:06.001Z"
                }
        """
        return self._request("GET", "/v1/status", response_model=APIResponse[ServiceStatusData])

    def get_ticker(self, symbol: str | None = None) -> APIResponse[list[TickerItem]]:
        """Fetch latest ticker rates.

        最新レートを取得します。パラメータ指定がない場合、全シンボルの情報を返します。

        Docs: https://api.coin.z.com/docs/#ticker

        Args:
            symbol: Optional symbol filter. If omitted, returns all symbols.

        Returns:
            APIResponse containing a list of ticker items.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "ask": "750760",
                      "bid": "750600",
                      "high": "762302",
                      "last": "756662",
                      "low": "704874",
                      "symbol": "BTC",
                      "timestamp": "2018-03-30T12:34:56.789Z",
                      "volume": "194785.8484"
                    }
                  ],
                  "responsetime": "2019-03-19T02:15:06.014Z"
                }
        """
        params = _prune_params({"symbol": symbol})
        return self._request(
            "GET",
            "/v1/ticker",
            params=params,
            response_model=APIResponse[list[TickerItem]],
        )

    def get_orderbooks(self, symbol: str) -> APIResponse[OrderbookData]:
        """Fetch order book snapshot for a symbol.

        板情報（スナップショット）を取得します。

        Docs: https://api.coin.z.com/docs/#orderbooks

        Args:
            symbol: Target symbol (e.g., "BTC").

        Returns:
            APIResponse containing order book data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "asks": [
                      {
                        "price": "455659",
                        "size": "0.1"
                      }
                    ],
                    "bids": [
                      {
                        "price": "455659",
                        "size": "0.1"
                      }
                    ],
                    "symbol": "BTC"
                  },
                  "responsetime": "2019-03-19T02:15:06.026Z"
                }
        """
        return self._request(
            "GET",
            "/v1/orderbooks",
            params={"symbol": symbol},
            response_model=APIResponse[OrderbookData],
        )

    def get_trades(self, symbol: str, *, page: int | None = None, count: int | None = None) -> APIResponse[TradesData]:
        """Fetch recent trades for a symbol.

        約定履歴を取得します。

        Docs: https://api.coin.z.com/docs/#trades

        Args:
            symbol: Target symbol (e.g., "BTC").
            page: Optional page number.
            count: Optional page size.

        Returns:
            APIResponse containing trades data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "pagination": {
                      "currentPage": 1,
                      "count": 30
                    },
                    "list": [
                      {
                        "price": "750760",
                        "side": "BUY",
                        "size": "0.1",
                        "timestamp": "2018-03-30T12:34:56.789Z"
                      }
                    ]
                  },
                  "responsetime": "2019-03-28T09:28:07.980Z"
                }
        """
        params = _prune_params({"symbol": symbol, "page": page, "count": count})
        return self._request(
            "GET",
            "/v1/trades",
            params=params,
            response_model=APIResponse[TradesData],
        )

    def get_klines(self, symbol: str, interval: str, date: str) -> APIResponse[list[KlineItem]]:
        """Fetch OHLCV kline data.

        ローソク足データを取得します。

        Docs: https://api.coin.z.com/docs/#klines

        Args:
            symbol: Target symbol (e.g., "BTC").
            interval: Kline interval (e.g., "1min").
            date: Date filter (YYYYMMDD or YYYY).

        Returns:
            APIResponse containing a list of kline items.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                        "openTime":"1618588800000",
                        "open":"6418255",
                        "high":"6518250",
                        "low":"6318250",
                        "close":"6418253",
                        "volume":"0.0001"
                    },
                    {
                        "openTime":"1618588860000",
                        "open":"6418251",
                        "high":"6418252",
                        "low":"6415250",
                        "close":"6418245",
                        "volume":"0.0001"
                    }
                  ],
                  "responsetime": "2019-03-28T09:28:07.980Z"
                }
        """
        params = {"symbol": symbol, "interval": interval, "date": date}
        return self._request(
            "GET",
            "/v1/klines",
            params=params,
            response_model=APIResponse[list[KlineItem]],
        )

    def get_symbols(self) -> APIResponse[list[SymbolRule]]:
        """Fetch trading rules and symbols.

        取引ルールとシンボル情報を取得します。

        Docs: https://api.coin.z.com/docs/#symbols

        Args:
            None.

        Returns:
            APIResponse containing symbol rules.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "symbol": "BTC",
                      "minOrderSize": "0.0001",
                      "maxOrderSize": "5",
                      "sizeStep": "0.0001",
                      "tickSize": "1",
                      "takerFee": "0.0005",
                      "makerFee": "-0.0001"
                    },
                    {
                      "symbol": "BTC_JPY",
                      "minOrderSize": "0.01",
                      "maxOrderSize": "5",
                      "sizeStep": "0.01",
                      "tickSize": "1",
                      "takerFee": "0",
                      "makerFee": "0"
                    }
                  ],
                  "responsetime": "2022-12-15T19:22:23.792Z"
                }
        """
        return self._request("GET", "/v1/symbols", response_model=APIResponse[list[SymbolRule]])

    # Private API methods (Account)
    def get_margin(self) -> APIResponse[MarginData]:
        """Fetch margin summary.

        証拠金サマリーを取得します。

        Docs: https://api.coin.z.com/docs/#margin

        Args:
            None.

        Returns:
            APIResponse containing margin data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "actualProfitLoss": "68286188",
                    "availableAmount": "57262506",
                    "margin": "1021682",
                    "marginCallStatus": "NORMAL",
                    "marginRatio": "6683.6",
                    "profitLoss": "0",
                    "transferableAmount": "57262506"
                  },
                  "responsetime": "2019-03-19T02:15:06.051Z"
                }
        """
        return self._request(
            "GET",
            "/v1/account/margin",
            private=True,
            response_model=APIResponse[MarginData],
        )

    def get_assets(self) -> APIResponse[list[AssetItem]]:
        """Fetch asset balances.

        資産残高を取得します。

        Docs: https://api.coin.z.com/docs/#assets

        Args:
            None.

        Returns:
            APIResponse containing asset balances.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "amount": "993982448",
                      "available": "993982448",
                      "conversionRate": "1",
                      "symbol": "JPY"
                    },
                    {
                      "amount": "4.0002",
                      "available": "4.0002",
                      "conversionRate": "859614",
                      "symbol": "BTC"
                    }
                  ],
                  "responsetime": "2019-03-19T02:15:06.055Z"
                }
        """
        return self._request(
            "GET",
            "/v1/account/assets",
            private=True,
            response_model=APIResponse[list[AssetItem]],
        )

    def get_trading_volume(self) -> APIResponse[TradingVolumeData]:
        """Fetch trading volume information.

        取引量情報を取得します。

        Docs: https://api.coin.z.com/docs/#tradingVolume

        Args:
            None.

        Returns:
            APIResponse containing trading volume data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                      "jpyVolume": "9988888",
                      "tierLevel": 1,
                      "limit": [
                         {
                           "symbol": "BTC/JPY",
                           "todayLimitOpenSize": "10000",
                           "takerFee": "0",
                           "makerFee": "0"
                         },
                         {
                           "symbol": "BTC",
                           "todayLimitBuySize": "98",
                           "todayLimitSellSize": "102",
                           "takerFee": "0.0015",
                           "makerFee": "-0.0007"
                         }
                      ]
                  },
                  "responsetime": "2019-03-19T02:15:06.055Z"
                }
        """
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
        """Fetch fiat deposit history.

        日本円の入金履歴を取得します。

        Docs: https://api.coin.z.com/docs/#fiatDepositHistory

        Args:
            from_timestamp: Start time in UTC ISO8601 format with milliseconds.
            to_timestamp: Optional end time in UTC ISO8601 format with milliseconds.

        Returns:
            APIResponse containing fiat deposit history records.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "amount": "50000",
                      "fee": "0",
                      "status": "EXECUTED",
                      "symbol": "JPY",
                      "timestamp": "2021-01-01T13:47:12.791Z"
                    }
                  ],
                  "responsetime": "2024-02-28T11:48:57.996Z"
                }
        """
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
        """Fetch fiat withdrawal history.

        日本円の出金履歴を取得します。

        Docs: https://api.coin.z.com/docs/#fiatWithdrawalHistory

        Args:
            from_timestamp: Start time in UTC ISO8601 format with milliseconds.
            to_timestamp: Optional end time in UTC ISO8601 format with milliseconds.

        Returns:
            APIResponse containing fiat withdrawal history records.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "amount": "50000",
                      "fee": "0",
                      "status": "EXECUTED",
                      "symbol": "JPY",
                      "timestamp": "2021-01-01T13:47:12.791Z"
                    }
                  ],
                  "responsetime": "2024-02-28T11:48:57.996Z"
                }
        """
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
        """Fetch cryptocurrency deposit history.

        暗号資産の入金履歴を取得します。

        Docs: https://api.coin.z.com/docs/#depositHistory

        Args:
            symbol: Asset symbol to filter (e.g., "BTC").
            from_timestamp: Start time in UTC ISO8601 format with milliseconds.
            to_timestamp: Optional end time in UTC ISO8601 format with milliseconds.

        Returns:
            APIResponse containing a list of deposit history records.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "address": "xxx",
                      "amount": "0.9503",
                      "status": "EXECUTED",
                      "symbol": "BTC",
                      "timestamp": "2021-10-05T06:04:46.241Z",
                      "txHash": "yyy"
                    }
                  ],
                  "responsetime": "2024-02-28T12:20:07.103Z"
                }
        """
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
        """Fetch cryptocurrency withdrawal history.

        暗号資産の出金履歴を取得します。

        Docs: https://api.coin.z.com/docs/#withdrawalHistory

        Args:
            symbol: Asset symbol to filter (e.g., "BTC").
            from_timestamp: Start time in UTC ISO8601 format with milliseconds.
            to_timestamp: Optional end time in UTC ISO8601 format with milliseconds.

        Returns:
            APIResponse containing withdrawal history records.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "address": "xxx",
                      "amount": "0.9503",
                      "status": "EXECUTED",
                      "symbol": "BTC",
                      "timestamp": "2021-10-05T06:04:46.241Z",
                      "txHash": "yyy"
                    }
                  ],
                  "responsetime": "2024-02-28T12:20:07.103Z"
                }
        """
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
        """Fetch order information by order IDs.

        注文情報を取得します。

        Docs: https://api.coin.z.com/docs/#orders

        Args:
            order_ids: Order ID or list of order IDs (comma-separated for multiple).

        Returns:
            APIResponse containing order list data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "list": [
                      {
                        "orderId": 223456789,
                        "rootOrderId": 223456789,
                        "symbol": "BTC_JPY",
                        "side": "BUY",
                        "orderType": "NORMAL",
                        "executionType": "LIMIT",
                        "settleType": "OPEN",
                        "size": "0.02",
                        "executedSize": "0.02",
                        "price": "1430001",
                        "losscutPrice": "0",
                        "status": "EXECUTED",
                        "timeInForce": "FAS",
                        "timestamp": "2020-10-14T20:18:59.343Z"
                      },
                      {
                        "rootOrderId": 123456789,
                        "orderId": 123456789,
                        "symbol": "BTC",
                        "side": "BUY",
                        "orderType": "NORMAL",
                        "executionType": "LIMIT",
                        "settleType": "OPEN",
                        "size": "1",
                        "executedSize": "0",
                        "price": "900000",
                        "losscutPrice": "0",
                        "status": "CANCELED",
                        "cancelType": "USER",
                        "timeInForce": "FAS",
                        "timestamp": "2019-03-19T02:15:06.059Z"
                      }
                    ]
                  },
                  "responsetime": "2019-03-19T02:15:06.059Z"
                }
        """
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
        """Fetch active orders for a symbol.

        注文中のオーダー一覧を取得します。

        Docs: https://api.coin.z.com/docs/#active-orders

        Args:
            symbol: Target symbol (e.g., "BTC").
            page: Optional page number.
            count: Optional page size.

        Returns:
            APIResponse containing active orders data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "pagination": {
                      "currentPage": 1,
                      "count": 30
                    },
                    "list": [
                      {
                        "rootOrderId": 123456789,
                        "orderId": 123456789,
                        "symbol": "BTC",
                        "side": "BUY",
                        "orderType": "NORMAL",
                        "executionType": "LIMIT",
                        "settleType": "OPEN",
                        "size": "1",
                        "executedSize": "0",
                        "price": "840000",
                        "losscutPrice": "0",
                        "status": "ORDERED",
                        "timeInForce": "FAS",
                        "timestamp": "2019-03-19T01:07:24.217Z"
                      }
                    ]
                  },
                  "responsetime": "2019-03-19T01:07:24.217Z"
                }
        """
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
        """Fetch executions for an order or execution IDs.

        約定情報を取得します。

        Docs: https://api.coin.z.com/docs/#executions

        Args:
            order_id: Optional order ID.
            execution_id: Optional execution ID or list of IDs.

        Returns:
            APIResponse containing executions data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "list": [
                      {
                        "executionId": 92123912,
                        "orderId": 223456789,
                        "positionId": 1234567,
                        "symbol": "BTC_JPY",
                        "side": "BUY",
                        "settleType": "OPEN",
                        "size": "0.02",
                        "price": "1900000",
                        "lossGain": "0",
                        "fee": "223",
                        "timestamp": "2020-11-24T21:27:04.764Z"
                      },
                      {
                        "executionId": 72123911,
                        "orderId": 123456789,
                        "positionId": 1234567,
                        "symbol": "BTC",
                        "side": "BUY",
                        "settleType": "OPEN",
                        "size": "0.7361",
                        "price": "877404",
                        "lossGain": "0",
                        "fee": "323",
                        "timestamp": "2019-03-19T02:15:06.081Z"
                      }
                    ]
                  },
                  "responsetime": "2019-03-19T02:15:06.081Z"
                }
        """
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
        """Fetch latest executions.

        最新約定情報を取得します。

        Docs: https://api.coin.z.com/docs/#latest-executions

        Args:
            symbol: Target symbol (e.g., "BTC").
            page: Optional page number.
            count: Optional page size.

        Returns:
            APIResponse containing latest executions data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "pagination": {
                      "currentPage": 1,
                      "count": 30
                    },
                    "list": [
                      {
                        "executionId": 72123911,
                        "orderId": 123456789,
                        "positionId": 1234567,
                        "symbol": "BTC",
                        "side": "BUY",
                        "settleType": "OPEN",
                        "size": "0.7361",
                        "price": "877404",
                        "lossGain": "0",
                        "fee": "323",
                        "timestamp": "2019-03-19T02:15:06.086Z"
                      }
                    ]
                  },
                  "responsetime": "2019-03-19T02:15:06.086Z"
                }
        """
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
        """Create a new order.

        新規注文を発注します。

        Docs: https://api.coin.z.com/docs/#order

        Args:
            symbol: Target symbol (e.g., "BTC_JPY").
            side: Order side ("BUY" or "SELL").
            execution_type: Order execution type (e.g., "LIMIT").
            size: Order size.
            time_in_force: Optional time-in-force value.
            price: Optional price (required for LIMIT/STOP).
            losscut_price: Optional losscut price (margin only).
            cancel_before: Optional cancel-before flag.

        Returns:
            APIResponse with the new order ID.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": "637000",
                  "responsetime": "2019-03-19T02:15:06.108Z"
                }
        """
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
        """Change an existing order.

        注文を変更します。

        Docs: https://api.coin.z.com/docs/#change-order

        Args:
            order_id: Order ID to modify.
            price: New price.
            losscut_price: Optional losscut price.

        Returns:
            APIResponse containing the status of the change request.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "responsetime": "2019-03-19T01:07:24.557Z"
                }
        """
        body = _prune_params({"orderId": order_id, "price": price, "losscutPrice": losscut_price})
        return self._request("POST", "/v1/changeOrder", private=True, json_body=body)

    def cancel_order(self, order_id: int) -> Any:
        """Cancel a single order.

        注文をキャンセルします。

        Docs: https://api.coin.z.com/docs/#cancel-order

        Args:
            order_id: Order ID to cancel.

        Returns:
            APIResponse containing the status of the cancel request.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "responsetime": "2019-03-19T01:07:24.557Z"
                }
        """
        return self._request("POST", "/v1/cancelOrder", private=True, json_body={"orderId": order_id})

    def cancel_orders(self, order_ids: Iterable[Any]) -> Any:
        """Cancel multiple orders.

        複数注文をキャンセルします。

        Docs: https://api.coin.z.com/docs/#cancel-orders

        Args:
            order_ids: List of order IDs (max 10).

        Returns:
            APIResponse containing success and failure results.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                      "failed": [
                        {
                          "message_code": "ERR-5122",
                          "message_string": "The request is invalid due to the status of the specified order.",
                          "orderId": 1
                        },
                        {
                          "message_code": "ERR-5122",
                          "message_string": "The request is invalid due to the status of the specified order.",
                          "orderId": 2
                        }
                      ],
                      "success": [3,4]
                  },
                  "responsetime": "2019-03-19T01:07:24.557Z"
                }
        """
        return self._request("POST", "/v1/cancelOrders", private=True, json_body={"orderIds": list(order_ids)})

    def cancel_bulk_order(
            self,
            symbols: Iterable[str],
            *,
            side: str | None = None,
            settle_type: str | None = None,
            desc: bool | None = None,
    ) -> Any:
        """Cancel bulk orders matching criteria.

        一括キャンセルを実行します。

        Docs: https://api.coin.z.com/docs/#cancel-bulk-order

        Args:
            symbols: Symbols to target.
            side: Optional side filter.
            settle_type: Optional settle type filter.
            desc: Optional ordering flag for cancellation.

        Returns:
            APIResponse containing canceled order IDs.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [637000,637002],
                  "responsetime": "2019-03-19T01:07:24.557Z"
                }
        """
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
        """Fetch open positions.

        建玉一覧を取得します。

        Docs: https://api.coin.z.com/docs/#open-positions

        Args:
            symbol: Margin trading symbol (e.g., "BTC_JPY").
            page: Optional page number.
            count: Optional page size.

        Returns:
            APIResponse containing open positions data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "pagination": {
                      "currentPage": 1,
                      "count": 30
                    },
                    "list": [
                      {
                        "positionId": 1234567,
                        "symbol": "BTC_JPY",
                        "side": "BUY",
                        "size": "0.22",
                        "orderdSize": "0",
                        "price": "876045",
                        "lossGain": "14",
                        "leverage": "4",
                        "losscutPrice": "766540",
                        "timestamp": "2019-03-19T02:15:06.094Z"
                      }
                    ]
                  },
                  "responsetime": "2019-03-19T02:15:06.095Z"
                }
        """
        params = _prune_params({"symbol": symbol, "page": page, "count": count})
        return self._request(
            "GET",
            "/v1/openPositions",
            private=True,
            params=params,
            response_model=APIResponse[OpenPositionsData],
        )

    def get_position_summary(self, symbol: str | None = None) -> APIResponse[PositionSummaryData]:
        """Fetch position summary.

        ポジションサマリーを取得します。

        Docs: https://api.coin.z.com/docs/#position-summary

        Args:
            symbol: Optional margin symbol filter.

        Returns:
            APIResponse containing position summary data.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": {
                    "list": [
                      {
                        "averagePositionRate": "715656",
                        "positionLossGain": "250675",
                        "side": "BUY",
                        "sumOrderQuantity": "2",
                        "sumPositionQuantity": "11.6999",
                        "symbol": "BTC_JPY"
                      }
                    ]
                  },
                  "responsetime": "2019-03-19T02:15:06.102Z"
                }
        """
        params = _prune_params({"symbol": symbol})
        return self._request(
            "GET",
            "/v1/positionSummary",
            private=True,
            params=params,
            response_model=APIResponse[PositionSummaryData],
        )

    def transfer(self, *, amount: str, transfer_type: str) -> Any:
        """Transfer funds between accounts.

        口座間振替を実行します。

        Docs: https://api.coin.z.com/docs/#transfer

        Args:
            amount: Transfer amount in JPY.
            transfer_type: Transfer type ("WITHDRAWAL" or "DEPOSIT").

        Returns:
            APIResponse containing transferred amount.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": [
                    {
                      "transferredAmount": "100000"
                    }
                  ],
                  "responsetime": "2019-03-19T02:15:06.055Z"
                }
        """
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
        """Close a position with a settlement order.

        建玉を決済します。

        Docs: https://api.coin.z.com/docs/#close-order

        Args:
            symbol: Margin trading symbol (e.g., "BTC_JPY").
            side: Order side ("BUY" or "SELL").
            execution_type: Execution type (e.g., "LIMIT").
            settle_positions: List of position IDs and sizes to close.
            time_in_force: Optional time-in-force.
            price: Optional price (required for LIMIT/STOP).
            cancel_before: Optional cancel-before flag.

        Returns:
            APIResponse with the new closing order ID.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": "637000",
                  "responsetime": "2019-03-19T01:07:24.557Z"
                }
        """
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
        """Close positions in bulk.

        複数建玉の一括決済を行います。

        Docs: https://api.coin.z.com/docs/#close-bulk-order

        Args:
            symbol: Margin trading symbol (e.g., "BTC_JPY").
            side: Order side ("BUY" or "SELL").
            execution_type: Execution type (e.g., "LIMIT").
            size: Order size.
            time_in_force: Optional time-in-force.
            price: Optional price (required for LIMIT/STOP).

        Returns:
            APIResponse with the new closing bulk order ID.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": "637000",
                  "responsetime": "2019-03-19T01:07:24.557Z"
                }
        """
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
        """Change losscut price for a position.

        ロスカットレートを変更します。

        Docs: https://api.coin.z.com/docs/#change-losscut-price

        Args:
            position_id: Position ID to update.
            losscut_price: New losscut price.

        Returns:
            APIResponse containing status of the update.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "responsetime": "2019-03-19T01:07:24.557Z"
                }
        """
        body = {"positionId": position_id, "losscutPrice": losscut_price}
        return self._request("POST", "/v1/changeLosscutPrice", private=True, json_body=body)

    # Private API methods (WebSocket auth)
    def ws_auth_create(self) -> Any:
        """Create a WebSocket access token.

        WebSocketアクセストークンを発行します。

        Docs: https://api.coin.z.com/docs/en/?rust#ws-auth-post

        Args:
            None.

        Returns:
            APIResponse containing the access token.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "data": "xxxxxxxxxxxxxxxxxxxx",
                  "responsetime": "2019-03-19T02:15:06.102Z"
                }
        """
        return self._request("POST", "/v1/ws-auth", private=True, json_body={})

    def ws_auth_extend(self, token: str) -> Any:
        """Extend a WebSocket access token.

        WebSocketアクセストークンの期限を延長します。

        Docs: https://api.coin.z.com/docs/en/?rust#ws-auth-put

        Args:
            token: Access token to extend.

        Returns:
            APIResponse containing status of the update.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "responsetime": "2019-03-19T02:15:06.102Z"
                }
        """
        return self._request(
            "PUT",
            "/v1/ws-auth",
            private=True,
            json_body={"token": token},
            sign_body=False,
        )

    def ws_auth_delete(self, token: str) -> Any:
        """Delete a WebSocket access token.

        WebSocketアクセストークンを削除します。

        Docs: https://api.coin.z.com/docs/en/?rust#ws-auth-delete

        Args:
            token: Access token to delete.

        Returns:
            APIResponse containing status of the deletion.

        Examples:
            .. code-block:: json
            
                {
                  "status": 0,
                  "responsetime": "2019-03-19T02:15:06.102Z"
                }
        """
        return self._request(
            "DELETE",
            "/v1/ws-auth",
            private=True,
            json_body={"token": token},
            sign_body=False,
        )
