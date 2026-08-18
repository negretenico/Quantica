import pytest

from model.build_prompt import build_prompt, build_window_prompt, build_synthesis_prompt


class TestBuildPrompt:
    def test_includes_event_details(self):
        events = [{"symbol": "BTCUSDT", "type": "BUY", "quantity": "1.5", "price": "100.0"}]
        prompt = build_prompt(events)
        assert "BTCUSDT" in prompt
        assert "BUY" in prompt
        assert "1.5" in prompt
        assert "100.0" in prompt

    def test_handles_nested_list(self):
        inner = [{"symbol": "ETH", "type": "SELL", "quantity": "2", "price": "50"}]
        prompt = build_prompt([inner])
        assert "ETH" in prompt

    def test_multiple_events(self):
        events = [
            {"symbol": "BTC", "type": "BUY", "quantity": "1", "price": "100"},
            {"symbol": "ETH", "type": "SELL", "quantity": "2", "price": "200"},
        ]
        prompt = build_prompt(events)
        assert "BTC" in prompt
        assert "ETH" in prompt

    def test_missing_optional_fields(self):
        events = [{"symbol": "DOT"}]
        prompt = build_prompt(events)
        assert "DOT" in prompt


class TestBuildWindowPrompt:
    @pytest.fixture()
    def metrics(self):
        return {
            "window_start": "09:30",
            "volume": 150.5,
            "price_movement": 12.3456,
            "anomaly_count": 2,
        }

    def test_includes_metrics(self, metrics):
        events = [{"symbol": "BTC", "type": "BUY", "quantity": "1", "price": "100"}]
        prompt = build_window_prompt(events, metrics)
        assert "Window: 09:30" in prompt
        assert "Volume: 150.5000" in prompt
        assert "Price movement: 12.3456" in prompt
        assert "Anomaly count: 2" in prompt

    def test_anomaly_marker_present(self, metrics):
        events = [
            {"symbol": "BTC", "type": "BUY", "quantity": "1", "price": "100", "anomaly_score": 0.95},
        ]
        prompt = build_window_prompt(events, metrics)
        assert "[ANOMALY]" in prompt

    def test_no_anomaly_marker_when_score_absent(self, metrics):
        events = [{"symbol": "BTC", "type": "BUY", "quantity": "1", "price": "100"}]
        prompt = build_window_prompt(events, metrics)
        assert "[ANOMALY]" not in prompt

    def test_anomaly_marker_absent_when_score_is_none(self, metrics):
        events = [{"symbol": "BTC", "anomaly_score": None}]
        prompt = build_window_prompt(events, metrics)
        assert "[ANOMALY]" not in prompt

    def test_contains_analyst_system_instruction(self, metrics):
        prompt = build_window_prompt([], metrics)
        assert "financial market analyst" in prompt

    def test_multiple_events_listed(self, metrics):
        events = [
            {"symbol": "BTC", "type": "BUY", "quantity": "1", "price": "100"},
            {"symbol": "ETH", "type": "SELL", "quantity": "5", "price": "3000"},
        ]
        prompt = build_window_prompt(events, metrics)
        assert "BTC" in prompt
        assert "ETH" in prompt


class TestBuildSynthesisPrompt:
    @pytest.fixture()
    def summaries(self):
        return [
            {
                "window_start": "09:30",
                "narrative_summary": "Calm session with low volume.",
                "category": "NEUTRAL",
                "metrics": {
                    "event_count": 50,
                    "volume": 120.0,
                    "price_movement": 5.0,
                    "anomaly_count": 1,
                },
            },
            {
                "window_start": "09:40",
                "narrative_summary": "Spike in BTC trading activity.",
                "category": "BULLISH",
                "metrics": {
                    "event_count": 200,
                    "volume": 800.0,
                    "price_movement": 45.0,
                    "anomaly_count": 3,
                },
            },
        ]

    def test_includes_session_totals(self, summaries):
        prompt = build_synthesis_prompt(summaries)
        assert "250 raw events" in prompt
        assert "4 anomalies" in prompt

    def test_includes_each_window_summary(self, summaries):
        prompt = build_synthesis_prompt(summaries)
        assert "09:30" in prompt
        assert "09:40" in prompt
        assert "NEUTRAL" in prompt
        assert "BULLISH" in prompt
        assert "Calm session" in prompt
        assert "Spike in BTC" in prompt

    def test_includes_per_window_metrics(self, summaries):
        prompt = build_synthesis_prompt(summaries)
        assert "Volume: 120.0000" in prompt
        assert "Volume: 800.0000" in prompt

    def test_empty_summaries(self):
        prompt = build_synthesis_prompt([])
        assert "0 raw events" in prompt
        assert "0 anomalies" in prompt

    def test_contains_analyst_system_instruction(self, summaries):
        prompt = build_synthesis_prompt(summaries)
        assert "financial market analyst" in prompt
