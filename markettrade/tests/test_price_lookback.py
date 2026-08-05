import threading
import time
from unittest.mock import MagicMock, patch

from trade.price_lookback import (
    BinancePriceSource,
    InMemoryPriceCache,
    LookbackTask,
    PriceLookback,
)


# --- InMemoryPriceCache ---


def test_cache_record_and_retrieve():
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 1000.0, 50000.0)
    assert cache.get_price("BTCUSDT", 1000.0) == 50000.0


def test_cache_retrieves_within_tolerance():
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 1000.0, 50000.0)
    assert cache.get_price("BTCUSDT", 1003.0, tolerance_s=5.0) == 50000.0


def test_cache_returns_none_outside_tolerance():
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 1000.0, 50000.0)
    assert cache.get_price("BTCUSDT", 1010.0, tolerance_s=5.0) is None


def test_cache_returns_none_for_unknown_symbol():
    cache = InMemoryPriceCache()
    assert cache.get_price("ETHUSDT", 1000.0) is None


def test_cache_bounded_eviction():
    cache = InMemoryPriceCache(maxlen_per_symbol=3)
    cache.record("BTCUSDT", 1.0, 100.0)
    cache.record("BTCUSDT", 2.0, 200.0)
    cache.record("BTCUSDT", 3.0, 300.0)
    cache.record("BTCUSDT", 4.0, 400.0)
    # oldest entry (1.0, 100.0) should be evicted
    assert cache.get_price("BTCUSDT", 1.0, tolerance_s=0.1) is None
    assert cache.get_price("BTCUSDT", 4.0) == 400.0


def test_cache_picks_closest_entry():
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 100.0, 50000.0)
    cache.record("BTCUSDT", 105.0, 50100.0)
    cache.record("BTCUSDT", 110.0, 50200.0)
    assert cache.get_price("BTCUSDT", 106.0, tolerance_s=5.0) == 50100.0


def test_cache_thread_safety():
    cache = InMemoryPriceCache()
    errors = []

    def writer():
        try:
            for i in range(500):
                cache.record("BTCUSDT", float(i), 50000.0 + i)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for i in range(500):
                cache.get_price("BTCUSDT", float(i))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


# --- BinancePriceSource ---


