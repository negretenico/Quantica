import datetime
import logging
import threading

import pytest
from unittest.mock import patch

from run import _cap_events, _compute_metrics, _supervised_thread
from app.config import Config


class TestCapEvents:
    def test_returns_all_when_under_cap(self):
        events = [{"id": i} for i in range(10)]
        assert _cap_events(events, 100) == events

    def test_returns_all_when_equal_to_cap(self):
        events = [{"id": i} for i in range(100)]
        assert _cap_events(events, 100) == events

    def test_samples_down_to_cap(self):
        events = [{"id": i} for i in range(10_000)]
        result = _cap_events(events, 100)
        assert len(result) == 100

    def test_preserves_first_element(self):
        events = [{"id": i} for i in range(500)]
        result = _cap_events(events, 50)
        assert result[0] == events[0]

    def test_evenly_spaced(self):
        events = [{"id": i} for i in range(1000)]
        result = _cap_events(events, 10)
        ids = [e["id"] for e in result]
        # step = 1000/10 = 100, so ids should be 0, 100, 200, ...
        assert ids == [i * 100 for i in range(10)]

    def test_empty_list(self):
        assert _cap_events([], 100) == []


class TestComputeMetrics:
    def test_basic_metrics(self):
        events = [
            {"quantity": "1.5", "price": "100.0", "anomaly_score": 0.9},
            {"quantity": "2.5", "price": "110.0"},
            {"quantity": "3.0", "price": "105.0", "anomaly_score": None},
        ]
        m = _compute_metrics(events, "09:30")
        assert m["window_start"] == "09:30"
        assert m["event_count"] == 3
        assert m["volume"] == pytest.approx(7.0)
        assert m["price_movement"] == pytest.approx(10.0)
        assert m["anomaly_count"] == 1

    def test_single_event_no_price_movement(self):
        events = [{"quantity": "5.0", "price": "50.0"}]
        m = _compute_metrics(events, "10:00")
        assert m["price_movement"] == 0.0

    def test_empty_events(self):
        m = _compute_metrics([], "11:00")
        assert m["event_count"] == 0
        assert m["volume"] == 0.0
        assert m["price_movement"] == 0.0
        assert m["anomaly_count"] == 0

    def test_missing_quantity_defaults_to_zero(self):
        events = [{"price": "100.0"}, {"price": "200.0", "quantity": "3.0"}]
        m = _compute_metrics(events, "12:00")
        assert m["volume"] == pytest.approx(3.0)


class TestSupervisedThread:
    def test_logs_critical_on_crash(self, caplog):
        def crasher():
            raise RuntimeError("boom")

        with caplog.at_level(logging.CRITICAL):
            t = _supervised_thread(crasher, "test-crasher")
            t.join(timeout=2)
        assert "THREAD DIED: test-crasher" in caplog.text
        assert "RuntimeError: boom" in caplog.text

    def test_normal_thread_completes(self, caplog):
        result = []

        def worker():
            result.append("done")

        with caplog.at_level(logging.CRITICAL):
            t = _supervised_thread(worker, "test-worker")
            t.join(timeout=2)
        assert result == ["done"]
        assert "THREAD DIED" not in caplog.text


class TestSynthesisHourConfig:
    def test_default_synthesis_hour(self):
        # Config.SYNTHESIS_HOUR should be an int
        assert isinstance(Config.SYNTHESIS_HOUR, int)

    def test_synthesis_hour_used_in_target(self, monkeypatch):
        monkeypatch.setattr(Config, "SYNTHESIS_HOUR", 20)
        from zoneinfo import ZoneInfo
        _ET = ZoneInfo("America/New_York")
        now = datetime.datetime(2026, 7, 31, 15, 0, 0, tzinfo=_ET)
        target = now.replace(hour=Config.SYNTHESIS_HOUR, minute=0, second=0, microsecond=0)
        assert target.hour == 20
        assert target > now

    def test_synthesis_hour_wraps_to_next_day(self, monkeypatch):
        monkeypatch.setattr(Config, "SYNTHESIS_HOUR", 20)
        from zoneinfo import ZoneInfo
        _ET = ZoneInfo("America/New_York")
        now = datetime.datetime(2026, 7, 31, 21, 0, 0, tzinfo=_ET)
        target = now.replace(hour=Config.SYNTHESIS_HOUR, minute=0, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        assert target.day == 1  # August 1
        assert target.hour == 20


class TestMaxEventsPerWindowConfig:
    def test_default_exists(self):
        assert isinstance(Config.MAX_EVENTS_PER_WINDOW, int)
        assert Config.MAX_EVENTS_PER_WINDOW > 0
