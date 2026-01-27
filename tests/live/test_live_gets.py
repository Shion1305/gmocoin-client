import os

import pytest

from gmocoin_client import Client
from gmocoin_client.models import (
    ActiveOrdersData,
    APIResponse,
    AssetItem,
    KlineItem,
    LatestExecutionsData,
    MarginData,
    OpenPositionsData,
    OrderbookData,
    OrderbookLevel,
    Pagination,
    PositionSummaryData,
    ServiceStatusData,
    SymbolRule,
    TickerItem,
    TradeItem,
    TradesData,
    TradingVolumeData,
)
from tests.live._helpers import require_live_env

pytestmark = pytest.mark.live


def _assert_list_items(items, item_type):
    assert isinstance(items, list)
    for item in items:
        assert isinstance(item, item_type)


def _get_symbol() -> str:
    return os.getenv("GMO_LIVE_SYMBOL", "BTC")


def _get_margin_symbol() -> str:
    return os.getenv("GMO_LIVE_MARGIN_SYMBOL", "BTC_JPY")


def _get_klines_interval() -> str:
    return os.getenv("GMO_LIVE_KLINES_INTERVAL", "1min")


def _get_klines_date() -> str:
    return os.getenv("GMO_LIVE_KLINES_DATE", "20210417")


def test_public_status():
    # Live check for service status response typing.
    require_live_env()
    client = Client()
    status = client.get_status()
    assert isinstance(status, APIResponse)
    assert isinstance(status.data, ServiceStatusData)


_USE_ENV_SYMBOL = object()


@pytest.mark.parametrize(
    "symbol_value, expect_symbol",
    [(_USE_ENV_SYMBOL, True), (None, False)],
    ids=["single_symbol", "all_symbols"],
)
def test_public_ticker(symbol_value, expect_symbol):
    """Table test: filtered ticker includes the symbol; unfiltered returns all symbols."""
    require_live_env()
    symbol = _get_symbol() if symbol_value is _USE_ENV_SYMBOL else None
    client = Client()
    ticker = client.get_ticker(symbol)
    assert isinstance(ticker, APIResponse)
    assert isinstance(ticker.data, list)
    _assert_list_items(ticker.data, TickerItem)
    assert len(ticker.data) > 0
    if expect_symbol:
        assert any(item.symbol == symbol for item in ticker.data)


def test_public_orderbooks():
    # Live check for orderbook response typing.
    require_live_env()
    client = Client()
    orderbooks = client.get_orderbooks(_get_symbol())
    assert isinstance(orderbooks, APIResponse)
    assert isinstance(orderbooks.data, OrderbookData)
    if orderbooks.data.asks is not None:
        _assert_list_items(orderbooks.data.asks, OrderbookLevel)
    if orderbooks.data.bids is not None:
        _assert_list_items(orderbooks.data.bids, OrderbookLevel)


@pytest.mark.parametrize(
    "page_value,count_value",
    [(1, 1), (None, None)],
    ids=["paged", "default"],
)
def test_public_trades(page_value, count_value):
    """Table test: paged and default trades responses are well-typed."""
    require_live_env()
    client = Client()
    trades = client.get_trades(_get_symbol(), page=page_value, count=count_value)
    assert isinstance(trades, APIResponse)
    assert isinstance(trades.data, TradesData)
    if trades.data.pagination is not None:
        assert isinstance(trades.data.pagination, Pagination)
    if trades.data.list is not None:
        _assert_list_items(trades.data.list, TradeItem)


def test_public_klines():
    # Live check for klines response typing.
    require_live_env()
    client = Client()
    klines = client.get_klines(_get_symbol(), _get_klines_interval(), _get_klines_date())
    assert isinstance(klines, APIResponse)
    assert isinstance(klines.data, list)
    _assert_list_items(klines.data, KlineItem)


def test_public_symbols():
    # Live check for symbols response typing.
    require_live_env()
    client = Client()
    symbols = client.get_symbols()
    assert isinstance(symbols, APIResponse)
    assert isinstance(symbols.data, list)
    _assert_list_items(symbols.data, SymbolRule)


def test_private_margin():
    # Live check for margin response typing.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY"])
    with Client.from_env() as client:
        margin = client.get_margin()
        assert isinstance(margin, APIResponse)
        assert isinstance(margin.data, MarginData)


def test_private_assets():
    # Live check for assets response typing.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY"])
    with Client.from_env() as client:
        assets = client.get_assets()
        assert isinstance(assets, APIResponse)
        assert isinstance(assets.data, list)
        _assert_list_items(assets.data, AssetItem)


def test_private_trading_volume():
    # Live check for trading volume response typing.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY"])
    with Client.from_env() as client:
        volume = client.get_trading_volume()
        assert isinstance(volume, APIResponse)
        assert isinstance(volume.data, TradingVolumeData)


def test_private_active_orders():
    # Live check for active orders response typing.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY"])
    with Client.from_env() as client:
        active = client.get_active_orders(_get_symbol(), page=1, count=1)
        assert isinstance(active, APIResponse)
        assert isinstance(active.data, ActiveOrdersData)


def test_private_latest_executions():
    # Live check for latest executions response typing.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY"])
    with Client.from_env() as client:
        latest = client.get_latest_executions(_get_symbol(), page=1, count=1)
        assert isinstance(latest, APIResponse)
        assert isinstance(latest.data, LatestExecutionsData)


def test_private_open_positions():
    # Live check for open positions response typing.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY"])
    with Client.from_env() as client:
        positions = client.get_open_positions(_get_margin_symbol(), page=1, count=1)
        assert isinstance(positions, APIResponse)
        assert isinstance(positions.data, OpenPositionsData)


def test_private_position_summary():
    # Live check for position summary response typing.
    require_live_env(["GMO_API_KEY", "GMO_SECRET_KEY"])
    with Client.from_env() as client:
        summary = client.get_position_summary(_get_margin_symbol())
        assert isinstance(summary, APIResponse)
        assert isinstance(summary.data, PositionSummaryData)
