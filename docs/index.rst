gmocoin-client
==============

Python API client for the GMO Coin crypto exchange.
GMO コイン向けの Python API クライアントです。

Quickstart
----------

.. code-block:: python

   from gmocoin_client import GmoCoinClient

   client = GmoCoinClient.from_env()
   ticker = client.get_ticker(symbol="BTC_JPY")
   print(ticker.data)

Links
-----

- GitHub: https://github.com/Shion1305/gmocoin-client
- GMO Coin API docs: https://api.coin.z.com/docs/

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   client
   models
   errors
