import threading
import time
import logging

from app.config import Config
from gh.github_client import GithubClient
from rabbitmq.rabbit_client import RabbitClientManager
from redis_cache.redis_client import RedisClient
from model.openai_client import OpenAIClient
from model.build_prompt import build_prompt
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

redis_client = RedisClient(host=Config.REDIS_HOST, batch_size=3, max_wait=5)
openai_client = OpenAIClient(Config.OPEN_AI_TOKEN)
github_client = GithubClient(token=Config.GH_TOKEN,repo_name= Config.GITHUB_REPO)


def signal_event_handler(event):
    enrichment = redis_client.get_enrichment(event.get("symbol"), event.get("eventTime"))
    if enrichment:
        event = {**event, "cluster_id": enrichment.get("cluster_id"), "anomaly_score": enrichment.get("anomaly_score")}
        logger.info(f"Enriched signal: symbol={event.get('symbol')} cluster={enrichment.get('cluster_id')} anomaly={enrichment.get('anomaly_score'):.4f}")
    redis_client.add_to_buffer(event)


def buffer_flusher():
    while True:
        try:
            redis_client.flush_buffer_if_ready()
        except Exception:
            logger.exception("buffer_flusher: error flushing buffer")
        time.sleep(2)

def story_worker():
    while True:
        try:
            batch = redis_client.get_latest_gen_queue()
            if not batch:
                time.sleep(2)
                continue

            events = batch["events"]
            logger.info(f"story_worker: generating story for {len(events)} events")
            prompt = build_prompt(events)
            story = openai_client.create_story(prompt, len(events))
            redis_client.add_story(story)
            logger.info("story_worker: story queued for writing")
        except Exception:
            logger.exception("story_worker: error generating story")
            time.sleep(5)


def writer():
    while True:
        try:
            story = redis_client.get_latest_story()
            if not story:
                time.sleep(2)
                continue

            story_md = story["story_md"].replace("\\n", "\n")
            github_client.write_story(story_md)
            logger.info("writer: committed new story to GitHub")
        except Exception:
            logger.exception("writer: error writing story to GitHub")
            time.sleep(5)



def main():
    logger.info("Starting MarketBard")
    rabbit_manager = RabbitClientManager(config=Config)
    rabbit_manager.subscribe(handler=signal_event_handler)
    threading.Thread(target=buffer_flusher, daemon=True).start()
    threading.Thread(target=story_worker, daemon=True).start()
    threading.Thread(target=writer, daemon=True).start()

    rabbit_manager.start_consuming()

    # Block forever to keep the main thread alive
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down cleanly…")


if __name__=="__main__":
    main()