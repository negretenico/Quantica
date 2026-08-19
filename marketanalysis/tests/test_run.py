from unittest.mock import patch, MagicMock

import pytest

from model.mini_batch import InvalidFeaturesError


@pytest.fixture(autouse=True)
def _reset_logged_failures():
    import run
    run._logged_failures.clear()
    yield
    run._logged_failures.clear()


class TestHandleEventErrorHandling:
    @patch("run._alerter")
    @patch("run.mini_batch", side_effect=InvalidFeaturesError("NaN in BTCUSDT"))
    @patch("run._dedup")
    def test_validation_error_increments_metrics(self, mock_dedup, mock_mb, mock_alerter):
        mock_dedup.is_duplicate.return_value = False
        import run
        from app.metrics import errors_total, validation_failures_total

        before_errors = errors_total._value.get()
        before_val = validation_failures_total.labels(symbol="BTCUSDT")._value.get()

        with pytest.raises(InvalidFeaturesError):
            run._handle_event({"symbol": "BTCUSDT", "price": "100"})

        assert errors_total._value.get() == before_errors + 1
        assert validation_failures_total.labels(symbol="BTCUSDT")._value.get() == before_val + 1

    @patch("run._alerter")
    @patch("run.mini_batch", side_effect=InvalidFeaturesError("NaN"))
    @patch("run._dedup")
    def test_validation_error_fires_alert(self, mock_dedup, mock_mb, mock_alerter):
        mock_dedup.is_duplicate.return_value = False
        import run

        with pytest.raises(InvalidFeaturesError):
            run._handle_event({"symbol": "ETHUSDT", "price": "3000"})

        mock_alerter.send_alert.assert_called_once_with("ETHUSDT", "validation_error", "NaN")

    @patch("run._alerter")
    @patch("run.mini_batch", side_effect=RuntimeError("sklearn exploded"))
    @patch("run._dedup")
    def test_ml_failure_increments_errors_and_alerts(self, mock_dedup, mock_mb, mock_alerter):
        mock_dedup.is_duplicate.return_value = False
        import run
        from app.metrics import errors_total

        before = errors_total._value.get()

        with pytest.raises(RuntimeError):
            run._handle_event({"symbol": "BTCUSDT", "price": "100"})

        assert errors_total._value.get() == before + 1
        mock_alerter.send_alert.assert_called_once_with(
            "BTCUSDT", "ml_failure", "sklearn exploded"
        )

    @patch("run._alerter")
    @patch("run.mini_batch", side_effect=RuntimeError("crash"))
    @patch("run._dedup")
    def test_exception_re_raised_for_retry(self, mock_dedup, mock_mb, mock_alerter):
        mock_dedup.is_duplicate.return_value = False
        import run

        with pytest.raises(RuntimeError, match="crash"):
            run._handle_event({"symbol": "X", "price": "1"})

    @patch("run._alerter")
    @patch("run.send_msg", side_effect=RuntimeError("publish failed"))
    @patch("run.mini_batch", return_value=({"symbol": "X"}, 0, 0.5))
    @patch("run._dedup")
    def test_publish_failure_increments_errors_and_alerts(
        self, mock_dedup, mock_mb, mock_send, mock_alerter
    ):
        mock_dedup.is_duplicate.return_value = False
        import run
        from app.metrics import errors_total

        before = errors_total._value.get()

        with pytest.raises(RuntimeError):
            run._handle_event({"symbol": "X", "price": "1"})

        assert errors_total._value.get() == before + 1
        mock_alerter.send_alert.assert_called_once()

    @patch("run._alerter")
    @patch("run.mini_batch", side_effect=InvalidFeaturesError("NaN"))
    @patch("run._dedup")
    def test_log_throttle_suppresses_duplicate_warnings(self, mock_dedup, mock_mb, mock_alerter):
        mock_dedup.is_duplicate.return_value = False
        import run

        with pytest.raises(InvalidFeaturesError):
            run._handle_event({"symbol": "BTCUSDT", "price": "100"})
        with pytest.raises(InvalidFeaturesError):
            run._handle_event({"symbol": "BTCUSDT", "price": "100"})

        assert ("BTCUSDT", "validation_error") in run._logged_failures
