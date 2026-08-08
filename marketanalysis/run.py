import logging
import threading
import time

from app import create_app, rabbit_manager
from app.config import Config
from app.metrics import (
    events_consumed_total,
    duplicates_dropped_total,
    clusters_computed_total,
    anomalies_detected_total,
    processing_latency,
    observe_tick_to_analysis,
    start_metrics_server,
)
from model.mini_batch import mini_batch
from analysis.outbound import send_msg
from shared.dedup import DedupFilter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()

_dedup = DedupFilter(maxlen=Config.DEDUP_SET_SIZE)


def _handle_event(event):
    events_consumed_total.inc()

    if _dedup.is_duplicate(event):
        duplicates_dropped_total.inc()
        logger.debug("Duplicate event dropped: %s", event.get("symbol"))
        return

    symbol = event.get("symbol", "unknown")
    start = time.perf_counter()

    prediction = mini_batch(event)
    elapsed = time.perf_counter() - start
    processing_latency.labels(symbol=symbol).observe(elapsed)

    if prediction is None:
        return

    _event, label, anomaly_score = prediction
    clusters_computed_total.labels(
        symbol=symbol, cluster_id=str(label)
    ).inc()

    if anomaly_score >= Config.ANOMALY_THRESHOLD:
        anomalies_detected_total.labels(symbol=symbol).inc()

    send_msg(prediction=prediction)
    observe_tick_to_analysis(event)


rabbit_manager.subscribe(handler=_handle_event)

if __name__ == '__main__':
    start_metrics_server()
    logger.info("Prometheus metrics server started on port 8000")
    threading.Thread(target=rabbit_manager.start_consuming, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
