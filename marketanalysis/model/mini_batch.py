from collections import deque
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction import FeatureHasher
from scipy.sparse import vstack
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


def _do_retrain():
    global model
    with _lock:
        if not _retrain_buffer:
            logger.info("retrain: buffer empty, skipping")
            return
        X = vstack(list(_retrain_buffer))
        model = MiniBatchKMeans(n_clusters=4, random_state=0, batch_size=1, n_init="auto")
        model.partial_fit(X)
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
            _warmup_rows.clear()
            _warmed_up = True
            logger.info(f"Warmup complete after {Config.WARMUP_SAMPLES} samples")

        _retrain_buffer.append(X)

        label = model.predict(X)[0]
        dist = model.transform(X)[0]
        score = float(dist.min())
        return (data_point, label, score)
