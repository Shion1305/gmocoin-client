import os
import time
from decimal import Decimal

import pytest
from pydantic import BaseModel

from gmocoin_client import GmoCoinClient
from tests.live._helpers import require_live_env

pytestmark = pytest.mark.live


def _require_price_if_needed(label: str, execution_type: str, price: str | None) -> None:
    if execution_type in {"LIMIT", "STOP"} and not price:
        pytest.skip(f"{label} requires a price when executionType is {execution_type}.")


def _get_executed_size(client: GmoCoinClient, order_id: int, timeout: float, interval: float) -> Decimal:
    deadline = time.monotonic() + timeout
    total = Decimal("0")

    while time.monotonic() < deadline:
        response = client.get_executions(order_id=order_id)
        data = response.data if hasattr(response, "data") else response.get("data")
        executions = _normalize_execution_list(data)
        if executions:
            total = sum((Decimal(item["size"]) for item in executions), Decimal("0"))
            if total > 0:
                return total
        time.sleep(interval)

    return total


def _normalize_execution_list(data) -> list[dict]:
    if hasattr(data, "list"):
        value = getattr(data, "list")
        if isinstance(value, list):
            return [_as_dict(item) for item in value if _as_dict(item) is not None]
    if isinstance(data, list):
        return [_as_dict(item) for item in data if _as_dict(item) is not None]
    if isinstance(data, dict):
        for key in ("list", "executions", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [_as_dict(item) for item in value if _as_dict(item) is not None]
    return []


def _as_dict(item) -> dict | None:
    if isinstance(item, dict):
        return item
    if isinstance(item, BaseModel):
        return item.model_dump()
    return None


def test_spot_buy_then_sell():
    # Live scenario: buy a small amount spot, then sell the executed size.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY", "GMO_LIVE_SYMBOL", "GMO_LIVE_SIZE"])

    symbol = os.getenv("GMO_LIVE_SYMBOL")
    size = os.getenv("GMO_LIVE_SIZE")

    buy_execution_type = os.getenv("GMO_LIVE_BUY_EXECUTION_TYPE", "MARKET")
    buy_time_in_force = os.getenv("GMO_LIVE_BUY_TIME_IN_FORCE", "FAK")
    buy_price = os.getenv("GMO_LIVE_BUY_PRICE")

    sell_execution_type = os.getenv("GMO_LIVE_SELL_EXECUTION_TYPE", "MARKET")
    sell_time_in_force = os.getenv("GMO_LIVE_SELL_TIME_IN_FORCE", "FAK")
    sell_price = os.getenv("GMO_LIVE_SELL_PRICE")

    _require_price_if_needed("BUY order", buy_execution_type, buy_price)
    _require_price_if_needed("SELL order", sell_execution_type, sell_price)

    wait_timeout = float(os.getenv("GMO_LIVE_WAIT_TIMEOUT", "10"))
    wait_interval = float(os.getenv("GMO_LIVE_WAIT_INTERVAL", "1"))

    with GmoCoinClient.from_env() as client:
        buy_response = client.create_order(
            symbol=symbol,
            side="BUY",
            execution_type=buy_execution_type,
            time_in_force=buy_time_in_force,
            price=buy_price,
            size=size,
        )
        buy_order_id = buy_response.get("data")
        assert buy_order_id is not None, f"Unexpected BUY response: {buy_response}"

        executed_size = _get_executed_size(
            client,
            order_id=int(buy_order_id),
            timeout=wait_timeout,
            interval=wait_interval,
        )
        assert executed_size > 0, "Buy order did not execute in time."

        sell_response = client.create_order(
            symbol=symbol,
            side="SELL",
            execution_type=sell_execution_type,
            time_in_force=sell_time_in_force,
            price=sell_price,
            size=str(executed_size),
        )
        sell_order_id = sell_response.get("data")
        assert sell_order_id is not None, f"Unexpected SELL response: {sell_response}"
