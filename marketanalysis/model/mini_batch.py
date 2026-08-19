from collections import deque
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction import FeatureHasher
from scipy.sparse import vstack
import bisect
import threading
import datetime
import logging
from zoneinfo import ZoneInfo

import numpy as np

from app.config import Config

logger = logging.getLogger(__name__)


class InvalidFeaturesError(ValueError):
    """Raised when a feature vector contains NaN or Inf values."""

_ET = ZoneInfo("America/New_York")

vectorizer = FeatureHasher(input_type='dict', n_features=Config.N_FEATURES)

model = MiniBatchKMeans(
    n_clusters=Config.N_CLUSTERS,
    random_state=Config.RANDOM_STATE,
    batch_size=Config.BATCH_SIZE,
    n_init="auto"
)

# Warmup buffer — sparse rows accumulated until WARMUP_SAMPLES reached
_warmup_rows: list = []
_warmed_up: bool = False

# Rolling retrain buffer — bounded at RETRAIN_BUFFER_SIZE; holds sparse rows
_retrain_buffer: deque = deque(maxlen=Config.RETRAIN_BUFFER_SIZE)

# Sorted list of recent raw distances for percentile-rank normalisation
_distance_buffer: list[float] = []
_DISTANCE_BUFFER_MAX = Config.RETRAIN_BUFFER_SIZE

_lock = threading.Lock()


def flatten_event(event: dict) -> dict:
    flat = {}
    for k, v in event.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                flat[f"{k}_{sk}"] = sv
        else:
            flat[k] = v
    return flat


def _percentile_rank(sorted_distances: list[float], value: float) -> float:
    """Return the fraction of values in *sorted_distances* that are <= *value* (0-1)."""
    n = len(sorted_distances)
    if n == 0:
        return 1.0
    rank = bisect.bisect_right(sorted_distances, value)
    return rank / n


def _validate_features(X, symbol: str = "unknown"):
    """Raise InvalidFeaturesError if sparse matrix *X* contains NaN or Inf."""
    data = X.data if hasattr(X, "data") else np.asarray(X).ravel()
    if len(data) > 0 and not np.all(np.isfinite(data)):
        raise InvalidFeaturesError(
            f"Feature vector for {symbol} contains NaN or Inf values"
        )


def _record_distance(raw_dist: float):
    """Insert *raw_dist* into the sorted distance buffer, evicting the oldest if full."""
    global _distance_buffer
    if _DISTANCE_BUFFER_MAX <= 0:
        return
    if len(_distance_buffer) >= _DISTANCE_BUFFER_MAX:
        mid = len(_distance_buffer) // 2
        _distance_buffer.pop(mid)
    bisect.insort(_distance_buffer, raw_dist)


def _do_retrain():
    global model, _distance_buffer
    with _lock:
        if not _retrain_buffer:
            logger.info("retrain: buffer empty, skipping")
            return
        X = vstack(list(_retrain_buffer))
        model = MiniBatchKMeans(n_clusters=Config.N_CLUSTERS, random_state=Config.RANDOM_STATE, batch_size=Config.BATCH_SIZE, n_init="auto")
        model.partial_fit(X)
        # Recompute distance buffer from new clusters
        dists = model.transform(X)
        _distance_buffer = sorted(float(row.min()) for row in dists)
        logger.info(f"retrain: completed on {len(_retrain_buffer)} samples")


def _schedule_retrain():
    while True:
        now = datetime.datetime.now(_ET)
        target = now.replace(hour=Config.RETRAIN_HOUR, minute=Config.RETRAIN_MINUTE, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        sleep_secs = (target - now).total_seconds()
        logger.info(f"retrain: next scheduled in {sleep_secs / 3600:.1f}h at {Config.RETRAIN_HOUR:02d}:{Config.RETRAIN_MINUTE:02d} ET")
        threading.Event().wait(timeout=sleep_secs)
        _do_retrain()


threading.Thread(target=_schedule_retrain, daemon=True).start()


def mini_batch(data_point):
    """
    Warmup phase: buffer the first WARMUP_SAMPLES events and run partial_fit once to seed clusters.
    Post-warmup: predict + anomaly score only — no per-message partial_fit.
    Retrain buffer is updated on every post-warmup call for the 09:30 ET daily retrain.

    Returns None during warmup, or (event, label, anomaly_score) once warmed up.
    """
    global _warmup_rows, _warmed_up

    with _lock:
        clean_point = flatten_event(data_point)
        X = vectorizer.transform([clean_point])
        symbol = data_point.get("symbol", "unknown")
        _validate_features(X, symbol)

        if not _warmed_up:
            _warmup_rows.append(X)
            if len(_warmup_rows) < Config.WARMUP_SAMPLES:
                return None
            X0 = vstack(_warmup_rows)
            model.partial_fit(X0)
            # Seed distance buffer from warmup data so the first post-warmup
            # scores have a meaningful baseline for percentile ranking.
            dists = model.transform(X0)
            _distance_buffer.clear()
            for row in dists:
                bisect.insort(_distance_buffer, float(row.min()))
            _warmup_rows.clear()
            _warmed_up = True
            logger.info(f"Warmup complete after {Config.WARMUP_SAMPLES} samples")

        _retrain_buffer.append(X)

        label = model.predict(X)[0]
        dist = model.transform(X)[0]
        raw_dist = float(dist.min())
        score = _percentile_rank(_distance_buffer, raw_dist)
        _record_distance(raw_dist)
        return (data_point, label, score)
