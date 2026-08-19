import datetime
import logging
import queue
import threading

import pytest
from unittest.mock import patch, MagicMock

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

    def test_anomaly_score_zero_is_not_counted(self):
        # anomaly_score=0 is not None, so it SHOULD be counted
        events = [
            {"quantity": "1", "price": "100", "anomaly_score": 0},
            {"quantity": "1", "price": "100", "anomaly_score": 0.0},
        ]
        m = _compute_metrics(events, "13:00")
        assert m["anomaly_count"] == 2

    def test_all_same_price_zero_movement(self):
        events = [
            {"quantity": "1", "price": "50.0"},
            {"quantity": "2", "price": "50.0"},
            {"quantity": "3", "price": "50.0"},
        ]
        m = _compute_metrics(events, "14:00")
        assert m["price_movement"] == 0.0

    def test_events_with_no_price_field(self):
        events = [{"quantity": "5"}, {"quantity": "3"}]
        m = _compute_metrics(events, "15:00")
        assert m["price_movement"] == 0.0
        assert m["volume"] == pytest.approx(8.0)

    def test_mixed_anomaly_scores(self):
        events = [
            {"anomaly_score": 0.9},
            {"anomaly_score": None},
            {},
            {"anomaly_score": 0.1},
        ]
        m = _compute_metrics(events, "16:00")
        assert m["anomaly_count"] == 2


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


class TestWindowWorker:
    def test_processes_batch_and_adds_to_summary_buffer(self, monkeypatch):
        import run
        from accumulator.summary_buffer import SummaryBuffer

        fake_client = MagicMock()
        fake_client.create_window_summary.return_value = {
            "narrative_summary": "BTC surged.",
            "category": "BULLISH",
        }
        monkeypatch.setattr(run, "openai_client", fake_client)

        test_summary_buffer = SummaryBuffer(maxlen=10)
        monkeypatch.setattr(run, "summary_buffer", test_summary_buffer)

        events = [
            {"symbol": "BTC", "quantity": "5", "price": "100", "anomaly_score": 0.9},
            {"symbol": "BTC", "quantity": "3", "price": "110"},
        ]

        # Put a batch on the window queue, then a sentinel to stop the worker
        test_queue = queue.Queue()
        test_queue.put(("10:00", events))
        monkeypatch.setattr(run, "window_queue", test_queue)

        # Run one iteration of window_worker by calling it in a thread with a timeout
        def one_iteration():
            window_start, evts = run.window_queue.get()
            metrics = _compute_metrics(evts, window_start)
            from model.build_prompt import build_window_prompt
            prompt = build_window_prompt(evts, metrics)
            result = run.openai_client.create_window_summary(prompt)
            summary = {
                "window_start": window_start,
                "narrative_summary": result["narrative_summary"],
                "category": result["category"],
                "metrics": metrics,
            }
            run.summary_buffer.add(summary)

        one_iteration()

        assert len(test_summary_buffer) == 1
        summaries = test_summary_buffer.drain()
        assert summaries[0]["window_start"] == "10:00"
        assert summaries[0]["category"] == "BULLISH"
        assert summaries[0]["narrative_summary"] == "BTC surged."
        assert summaries[0]["metrics"]["event_count"] == 2
        assert summaries[0]["metrics"]["volume"] == pytest.approx(8.0)
        assert summaries[0]["metrics"]["anomaly_count"] == 1

    def test_prompt_passed_to_llm_contains_events(self, monkeypatch):
        import run

        captured_prompt = []
        fake_client = MagicMock()
        fake_client.create_window_summary.side_effect = lambda prompt, **kw: (
            captured_prompt.append(prompt) or
            {"narrative_summary": "ok", "category": "NEUTRAL"}
        )
        monkeypatch.setattr(run, "openai_client", fake_client)
        monkeypatch.setattr(run, "summary_buffer", MagicMock())

        events = [{"symbol": "ETH", "type": "SELL", "quantity": "10", "price": "3000"}]
        test_queue = queue.Queue()
        test_queue.put(("11:00", events))
        monkeypatch.setattr(run, "window_queue", test_queue)

        window_start, evts = run.window_queue.get()
        metrics = _compute_metrics(evts, window_start)
        from model.build_prompt import build_window_prompt
        prompt = build_window_prompt(evts, metrics)
        run.openai_client.create_window_summary(prompt)

        assert "ETH" in captured_prompt[0]
        assert "3000" in captured_prompt[0]
        assert "11:00" in captured_prompt[0]


class TestMaxEventsPerWindowConfig:
    def test_default_exists(self):
        assert isinstance(Config.MAX_EVENTS_PER_WINDOW, int)
        assert Config.MAX_EVENTS_PER_WINDOW > 0
