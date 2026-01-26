from __future__ import annotations

from typing import Generic, List, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

ServiceStatus = Literal["MAINTENANCE", "PREOPEN", "OPEN"]
Side = Literal["BUY", "SELL"]
ExecutionType = Literal["MARKET", "LIMIT", "STOP"]
TimeInForce = Literal["FAK", "FAS", "FOK", "SOK"]
OrderType = Literal["NORMAL", "LOSSCUT"]
SettleType = Literal["OPEN", "CLOSE"]
OrderStatus = Literal["WAITING", "ORDERED", "MODIFYING", "CANCELLING", "CANCELED", "EXECUTED", "EXPIRED"]
CancelType = Literal[
    "USER",
    "POSITION_LOSSCUT",
    "INSUFFICIENT_BALANCE",
    "INSUFFICIENT_MARGIN",
    "ACCOUNT_LOSSCUT",
    "MARGIN_CALL",
    "MARGIN_CALL_LOSSCUT",
    "EXPIRED_FAK",
    "EXPIRED_FOK",
    "EXPIRED_SOK",
    "EXPIRED_SELFTRADE",
]
MarginCallStatus = Literal["NORMAL", "MARGIN_CALL", "LOSSCUT"]
ExecutionStatus = Literal["EXECUTED"]


class APIBaseModel(BaseModel):
    """Base model for API payloads.

    API用のベースモデル
    """
    model_config = ConfigDict(extra="allow")


class APIErrorMessage(APIBaseModel):
    """API error message entry.

    エラーメッセージ1件
    """
    message_code: str | None = None
    message_string: str | None = None


class APIResponse(APIBaseModel, Generic[T]):
    """API wrapper response.

    `messages` is populated on error responses when `raise_on_error` is False.
    """
    status: int
    data: T | None = None
    messages: list[APIErrorMessage] | None = None
    responsetime: str | None = None


class Pagination(APIBaseModel):
    """Pagination metadata.

    ページ情報
    """
    currentPage: int | None = None
    count: int | None = None


class ServiceStatusData(APIBaseModel):
    """Service status payload.

    サービスステータス
    """
    status: ServiceStatus


class TickerItem(APIBaseModel):
    """Ticker entry.

    ティッカー情報
    """
    ask: str | None = None
    bid: str | None = None
    high: str | None = None
    last: str | None = None
    low: str | None = None
    symbol: str | None = None
    timestamp: str | None = None
    volume: str | None = None


class OrderbookLevel(APIBaseModel):
    """Order book level.

    板の価格レベル
    """
    price: str | None = None
    size: str | None = None


class OrderbookData(APIBaseModel):
    """Order book snapshot.

    板スナップショット
    """
    asks: list[OrderbookLevel] | None = None
    bids: list[OrderbookLevel] | None = None
    symbol: str | None = None


class TradeItem(APIBaseModel):
    """Trade entry.

    約定情報
    """
    price: str | None = None
    side: Side | None = None
    size: str | None = None
    timestamp: str | None = None


class TradesData(APIBaseModel):
    """Trades response payload.

    約定一覧データ
    """
    pagination: Pagination | None = None
    list: List[TradeItem] | None = None


class KlineItem(APIBaseModel):
    """Kline entry.

    ローソク足データ
    """
    openTime: str | None = None
    open: str | None = None
    high: str | None = None
    low: str | None = None
    close: str | None = None
    volume: str | None = None


class SymbolRule(APIBaseModel):
    """Symbol rule entry.

    銘柄の取引ルール
    """
    symbol: str | None = None
    minOrderSize: str | None = None
    maxOrderSize: str | None = None
    sizeStep: str | None = None
    tickSize: str | None = None
    takerFee: str | None = None
    makerFee: str | None = None


class MarginData(APIBaseModel):
    """Margin summary.

    証拠金サマリー
    """
    actualProfitLoss: str | None = None
    availableAmount: str | None = None
    margin: str | None = None
    marginCallStatus: MarginCallStatus | None = None
    marginRatio: str | None = None
    profitLoss: str | None = None
    transferableAmount: str | None = None


