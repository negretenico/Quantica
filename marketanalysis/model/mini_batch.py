from collections import deque
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction import FeatureHasher
from scipy.sparse import vstack
import bisect
import threading
import datetime
import logging
from zoneinfo import ZoneInfo

from app.config import Config

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

vectorizer = FeatureHasher(input_type='dict', n_features=64)

model = MiniBatchKMeans(
    n_clusters=4,
    random_state=0,
    batch_size=1,
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


def _record_distance(raw_dist: float):
    """Insert *raw_dist* into the sorted distance buffer, evicting the oldest if full."""
    global _distance_buffer
    if len(_distance_buffer) >= _DISTANCE_BUFFER_MAX:
        # Drop the median element to keep the buffer bounded without skewing extremes
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
        model = MiniBatchKMeans(n_clusters=4, random_state=0, batch_size=1, n_init="auto")
        model.partial_fit(X)
        # Recompute distance buffer from new clusters
        dists = model.transform(X)
        _distance_buffer = sorted(float(row.min()) for row in dists)
        logger.info(f"retrain: completed on {len(_retrain_buffer)} samples")


def _schedule_retrain():
    while True:
        now = datetime.datetime.now(_ET)
        target = now.replace(hour=9, minute=30, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        sleep_secs = (target - now).total_seconds()
        logger.info(f"retrain: next scheduled in {sleep_secs / 3600:.1f}h at 09:30 ET")
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
