import json
import queue
import threading
import datetime
import logging
from zoneinfo import ZoneInfo

import pika

from app.config import Config
from gh.github_client import GithubClient
from rabbitmq.rabbit_client import RabbitClientManager
from accumulator.event_buffer import EventBuffer
from accumulator.summary_buffer import SummaryBuffer
from model.openai_client import OpenAIClient
from model.build_prompt import build_window_prompt, build_synthesis_prompt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

event_buffer = EventBuffer()
summary_buffer = SummaryBuffer(maxlen=Config.MAX_SUMMARY_BUFFER)
openai_client = OpenAIClient(Config.OPEN_AI_TOKEN)
github_client = GithubClient(token=Config.GH_TOKEN, repo_name=Config.GITHUB_REPO)

# window_queue: (window_start: str, events: list) tuples from window_trigger
# write_queue: final narrative strings ready for GitHub commit
window_queue: queue.Queue = queue.Queue()
write_queue: queue.Queue = queue.Queue()

_ET = ZoneInfo("America/New_York")
_analytics_channel = None
_declared_queues: set = set()


def _analytics_channel_get():
    global _analytics_channel
    if _analytics_channel is None or _analytics_channel.is_closed:
        conn = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
        _analytics_channel = conn.channel()
        _analytics_channel.exchange_declare(
            exchange=Config.ANALYTICS_EXCHANGE,
            exchange_type="topic",
            durable=True,
        )
    return _analytics_channel


def _pop_analytics(symbol: str) -> dict | None:
    try:
        ch = _analytics_channel_get()
        queue_name = f"analytics.bard.{symbol}"
        if queue_name not in _declared_queues:
            ch.queue_declare(queue=queue_name, durable=True)
            ch.queue_bind(
                queue=queue_name,
                exchange=Config.ANALYTICS_EXCHANGE,
                routing_key=f"signal.analytics.{symbol}",
            )
            _declared_queues.add(queue_name)
        method, _, body = ch.basic_get(queue=queue_name, auto_ack=True)
        return json.loads(body) if body else None
    except Exception:
        logger.exception("_pop_analytics: failed, continuing without enrichment")
        return None


def signal_event_handler(event):
    symbol = event.get("symbol")
    enriched = _pop_analytics(symbol)
    if enriched:
        event = {**event, "cluster_id": enriched.get("cluster_id"), "anomaly_score": enriched.get("anomaly_score")}
        logger.info(f"Enriched signal: symbol={symbol} cluster={enriched.get('cluster_id')} anomaly={enriched.get('anomaly_score'):.4f}")
    event_buffer.add(event)


def _compute_metrics(events: list, window_start: str) -> dict:
    quantities = [float(e.get("quantity") or 0) for e in events]
    prices = [float(e.get("price") or 0) for e in events if e.get("price")]
    anomaly_count = sum(1 for e in events if e.get("anomaly_score") is not None)
    return {
        "window_start": window_start,
        "event_count": len(events),
        "volume": sum(quantities),
        "price_movement": (max(prices) - min(prices)) if len(prices) >= 2 else 0.0,
        "anomaly_count": anomaly_count,
    }


def window_trigger():
    """Fires every WINDOW_MINUTES, drains event_buffer, puts batch on window_queue."""
    interval = Config.WINDOW_MINUTES * 60
    while True:
        threading.Event().wait(timeout=interval)
        window_start = datetime.datetime.now(_ET).strftime("%H:%M")
        events = event_buffer.drain()
        if not events:
            logger.debug(f"window_trigger: no events in window ending at {window_start}, skipping")
            continue
        logger.info(f"window_trigger: {len(events)} events in window ending at {window_start}")
        window_queue.put((window_start, events))


def synthesis_trigger():
    """Fires at 4:00 PM ET, drains summary_buffer, runs synthesis, queues narrative for GitHub."""
    while True:
        now = datetime.datetime.now(_ET)
        target = now.replace(hour=20, minute=45, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        sleep_secs = (target - now).total_seconds()
        logger.info(f"synthesis_trigger: next synthesis in {sleep_secs / 3600:.1f}h at market close")
        threading.Event().wait(timeout=sleep_secs)
        summaries = summary_buffer.drain()
        if not summaries:
            logger.info("synthesis_trigger: no window summaries accumulated today, skipping")
            continue
        logger.info(f"synthesis_trigger: running synthesis over {len(summaries)} windows")
        try:
            prompt = build_synthesis_prompt(summaries)
            narrative = openai_client.create_synthesis(prompt, max_tokens=Config.SYNTHESIS_MAX_TOKENS)
            write_queue.put(narrative)
            logger.info("synthesis_trigger: synthesis queued for writing")
        except Exception:
            logger.exception("synthesis_trigger: error during synthesis")


def window_worker():
    """Consumes window batches, computes metrics, calls structured window inference, adds to summary_buffer."""
    while True:
        try:
            window_start, events = window_queue.get()
            metrics = _compute_metrics(events, window_start)
            prompt = build_window_prompt(events, metrics)
            result = openai_client.create_window_summary(prompt, max_tokens=Config.WINDOW_SUMMARY_MAX_TOKENS)
            summary = {
                "window_start": window_start,
                "narrative_summary": result["narrative_summary"],
                "category": result["category"],
                "metrics": metrics,
            }
            summary_buffer.add(summary)
            logger.info(f"window_worker: summary added for window {window_start} [{result['category']}]")
        except Exception:
            logger.exception("window_worker: error processing window")


def writer():
    """Commits narratives from write_queue to GitHub."""
    while True:
        try:
            narrative = write_queue.get()
            github_client.write_story(narrative)
            logger.info("writer: committed daily narrative to GitHub")
        except Exception:
            logger.exception("writer: error writing narrative to GitHub")


def main():
    logger.info("Starting MarketBard")
    github_client.check_connection()
    rabbit_manager = RabbitClientManager(config=Config)
    rabbit_manager.subscribe(handler=signal_event_handler)
    threading.Thread(target=window_trigger, daemon=True).start()
    threading.Thread(target=synthesis_trigger, daemon=True).start()
    threading.Thread(target=window_worker, daemon=True).start()
    threading.Thread(target=writer, daemon=True).start()

    rabbit_manager.start_consuming()

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down cleanly…")


if __name__ == "__main__":
    main()
