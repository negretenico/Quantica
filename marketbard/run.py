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
from model.openai_client import OpenAIClient
from model.build_prompt import build_prompt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

event_buffer = EventBuffer()
openai_client = OpenAIClient(Config.OPEN_AI_TOKEN)
github_client = GithubClient(token=Config.GH_TOKEN, repo_name=Config.GITHUB_REPO)

gen_queue: queue.Queue = queue.Queue()
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


def daily_trigger():
    while True:
        now = datetime.datetime.now(_ET)
        target = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        sleep_secs = (target - now).total_seconds()
        logger.info(f"daily_trigger: next flush in {sleep_secs / 3600:.1f}h at market close")
        threading.Event().wait(timeout=sleep_secs)
        batch = event_buffer.drain()
        if batch:
            if len(batch) > 500:
                step = len(batch) // 500
                batch = batch[::step][:500]
            logger.info(f"daily_trigger: flushing {len(batch)} events to gen_queue")
            gen_queue.put(batch)
        else:
            logger.info("daily_trigger: no events accumulated today")


def story_worker():
    while True:
        try:
            batch = gen_queue.get()
            logger.info(f"story_worker: generating story for {len(batch)} events")
            prompt = build_prompt(batch)
            story = openai_client.create_story(prompt, len(batch))
            write_queue.put(story)
            logger.info("story_worker: story queued for writing")
        except Exception:
            logger.exception("story_worker: error generating story")


def writer():
    while True:
        try:
            story = write_queue.get()
            story_md = story["story_md"].replace("\\n", "\n")
            github_client.write_story(story_md)
            logger.info("writer: committed new story to GitHub")
        except Exception:
            logger.exception("writer: error writing story to GitHub")


def main():
    logger.info("Starting MarketBard")
    rabbit_manager = RabbitClientManager(config=Config)
    rabbit_manager.subscribe(handler=signal_event_handler)
    threading.Thread(target=daily_trigger, daemon=True).start()
    threading.Thread(target=story_worker, daemon=True).start()
    threading.Thread(target=writer, daemon=True).start()

    rabbit_manager.start_consuming()

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down cleanly…")


if __name__ == "__main__":
    main()
