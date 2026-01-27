# GMO Coin Python Client Library

A Python client library for interacting with the GMO Coin cryptocurrency exchange API.

## 📘 GMO Coin API Coverage

## Usage

Set `GMO_API_KEY` and `GMO_SECRET_KEY` in your environment for private API calls.

### Public endpoints

```python
from gmocoin_client import Client

client = Client()

status = client.get_status()
ticker = client.get_ticker("BTC")
orderbooks = client.get_orderbooks("BTC")
```

### Private endpoints (with env vars)

```python
from gmocoin_client import Client

with Client.from_env() as client:
    assets = client.get_assets()
    margin = client.get_margin()
```

### Place an order

```python
from gmocoin_client import Client

with Client.from_env() as client:
    order = client.create_order(
        symbol="BTC_JPY",
        side="BUY",
        execution_type="LIMIT",
        time_in_force="FAS",
        price="430001",
        size="0.02",
    )
```

### WebSocket access token

```python
from gmocoin_client import Client

with Client.from_env() as client:
    token = client.ws_auth_create()
```

### Error handling

```python
from gmocoin_client import GmoCoinApiError, Client, GmoCoinHttpError

client = Client()

try:
    client.get_ticker("BTC")
except GmoCoinApiError as exc:
    print(exc)
except GmoCoinHttpError as exc:
    print(exc)
```

### Live trading tests (local-only)

Live tests are excluded by default. To run them locally, opt in and set required
environment variables (see `.env.example`). Tests load `.env` automatically:

```bash
export GMO_LIVE_TESTS=true
export GMO_API_KEY="your_api_key"
export GMO_SECRET_KEY="your_secret_key"
export GMO_LIVE_SYMBOL="BTC"
export GMO_LIVE_SIZE="0.0001"
export GMO_LIVE_BUY_EXECUTION_TYPE="MARKET"
export GMO_LIVE_SELL_EXECUTION_TYPE="MARKET"
```

Then run:

```bash
pytest -m live
```

## Public REST API

| Category                | Endpoint / Function     | Path | Implemented |
|-------------------------|-------------------------|------|-------------|
| Exchange status         | `/public/v1/status`     | ✅    |
| Latest ticker (rate)    | `/public/v1/ticker`     | ✅    |
| Order book              | `/public/v1/orderbooks` | ✅    |
| Trades                  | `/public/v1/trades`     | ✅    |
| K-Line (OHLCV)          | `/public/v1/klines`     | ✅    |
| Trading rules / symbols | `/public/v1/symbols`    | ✅    |

## Private REST API

| Category                    | Endpoint / Function                          | Path | Implemented |
|-----------------------------|----------------------------------------------|------|-------------|
| Collateral / margin summary | `/private/v1/account/margin`                 | ✅    |
| Asset balances              | `/private/v1/account/assets`                 | ✅    |
| Trading volume info         | `/private/v1/account/tradingVolume`          | ✅    |
| JPY deposit history         | `/private/v1/account/fiatDeposit/history`    | ✅    |
| JPY withdrawal history      | `/private/v1/account/fiatWithdrawal/history` | ✅    |
| Crypto deposit history      | `/private/v1/account/deposit/history`        | ✅    |
| Crypto withdrawal history   | `/private/v1/account/withdrawal/history`     | ✅    |
| Query orders                | `/private/v1/orders`                         | ✅    |
| Active orders               | `/private/v1/activeOrders`                   | ✅    |
| Executions                  | `/private/v1/executions`                     | ✅    |
| Latest executions           | `/private/v1/latestExecutions`               | ✅    |
| Open positions              | `/private/v1/openPositions`                  | ✅    |
| Position summary            | `/private/v1/positionSummary`                | ✅    |
| Internal transfer           | `/private/v1/account/transfer`               | ✅    |
| Place order                 | `/private/v1/order` (POST)                   | ✅    |
| Change order                | `/private/v1/changeOrder`                    | ✅    |
| Cancel order                | `/private/v1/cancelOrder`                    | ✅    |
| Cancel multiple orders      | `/private/v1/cancelOrders`                   | ✅    |
| Cancel bulk orders          | `/private/v1/cancelBulkOrder`                | ✅    |
| Cancel all orders           | `/private/v1/cancelAll`                      | ❌    |
| Close (settlement) order    | `/private/v1/closeOrder`                     | ✅    |
| Bulk close orders           | `/private/v1/closeBulkOrder`                 | ✅    |
| Change loss-cut price       | `/private/v1/changeLosscutPrice`             | ✅    |

## Public WebSocket API

| Category                  | Endpoint / Function                                     | Path | Implemented |
|---------------------------|---------------------------------------------------------|------|-------------|
| Subscribe: ticker updates | `wss://api.coin.z.com/ws/public` (channel=`ticker`)     | ❌    |
| Subscribe: order book     | `wss://api.coin.z.com/ws/public` (channel=`orderbooks`) | ❌    |
| Subscribe: trades         | `wss://api.coin.z.com/ws/public` (channel=`trades`)     | ❌    |

## Private WebSocket API

| Category                           | Endpoint / Function                                                 | Path | Implemented |
|------------------------------------|---------------------------------------------------------------------|------|-------------|
| Obtain access token                | `/private/v1/ws-auth` (POST)                                        | ✅    |
| Extend access token                | `/private/v1/ws-auth` (PUT)                                         | ✅    |
| Revoke access token                | `/private/v1/ws-auth` (DELETE)                                      | ✅    |
| Subscribe: order events            | `wss://api.coin.z.com/ws/private` (channel=`orderEvents`)           | ❌    |
| Subscribe: execution events        | `wss://api.coin.z.com/ws/private` (channel=`executionEvents`)       | ❌    |
| Subscribe: position events         | `wss://api.coin.z.com/ws/private` (channel=`positionEvents`)        | ❌    |
| Subscribe: position summary events | `wss://api.coin.z.com/ws/private` (channel=`positionSummaryEvents`) | ❌    |
