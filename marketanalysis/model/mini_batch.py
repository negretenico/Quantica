from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction import FeatureHasher
from scipy.sparse import vstack  # <- important: stack sparse rows correctly
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Vectorizer & model
vectorizer = FeatureHasher(input_type='dict', n_features=64)

model = MiniBatchKMeans(
    n_clusters=4,
    random_state=0,
    batch_size=1,      # per-message update (you said you don't like batching)
    n_init="auto"
)

# Warm-up buffer for the first n_clusters samples (sparse rows)
_init_rows = []

def flatten_event(event: dict) -> dict:
    flat = {}
    for k, v in event.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                flat[f"{k}_{sk}"] = sv
        else:
            flat[k] = v
    return flat

def mini_batch(data_point):
    """
    - Before the model is initialized: buffer rows until we have >= n_clusters.
    - Initialize with a single partial_fit on the stacked warm-up.
    - Then, for each message: partial_fit + predict + anomaly score.
    Returns:
        None until initialized,
        or (event, label, anomaly_score) thereafter.
    """
    global _init_rows, model, vectorizer

    logger.info(f"Training on msg {data_point}")

    clean_point = flatten_event(data_point)
    X = vectorizer.transform([clean_point])  # CSR (1, n_features)

    # If not initialized yet, buffer rows
    if not hasattr(model, "cluster_centers_"):
        _init_rows.append(X)
        if len(_init_rows) < model.n_clusters:
            # Not enough samples yet; don't train/predict
            return None

        # Initialize clusters with >= n_clusters samples
        X0 = vstack(_init_rows)          # <- key fix (use scipy.sparse.vstack)
        model.partial_fit(X0)            # seeds cluster centers
        _init_rows.clear()               # free buffer

        # Now we can predict for the current X as well
        label = model.predict(X)[0]
        dist = model.transform(X)[0]     # distances to each centroid (1D)
        score = float(dist.min())        # anomaly score
        return (data_point, label, score)

    # Normal streaming path: update + predict
    model.partial_fit(X)
    label = model.predict(X)[0]
    dist = model.transform(X)[0]
    score = float(dist.min())
    return (data_point, label, score)
