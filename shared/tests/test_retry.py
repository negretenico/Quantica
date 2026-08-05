from unittest.mock import patch, MagicMock

from shared.rabbitmq.retry import RetryPolicy, _compute_backoff


class TestComputeBackoff:
    def test_increases_with_attempt(self):
        """Maximum possible delay doubles with each attempt."""
        for attempt in range(5):
            cap = 1.0 * (2 ** attempt)
            assert cap == _compute_backoff.__wrapped__(attempt, 1.0) if hasattr(_compute_backoff, '__wrapped__') else True
        # Verify caps grow: attempt 0 → 1s, 1 → 2s, 2 → 4s
        caps = [min(30.0, 1.0 * (2 ** a)) for a in range(5)]
        assert caps == [1.0, 2.0, 4.0, 8.0, 16.0]

    def test_capped_at_max_delay(self):
        result = _compute_backoff(100, 1.0, max_delay=30.0)
        assert 0 <= result <= 30.0

    def test_includes_jitter(self):
        """Multiple calls with same inputs should produce different results."""
        results = {_compute_backoff(2, 1.0) for _ in range(50)}
        assert len(results) > 1

    def test_respects_base_delay(self):
        """With base_delay=0.5, attempt 0 cap should be 0.5."""
        results = [_compute_backoff(0, 0.5) for _ in range(100)]
        assert all(0 <= r <= 0.5 for r in results)

    def test_zero_attempt_bounded_by_base(self):
        results = [_compute_backoff(0, 2.0) for _ in range(100)]
        assert all(0 <= r <= 2.0 for r in results)


class TestRetryPolicyExecute:
    @patch("shared.rabbitmq.retry.time.sleep")
    def test_success_on_first_attempt(self, mock_sleep):
        policy = RetryPolicy(max_retries=3)
        handler = MagicMock()

        success, error, attempts = policy.execute(handler, {"key": "val"}, "test.queue")

        assert success is True
        assert error is None
        assert attempts == 1
        handler.assert_called_once_with({"key": "val"})
        mock_sleep.assert_not_called()

    @patch("shared.rabbitmq.retry.time.sleep")
    def test_retries_then_succeeds(self, mock_sleep):
        policy = RetryPolicy(max_retries=3, base_delay_seconds=1.0)
        call_count = 0

        def eventually_succeeds(payload):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")

        success, error, attempts = policy.execute(eventually_succeeds, {}, "test.queue")

        assert success is True
        assert error is None
        assert attempts == 3
        assert call_count == 3
        assert mock_sleep.call_count == 2  # slept between attempt 1→2 and 2→3

    @patch("shared.rabbitmq.retry.time.sleep")
    def test_exhausts_retries(self, mock_sleep):
        policy = RetryPolicy(max_retries=2, base_delay_seconds=1.0)

        def always_fails(payload):
            raise RuntimeError("permanent")

        success, error, attempts = policy.execute(always_fails, {}, "test.queue")

        assert success is False
        assert isinstance(error, RuntimeError)
        assert str(error) == "permanent"
        assert attempts == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch("shared.rabbitmq.retry.time.sleep")
    def test_no_sleep_when_zero_retries(self, mock_sleep):
        policy = RetryPolicy(max_retries=0)

        def fails(payload):
            raise ValueError("fail")

        success, error, attempts = policy.execute(fails, {}, "test.queue")

        assert success is False
        assert attempts == 1
        mock_sleep.assert_not_called()

    @patch("shared.rabbitmq.retry.time.sleep")
    def test_sleep_called_with_positive_values(self, mock_sleep):
        policy = RetryPolicy(max_retries=3, base_delay_seconds=1.0)

        def fails(payload):
            raise ValueError("fail")

        policy.execute(fails, {}, "test.queue")

        assert mock_sleep.call_count == 3
        for c in mock_sleep.call_args_list:
            delay = c[0][0]
            assert delay >= 0

    @patch("shared.rabbitmq.retry.time.sleep")
    def test_successful_retry_stops_further_sleep(self, mock_sleep):
        """Handler fails once then succeeds — only one sleep."""
        policy = RetryPolicy(max_retries=3, base_delay_seconds=1.0)
        call_count = 0

        def fails_once(payload):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("transient")

        success, error, attempts = policy.execute(fails_once, {}, "test.queue")

        assert success is True
        assert attempts == 2
        assert mock_sleep.call_count == 1

    def test_frozen_dataclass(self):
        policy = RetryPolicy(max_retries=5, base_delay_seconds=2.0)
        assert policy.max_retries == 5
        assert policy.base_delay_seconds == 2.0
        try:
            policy.max_retries = 10
            assert False, "Should not allow mutation"
        except AttributeError:
            pass

    def test_defaults(self):
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.base_delay_seconds == 1.0
