import bisect
from collections import deque
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from model.mini_batch import (
    flatten_event,
    _percentile_rank,
    _record_distance,
    _validate_features,
    _do_retrain,
    mini_batch,
    InvalidFeaturesError,
)
import model.mini_batch as mb


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Reset all module-level mutable state before each test."""
    mb._warmup_rows.clear()
    mb._warmed_up = False
    mb._retrain_buffer.clear()
    mb._distance_buffer.clear()
    # Re-init the model so cluster centers are not carried across tests
    from sklearn.cluster import MiniBatchKMeans
    mb.model = MiniBatchKMeans(n_clusters=4, random_state=0, batch_size=1, n_init="auto")
    yield


@pytest.fixture()
def small_warmup(monkeypatch):
    """Set WARMUP_SAMPLES to a small value for fast tests (must be >= n_clusters=4)."""
    monkeypatch.setattr("app.config.Config.WARMUP_SAMPLES", 5)


# ---------------------------------------------------------------------------
# flatten_event
# ---------------------------------------------------------------------------

class TestFlattenEvent:
    def test_flat_dict_unchanged(self):
        event = {"symbol": "BTCUSDT", "price": "100.0"}
        assert flatten_event(event) == event

    def test_nested_dict_flattened(self):
        event = {"symbol": "BTCUSDT", "metadata": {"exchange": "binance", "lag": 5}}
        flat = flatten_event(event)
        assert flat == {"symbol": "BTCUSDT", "metadata_exchange": "binance", "metadata_lag": 5}

    def test_multiple_nested_dicts(self):
        event = {"a": {"x": 1, "y": 2}, "b": {"z": 3}}
        flat = flatten_event(event)
        assert flat == {"a_x": 1, "a_y": 2, "b_z": 3}

    def test_empty_dict(self):
        assert flatten_event({}) == {}

    def test_mixed_types_preserved(self):
        event = {"symbol": "ETH", "price": 3000.5, "active": True, "meta": {"v": None}}
        flat = flatten_event(event)
        assert flat["price"] == 3000.5
        assert flat["active"] is True
        assert flat["meta_v"] is None


# ---------------------------------------------------------------------------
# _percentile_rank
# ---------------------------------------------------------------------------

class TestPercentileRank:
    def test_empty_buffer_returns_one(self):
        assert _percentile_rank([], 5.0) == 1.0

    def test_value_below_all(self):
        buf = [1.0, 2.0, 3.0]
        assert _percentile_rank(buf, 0.5) == 0.0

    def test_value_above_all(self):
        buf = [1.0, 2.0, 3.0]
        assert _percentile_rank(buf, 10.0) == 1.0

    def test_value_in_middle(self):
        buf = [1.0, 2.0, 3.0, 4.0]
        # bisect_right([1,2,3,4], 2.0) == 2 → 2/4 = 0.5
        assert _percentile_rank(buf, 2.0) == 0.5

    def test_single_element_equal(self):
        assert _percentile_rank([5.0], 5.0) == 1.0

    def test_single_element_below(self):
        assert _percentile_rank([5.0], 3.0) == 0.0

    def test_duplicates_in_buffer(self):
        buf = [1.0, 1.0, 1.0, 2.0]
        # bisect_right returns 3 → 3/4 = 0.75
        assert _percentile_rank(buf, 1.0) == 0.75


# ---------------------------------------------------------------------------
# _record_distance
# ---------------------------------------------------------------------------

class TestRecordDistance:
    def test_inserts_in_sorted_order(self):
        mb._distance_buffer = []
        _record_distance(3.0)
        _record_distance(1.0)
        _record_distance(5.0)
        assert mb._distance_buffer == [1.0, 3.0, 5.0]

    def test_evicts_median_when_full(self, monkeypatch):
        monkeypatch.setattr(mb, "_DISTANCE_BUFFER_MAX", 4)
        mb._distance_buffer = [1.0, 2.0, 3.0, 4.0]
        _record_distance(2.5)
        # Buffer was full (4), pops median index 2 (value 3.0), then inserts 2.5
        assert len(mb._distance_buffer) == 4
        assert 3.0 not in mb._distance_buffer
        assert 2.5 in mb._distance_buffer

    def test_buffer_stays_bounded(self, monkeypatch):
        monkeypatch.setattr(mb, "_DISTANCE_BUFFER_MAX", 5)
        for i in range(20):
            _record_distance(float(i))
        assert len(mb._distance_buffer) <= 5


# ---------------------------------------------------------------------------
# _do_retrain
# ---------------------------------------------------------------------------

class TestDoRetrain:
    def test_skips_when_buffer_empty(self, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            _do_retrain()
        assert "buffer empty" in caplog.text

    def test_retrains_and_rebuilds_distance_buffer(self):
        # Seed retrain buffer with some sparse rows
        from sklearn.feature_extraction import FeatureHasher
        h = FeatureHasher(input_type="dict", n_features=64)
        for i in range(10):
            X = h.transform([{"price": float(i), "qty": float(i * 2)}])
            mb._retrain_buffer.append(X)

        _do_retrain()

        # After retrain, distance buffer should have entries
        assert len(mb._distance_buffer) == 10
        # All distances should be non-negative floats
        assert all(d >= 0.0 for d in mb._distance_buffer)
        # Buffer should be sorted
        assert mb._distance_buffer == sorted(mb._distance_buffer)


# ---------------------------------------------------------------------------
# mini_batch — warmup phase
# ---------------------------------------------------------------------------

class TestMininBatchWarmup:
    def test_returns_none_during_warmup(self, small_warmup):
        event = {"symbol": "BTCUSDT", "price": "100", "quantity": "1"}
        assert mini_batch(event) is None
        assert mini_batch(event) is None
        assert mb._warmed_up is False

    def test_warmup_completes_at_threshold(self, small_warmup):
        events = [
            {"symbol": "BTCUSDT", "price": str(100 + i), "quantity": str(i)}
            for i in range(5)
        ]
        for e in events[:4]:
            assert mini_batch(e) is None
        # Fifth completes warmup AND returns a result
        result = mini_batch(events[4])
        assert mb._warmed_up is True
        assert result is not None

    def test_distance_buffer_seeded_after_warmup(self, small_warmup):
        for i in range(5):
            mini_batch({"symbol": "X", "price": str(i), "quantity": "1"})
        # Distance buffer has warmup_samples (5) + 1 from the post-warmup inference
        # on the final call that triggers warmup completion
        assert len(mb._distance_buffer) == 6


# ---------------------------------------------------------------------------
# mini_batch — inference phase
# ---------------------------------------------------------------------------

class TestMiniBatchInference:
    def _warmup(self):
        """Push enough events to complete warmup (5 with small_warmup)."""
        for i in range(5):
            mini_batch({"symbol": "BTCUSDT", "price": str(100 + i), "quantity": str(i)})

    def test_returns_tuple_after_warmup(self, small_warmup):
        self._warmup()
        result = mini_batch({"symbol": "ETHUSDT", "price": "3000", "quantity": "0.5"})
        assert result is not None
        event, label, score = result
        assert event["symbol"] == "ETHUSDT"

    def test_label_is_valid_cluster_id(self, small_warmup):
        self._warmup()
        _, label, _ = mini_batch({"symbol": "X", "price": "50", "quantity": "1"})
        assert label in range(4)  # n_clusters=4

    def test_anomaly_score_is_between_zero_and_one(self, small_warmup):
        self._warmup()
        for i in range(10):
            result = mini_batch({"symbol": "X", "price": str(50 + i * 10), "quantity": str(i)})
            _, _, score = result
            assert 0.0 <= score <= 1.0

    def test_retrain_buffer_grows(self, small_warmup):
        self._warmup()
        before = len(mb._retrain_buffer)
        mini_batch({"symbol": "X", "price": "99", "quantity": "1"})
        assert len(mb._retrain_buffer) == before + 1

    def test_distance_buffer_grows_with_inference(self, small_warmup):
        self._warmup()
        before = len(mb._distance_buffer)
        mini_batch({"symbol": "X", "price": "200", "quantity": "5"})
        assert len(mb._distance_buffer) == before + 1

    def test_original_event_returned_unchanged(self, small_warmup):
        self._warmup()
        original = {"symbol": "DOT", "price": "7.5", "quantity": "100", "extra": "field"}
        event, _, _ = mini_batch(original)
        assert event == original

    def test_nested_event_handled(self, small_warmup):
        self._warmup()
        event = {"symbol": "X", "price": "1", "metadata": {"lag": 5, "src": "ws"}}
        result = mini_batch(event)
        assert result is not None
        returned_event, label, score = result
        assert returned_event is event


# ---------------------------------------------------------------------------
# mini_batch — retrain buffer bounding
# ---------------------------------------------------------------------------

class TestRetainBufferBounding:
    def test_retrain_buffer_respects_maxlen(self, small_warmup, monkeypatch):
        monkeypatch.setattr("app.config.Config.RETRAIN_BUFFER_SIZE", 5)
        # Re-create bounded deque with new maxlen
        mb._retrain_buffer = deque(maxlen=5)

        self._warmup()
        for i in range(10):
            mini_batch({"symbol": "X", "price": str(i), "quantity": "1"})
        assert len(mb._retrain_buffer) <= 5

    def _warmup(self):
        for i in range(5):
            mini_batch({"symbol": "X", "price": str(i), "quantity": "1"})


# ---------------------------------------------------------------------------
# _validate_features
# ---------------------------------------------------------------------------

class TestValidateFeatures:
    def test_accepts_clean_matrix(self):
        X = csr_matrix(np.array([[1.0, 2.0, 3.0]]))
        _validate_features(X, "BTCUSDT")  # should not raise

    def test_rejects_nan(self):
        X = csr_matrix(np.array([[1.0, float("nan"), 3.0]]))
        with pytest.raises(InvalidFeaturesError, match="NaN or Inf"):
            _validate_features(X, "BTCUSDT")

    def test_rejects_inf(self):
        X = csr_matrix(np.array([[1.0, float("inf"), 3.0]]))
        with pytest.raises(InvalidFeaturesError, match="NaN or Inf"):
            _validate_features(X, "BTCUSDT")

    def test_rejects_neg_inf(self):
        X = csr_matrix(np.array([[float("-inf"), 2.0]]))
        with pytest.raises(InvalidFeaturesError, match="NaN or Inf"):
            _validate_features(X, "ETHUSDT")

    def test_empty_sparse_matrix_passes(self):
        X = csr_matrix((1, 5))  # all zeros, no stored data
        _validate_features(X)  # should not raise

    def test_includes_symbol_in_message(self):
        X = csr_matrix(np.array([[float("nan")]]))
        with pytest.raises(InvalidFeaturesError, match="SOLUSDT"):
            _validate_features(X, "SOLUSDT")


class TestMiniBatchValidation:
    def test_raises_on_nan_features(self, small_warmup):
        with patch.object(mb.vectorizer, "transform") as mock_transform:
            mock_transform.return_value = csr_matrix(np.array([[float("nan"), 1.0]]))
            with pytest.raises(InvalidFeaturesError):
                mini_batch({"symbol": "BTCUSDT", "price": "100", "quantity": "1"})


# ---------------------------------------------------------------------------
# _record_distance — edge cases
# ---------------------------------------------------------------------------

class TestRecordDistanceEdgeCases:
    def test_zero_max_is_noop(self, monkeypatch):
        monkeypatch.setattr(mb, "_DISTANCE_BUFFER_MAX", 0)
        mb._distance_buffer = []
        _record_distance(1.0)
        assert mb._distance_buffer == []

    def test_max_one_keeps_single_element(self, monkeypatch):
        monkeypatch.setattr(mb, "_DISTANCE_BUFFER_MAX", 1)
        mb._distance_buffer = []
        _record_distance(5.0)
        assert mb._distance_buffer == [5.0]
        _record_distance(3.0)
        assert len(mb._distance_buffer) == 1
