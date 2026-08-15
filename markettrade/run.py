import logging
import time
import threading
from datetime import datetime, timezone
from functools import partial

from app.config import Config
from app.metrics import (
    start_metrics_server,
)
from app.rabbit_client import SignalRabbitClient
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.observer import (
    AccumulationObserver,
    ConcentrationObserver,
    NearLimitObserver,
    RiskObserverPipeline,
)
from shared.blob import get_store
from shared.dedup import DedupFilter
from shared.rabbitmq.publisher import RabbitPublisher
from trade.outcome import DecisionLog
from trade.calibration import CalibrationEngine, BUCKETS, _bucket_label, _bucket_for
from shared.monitor import metric_monitor
from trade.outcome_tracker import OutcomeTracker
from trade.outcome_writer import OutcomeWriter
from trade.price_lookback import create_lookback
from trade.rate_limiter import TradeRateLimiter
from trade.validation import ValidationPipeline, validate_schema, validate_price_sanity
from trade.pipeline.chain import Pipeline
from trade.pipeline.context import PipelineContext
from trade.pipeline.steps.dedup import DedupStep
from trade.pipeline.steps.validate import ValidateStep
from trade.pipeline.steps.decide import DecideStep
from trade.pipeline.steps.risk_evaluate import RiskEvaluateStep
from trade.pipeline.steps.near_limit import NearLimitStep
from trade.pipeline.steps.risk_gate import RiskGateStep
from trade.pipeline.steps.record_outcome import RecordOutcomeStep
from trade.pipeline.steps.persist_and_notify import PersistAndNotifyStep

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    config = Config()
    client = SignalRabbitClient(config.rabbitmq)
    risk_engine = RiskEngine(config.risk)
    near_limit_observer = NearLimitObserver(threshold_pct=config.risk.NEAR_LIMIT_THRESHOLD_PCT)
    concentration_observer = ConcentrationObserver(
        near_limit_observer, max_correlated=config.risk.CONCENTRATION_THRESHOLD,
    )
    accumulation_observer = AccumulationObserver(
        threshold=config.risk.ACCUMULATION_THRESHOLD,
    )
    risk_observer_pipeline = RiskObserverPipeline([
        near_limit_observer, concentration_observer, accumulation_observer,
    ])
    store = get_store(config.blob_store.BACKEND, config.blob_store.PATH)
    outcome_store = get_store(config.blob_store.BACKEND, config.OUTCOME_STORE_PATH)
    risk_alert_store = get_store(config.blob_store.BACKEND, config.RISK_ALERT_STORE_PATH)
    decision_log = DecisionLog(outcome_store, max_size=config.DECISION_LOG_MAX_SIZE)
    outcome_tracker = OutcomeTracker()
    outcome_writer = OutcomeWriter(
        store=outcome_store,
        flush_count=config.OUTCOME_FLUSH_COUNT,
        flush_interval_seconds=config.OUTCOME_FLUSH_INTERVAL,
    )
    outcome_tracker.add_on_outcome(outcome_writer.write)
    notify_publisher = RabbitPublisher(
        url=config.rabbitmq.URL,
        exchange="notifications",
    )
    calibration_engine = CalibrationEngine(window_size=config.calibration.WINDOW_SIZE)

    @metric_monitor(
        publisher=notify_publisher,
        routing_key="alert.markettrade",
        prefix="CALIBRATION",
        thresholds={
            "floor": config.calibration.DRIFT_THRESHOLD,
            "ceiling": config.calibration.OVERFIT_THRESHOLD,
            "min_samples": config.calibration.MIN_SAMPLES,
        },
        source="markettrade",
    )
    def record_and_monitor(outcome):
        from app.metrics import (
            calibration_drift,
            calibration_overfit,
            outcome_correct_total,
            outcome_incorrect_total,
            calibration_alerts_total,
        )

        calibration_engine.record(outcome)

        bucket = _bucket_for(outcome.anomaly_score)
        label = _bucket_label(bucket) if bucket else "none"
        if outcome.direction_correct:
            outcome_correct_total.labels(bucket=label).inc()
        else:
            outcome_incorrect_total.labels(bucket=label).inc()

        metrics = {}
        for b in BUCKETS:
            bl = _bucket_label(b)
            acc = calibration_engine.accuracy(b)
            cnt = calibration_engine.count(b)
            if acc is not None:
                metrics[bl] = (acc, cnt)
                is_drifting = acc < config.calibration.DRIFT_THRESHOLD and cnt >= config.calibration.MIN_SAMPLES
                is_overfit = acc > config.calibration.OVERFIT_THRESHOLD and cnt >= config.calibration.MIN_SAMPLES
                calibration_drift.labels(bucket=bl).set(1 if is_drifting else 0)
                calibration_overfit.labels(bucket=bl).set(1 if is_overfit else 0)

        return metrics

    outcome_tracker.add_on_outcome(record_and_monitor)
    dedup = DedupFilter()
    lookback, price_cache = create_lookback(config, outcome_tracker=outcome_tracker)

    validation_pipeline = ValidationPipeline([
        validate_schema,
        partial(
            validate_price_sanity,
            enabled=config.price_sanity.ENABLED,
            min_price=config.price_sanity.MIN_PRICE,
            max_price=config.price_sanity.MAX_PRICE,
        ),
    ])

    rate_limiter = None
    if config.rate_limiter.ENABLED:
        rate_limiter = TradeRateLimiter(
            max_per_minute=config.rate_limiter.MAX_PER_MINUTE,
            window_seconds=config.rate_limiter.WINDOW_SECONDS,
        )
        logger.info(
            "Rate limiter enabled — max %d per symbol per %.0fs",
            config.rate_limiter.MAX_PER_MINUTE,
            config.rate_limiter.WINDOW_SECONDS,
        )

    start_metrics_server()
    logger.info("Prometheus metrics server started on :8000")

    pipeline = Pipeline([
        DedupStep(dedup),
        ValidateStep(validation_pipeline, price_cache),
        DecideStep(config, rate_limiter),
        RiskEvaluateStep(risk_engine, config),
        NearLimitStep(risk_observer_pipeline, near_limit_observer, risk_alert_store, config, risk_engine),
        RiskGateStep(),
        RecordOutcomeStep(decision_log, lookback),
        PersistAndNotifyStep(store, notify_publisher),
    ])

    def handle_message(payload):
        ctx = PipelineContext(payload=payload)
        pipeline.execute(ctx)

    client.subscribe(handle_message)
    client.start_consuming()
    threading.Event().wait()


if __name__ == "__main__":
    main()
