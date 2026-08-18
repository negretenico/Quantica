from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _isolate_run_module():
    """Reset module-level enrichment state before each test."""
    import run
    run._enrichment_cache.clear()
    run._analytics_dedup = MagicMock()
    run._analytics_dedup.is_duplicate.return_value = False
    run._signal_dedup = MagicMock()
    run._signal_dedup.is_duplicate.return_value = False
    yield
    run._enrichment_cache.clear()


class TestAnalyticsHandler:
    def test_caches_enrichment_by_symbol(self):
        from run import analytics_handler, _enrichment_cache
        payload = {"symbol": "BTCUSDT", "cluster_id": 2, "anomaly_score": 0.85}
        analytics_handler(payload)
        assert _enrichment_cache["BTCUSDT"] == payload

    def test_overwrites_previous_enrichment(self):
        from run import analytics_handler, _enrichment_cache
        analytics_handler({"symbol": "ETH", "cluster_id": 0, "anomaly_score": 0.1})
        analytics_handler({"symbol": "ETH", "cluster_id": 3, "anomaly_score": 0.99})
        assert _enrichment_cache["ETH"]["cluster_id"] == 3

    def test_skips_duplicate(self):
        import run
        run._analytics_dedup.is_duplicate.return_value = True
        run.analytics_handler({"symbol": "BTC", "cluster_id": 1, "anomaly_score": 0.5})
        assert "BTC" not in run._enrichment_cache

    def test_ignores_event_without_symbol(self):
        from run import analytics_handler, _enrichment_cache
        analytics_handler({"cluster_id": 1, "anomaly_score": 0.5})
        assert len(_enrichment_cache) == 0


class TestSignalEventHandler:
    def test_enriches_event_from_cache(self):
        import run
        run._enrichment_cache["BTCUSDT"] = {"cluster_id": 2, "anomaly_score": 0.75}
        captured = []
        run.event_buffer = MagicMock()
        run.event_buffer.add = lambda e: captured.append(e)
        run.event_buffer.__len__ = lambda self: len(captured)

        run.signal_event_handler({"symbol": "BTCUSDT", "price": "100", "eventTime": 1000})

        assert len(captured) == 1
        assert captured[0]["cluster_id"] == 2
        assert captured[0]["anomaly_score"] == 0.75

    def test_passes_through_without_enrichment(self):
        import run
        captured = []
        run.event_buffer = MagicMock()
        run.event_buffer.add = lambda e: captured.append(e)
        run.event_buffer.__len__ = lambda self: len(captured)

        event = {"symbol": "DOTUSDT", "price": "7", "eventTime": 2000}
        run.signal_event_handler(event)

        assert len(captured) == 1
        assert "cluster_id" not in captured[0]

    def test_skips_duplicate_signal(self):
        import run
        run._signal_dedup.is_duplicate.return_value = True
        run.event_buffer = MagicMock()

        run.signal_event_handler({"symbol": "BTC", "eventTime": 3000})

        run.event_buffer.add.assert_not_called()

    def test_enrichment_does_not_mutate_original_event(self):
        import run
        run._enrichment_cache["BTC"] = {"cluster_id": 1, "anomaly_score": 0.5}
        captured = []
        run.event_buffer = MagicMock()
        run.event_buffer.add = lambda e: captured.append(e)
        run.event_buffer.__len__ = lambda self: len(captured)

        original = {"symbol": "BTC", "price": "50", "eventTime": 4000}
        run.signal_event_handler(original)

        # Original dict should not be mutated (enrichment creates a new dict)
        assert "cluster_id" not in original
        assert captured[0]["cluster_id"] == 1

    def test_enrichment_preserves_all_original_fields(self):
        import run
        run._enrichment_cache["X"] = {"cluster_id": 0, "anomaly_score": 0.1}
        captured = []
        run.event_buffer = MagicMock()
        run.event_buffer.add = lambda e: captured.append(e)
        run.event_buffer.__len__ = lambda self: len(captured)

        run.signal_event_handler({
            "symbol": "X", "price": "10", "quantity": "5",
            "type": "BUY", "side": "ask", "eventTime": 5000,
        })

        enriched = captured[0]
        assert enriched["symbol"] == "X"
        assert enriched["price"] == "10"
        assert enriched["quantity"] == "5"
        assert enriched["type"] == "BUY"
        assert enriched["side"] == "ask"
        assert enriched["cluster_id"] == 0
        assert enriched["anomaly_score"] == 0.1