def test_binance_source_parses_kline():
    import json
    import urllib.request

    kline = [[1234, "49000", "51000", "48000", "50500", "100", 1235, "0", 0, "0", "0", "0"]]

    source = BinancePriceSource()
    with patch.object(urllib.request, "urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(kline).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        price = source.get_price("BTCUSDT", 1234.0)
    assert price == 50500.0  # close price at index 4


def test_binance_source_returns_none_on_error():
    import urllib.request

    source = BinancePriceSource()
    with patch.object(urllib.request, "urlopen", side_effect=Exception("network")):
        price = source.get_price("BTCUSDT", 1234.0)
    assert price is None


def test_binance_source_returns_none_on_empty_response():
    import json
    import urllib.request

    source = BinancePriceSource()
    with patch.object(urllib.request, "urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([]).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        price = source.get_price("BTCUSDT", 1234.0)
    assert price is None


# --- LookbackTask ---


def test_lookback_task_ordering():
    t1 = LookbackTask(due_time=100, symbol="A", action="BUY", entry_price=1.0, decision_time=0, window=60)
    t2 = LookbackTask(due_time=200, symbol="B", action="SELL", entry_price=2.0, decision_time=0, window=60)
    assert t1 < t2


# --- PriceLookback ---


@patch("trade.price_lookback.logger")
def test_lookback_schedule_enqueues(mock_logger):
    source = MagicMock()
    cache = InMemoryPriceCache()
    store = MagicMock()

    lb = PriceLookback(windows=[60, 300], price_source=source, cache=cache, outcome_store=store)
    decision = {"symbol": "BTCUSDT", "action": "BUY", "entry_price": 50000.0}

    lb.schedule(decision)
    assert lb._queue.qsize() == 2
    lb.stop()


@patch("trade.price_lookback.logger")
def test_lookback_executes_and_writes_outcome(mock_logger):
    source = MagicMock()
    source.get_price.return_value = 50150.0
    cache = InMemoryPriceCache()
    store = MagicMock()

    lb = PriceLookback(windows=[0], price_source=source, cache=cache, outcome_store=store)
    decision = {"symbol": "BTCUSDT", "action": "BUY", "entry_price": 50000.0}

    lb.schedule(decision)
    time.sleep(0.5)
    lb.stop()

    assert store.write.called
    record = store.write.call_args[0][0]
    assert record["type"] == "price_lookback"
    assert record["symbol"] == "BTCUSDT"
    assert record["outcome_price"] == 50150.0
    assert record["direction_correct"] is True


@patch("trade.price_lookback.logger")
def test_lookback_pnl_calculation_buy(mock_logger):
    source = MagicMock()
    source.get_price.return_value = 105.0
    cache = InMemoryPriceCache()
    store = MagicMock()

    lb = PriceLookback(windows=[0], price_source=source, cache=cache, outcome_store=store)
    lb.schedule({"symbol": "X", "action": "BUY", "entry_price": 100.0})
    time.sleep(0.5)
    lb.stop()

    record = store.write.call_args[0][0]
    assert record["pnl_pct"] == 0.05
    assert record["direction_correct"] is True


@patch("trade.price_lookback.logger")
def test_lookback_pnl_calculation_sell(mock_logger):
    source = MagicMock()
    source.get_price.return_value = 95.0
    cache = InMemoryPriceCache()
    store = MagicMock()

    lb = PriceLookback(windows=[0], price_source=source, cache=cache, outcome_store=store)
    lb.schedule({"symbol": "X", "action": "SELL", "entry_price": 100.0})
    time.sleep(0.5)
    lb.stop()

    record = store.write.call_args[0][0]
    assert record["pnl_pct"] == 0.05
    assert record["direction_correct"] is True


@patch("trade.price_lookback.logger")
def test_lookback_cache_preferred_over_binance(mock_logger):
    source = MagicMock()
    source.get_price.return_value = 999.0
    cache = InMemoryPriceCache()
    store = MagicMock()

    lb = PriceLookback(windows=[0], price_source=source, cache=cache, outcome_store=store)

    # Pre-populate cache with a price near due_time
    now = time.time()
    cache.record("BTCUSDT", now, 50100.0)

    lb.schedule({"symbol": "BTCUSDT", "action": "BUY", "entry_price": 50000.0})
    time.sleep(0.5)
    lb.stop()

    record = store.write.call_args[0][0]
    assert record["price_source"] == "cache"
    assert record["outcome_price"] == 50100.0
    source.get_price.assert_not_called()


@patch("trade.price_lookback.logger")
def test_lookback_falls_back_to_binance(mock_logger):
    source = MagicMock()
    source.get_price.return_value = 50200.0
    cache = InMemoryPriceCache()  # empty cache
    store = MagicMock()

    lb = PriceLookback(windows=[0], price_source=source, cache=cache, outcome_store=store)
    lb.schedule({"symbol": "BTCUSDT", "action": "BUY", "entry_price": 50000.0})
    time.sleep(0.5)
    lb.stop()

    record = store.write.call_args[0][0]
    assert record["price_source"] == "binance"
    source.get_price.assert_called_once()


@patch("trade.price_lookback.logger")
def test_lookback_handles_both_sources_failing(mock_logger):
    source = MagicMock()
    source.get_price.return_value = None
    cache = InMemoryPriceCache()  # empty
    store = MagicMock()

    lb = PriceLookback(windows=[0], price_source=source, cache=cache, outcome_store=store)
    lb.schedule({"symbol": "BTCUSDT", "action": "BUY", "entry_price": 50000.0})
    time.sleep(0.5)
    lb.stop()

    store.write.assert_not_called()


@patch("trade.price_lookback.logger")
def test_max_pending_drops_tasks(mock_logger):
    source = MagicMock()
    cache = InMemoryPriceCache()
    store = MagicMock()

    lb = PriceLookback(
        windows=[9999],  # far future so nothing executes
        price_source=source,
        cache=cache,
        outcome_store=store,
        max_pending=2,
    )

    lb.schedule({"symbol": "A", "action": "BUY", "entry_price": 1.0})
    lb.schedule({"symbol": "B", "action": "BUY", "entry_price": 2.0})
    lb.schedule({"symbol": "C", "action": "BUY", "entry_price": 3.0})  # should drop

    # 2 accepted + 1 dropped = queue should have 2
    assert lb._queue.qsize() == 2
    lb.stop()


@patch("trade.price_lookback.logger")
def test_schedule_is_nonblocking(mock_logger):
    source = MagicMock()
    cache = InMemoryPriceCache()
    store = MagicMock()

    lb = PriceLookback(windows=[60, 300, 900], price_source=source, cache=cache, outcome_store=store)

    start = time.time()
    lb.schedule({"symbol": "BTCUSDT", "action": "BUY", "entry_price": 50000.0})
    elapsed = time.time() - start

    assert elapsed < 0.1
    lb.stop()