class AssetItem(APIBaseModel):
    """Asset balance entry.

    資産残高
    """
    amount: str | None = None
    available: str | None = None
    conversionRate: str | None = None
    symbol: str | None = None


class TradingVolumeLimit(APIBaseModel):
    """Trading volume limit entry.

    取引量の制限
    """
    symbol: str | None = None
    todayLimitOpenSize: str | None = None
    todayLimitBuySize: str | None = None
    todayLimitSellSize: str | None = None
    takerFee: str | None = None
    makerFee: str | None = None


class TradingVolumeData(APIBaseModel):
    """Trading volume payload.

    取引量データ
    """
    jpyVolume: str | None = None
    tierLevel: int | None = None
    limit: list[TradingVolumeLimit] | None = None


class FiatHistoryItem(APIBaseModel):
    """Fiat history entry.

    法定通貨の履歴
    """
    amount: str | None = None
    fee: str | None = None
    status: ExecutionStatus | None = None
    symbol: str | None = None
    timestamp: str | None = None


class CryptoHistoryItem(APIBaseModel):
    """Crypto history entry.

    暗号資産の履歴
    """
    address: str | None = None
    amount: str | None = None
    fee: str | None = None
    status: ExecutionStatus | None = None
    symbol: str | None = None
    timestamp: str | None = None
    txHash: str | None = None


class OrderItem(APIBaseModel):
    """Order entry.

    注文情報
    """
    rootOrderId: int | None = None
    orderId: int | None = None
    symbol: str | None = None
    side: Side | None = None
    orderType: OrderType | None = None
    executionType: ExecutionType | None = None
    settleType: SettleType | None = None
    size: str | None = None
    executedSize: str | None = None
    price: str | None = None
    losscutPrice: str | None = None
    status: OrderStatus | None = None
    cancelType: CancelType | None = None
    timeInForce: TimeInForce | None = None
    timestamp: str | None = None


class OrdersData(APIBaseModel):
    """Orders list payload.

    注文一覧データ
    """
    list: List[OrderItem] | None = None


class ActiveOrdersData(APIBaseModel):
    """Active orders payload.

    注文中一覧データ
    """
    pagination: Pagination | None = None
    list: List[OrderItem] | None = None


class ExecutionItem(APIBaseModel):
    """Execution entry.

    約定情報
    """
    executionId: int | None = None
    orderId: int | None = None
    positionId: int | None = None
    symbol: str | None = None
    side: Side | None = None
    settleType: SettleType | None = None
    size: str | None = None
    price: str | None = None
    lossGain: str | None = None
    fee: str | None = None
    timestamp: str | None = None


class ExecutionsData(APIBaseModel):
    """Executions list payload.

    約定一覧データ
    """
    list: List[ExecutionItem] | None = None


class LatestExecutionsData(APIBaseModel):
    """Latest executions payload.

    最新約定データ
    """
    pagination: Pagination | None = None
    list: List[ExecutionItem] | None = None


class PositionItem(APIBaseModel):
    """Position entry.

    建玉情報
    """
    positionId: int | None = None
    symbol: str | None = None
    side: Side | None = None
    size: str | None = None
    orderdSize: str | None = None
    price: str | None = None
    lossGain: str | None = None
    leverage: str | None = None
    losscutPrice: str | None = None
    timestamp: str | None = None


class OpenPositionsData(APIBaseModel):
    """Open positions payload.

    建玉一覧データ
    """
    pagination: Pagination | None = None
    list: List[PositionItem] | None = None


class PositionSummaryItem(APIBaseModel):
    """Position summary entry.

    ポジションサマリー
    """
    averagePositionRate: str | None = None
    positionLossGain: str | None = None
    side: Side | None = None
    sumOrderQuantity: str | None = None
    sumPositionQuantity: str | None = None
    symbol: str | None = None


class PositionSummaryData(APIBaseModel):
    """Position summary payload.

    ポジションサマリー一覧データ
    """
    list: List[PositionSummaryItem] | None = None
